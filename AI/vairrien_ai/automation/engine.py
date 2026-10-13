from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from croniter import croniter

from vairrien_ai.automation.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    AutomationScheduleType,
)
from vairrien_ai.automation.scheduler import AutomationScheduler
from vairrien_ai.automation.state import AutomationStateStore


AutomationAction = Callable[
    [Automation],
    Awaitable[dict[str, Any]],
]


class AutomationEngine:
    """
    Coordinates scheduling and execution of Vairrien automations.

    Supports:
    - registered custom automation handlers
    - native Vairrien tasks through VairrienOrchestrator
    - one-time schedules
    - interval schedules
    - cron schedules
    - reliable transient-error recovery
    """

    def __init__(
        self,
        *,
        orchestrator: Any = None,
        state_store: AutomationStateStore | None = None,
        scheduler: AutomationScheduler | None = None,
        poll_interval: float = 5.0,
    ):
        self.orchestrator = orchestrator

        self.state_store = (
            state_store or AutomationStateStore()
        )

        self.scheduler = (
            scheduler
            or AutomationScheduler(
                state_store=self.state_store,
                poll_interval=poll_interval,
            )
        )

        self._action_handlers: dict[
            str,
            AutomationAction,
        ] = {}

        # ----------------------------------------------------
        # RELIABLE ERROR RECOVERY
        # ----------------------------------------------------

        # Number of retries AFTER the initial attempt.
        self.max_retries = 3

        # Exponential backoff:
        # retry 1 -> 2 seconds
        # retry 2 -> 4 seconds
        # retry 3 -> 8 seconds
        self.retry_base_delay = 2.0

        # Never allow the retry delay to exceed this value.
        self.retry_max_delay = 30.0

    # ========================================================
    # ACTION REGISTRATION
    # ========================================================

    def register_action(
        self,
        action_type: str,
        handler: AutomationAction,
    ) -> None:
        if not action_type:
            raise ValueError(
                "action_type must not be empty."
            )

        self._action_handlers[action_type] = handler

    # ========================================================
    # VAIRRIEN ACTION
    # ========================================================

    async def _execute_vairrien_task(
        self,
        automation: Automation,
    ) -> dict[str, Any]:
        """
        Execute an automation through the existing
        VairrienOrchestrator.
        """

        if self.orchestrator is None:
            raise RuntimeError(
                "AutomationEngine requires a "
                "VairrienOrchestrator for vairrien_task actions."
            )

        message = automation.action_data.get(
            "message"
        )

        if not message:
            raise ValueError(
                "vairrien_task requires "
                "action_data.message."
            )

        response = await self.orchestrator.respond(
            user_id=automation.user_id,
            conversation_id=automation.conversation_id,
            message=str(message),
        )

        return {
            "type": "vairrien_task",
            "response": response.get(
                "response",
                "",
            ),
            "conversation_id": response.get(
                "conversation_id",
                automation.conversation_id,
            ),
            "user_id": response.get(
                "user_id",
                automation.user_id,
            ),
            "tool_rounds": response.get(
                "tool_rounds",
                0,
            ),
            "tools_used": response.get(
                "tools_used",
                False,
            ),
            "usage": response.get(
                "usage"
            ),
        }

    # ========================================================
    # RELIABLE ERROR RECOVERY
    # ========================================================

    def _is_transient_error(
        self,
        error: Exception,
    ) -> bool:
        """
        Determine whether an error is likely temporary and
        therefore safe to retry.
        """

        message = str(error).lower()

        transient_markers = (
            "429",
            "502",
            "503",
            "504",
            "rate limit",
            "service temporarily overloaded",
            "temporarily unavailable",
            "upstream error",
            "timeout",
            "timed out",
            "connection error",
            "connection reset",
            "connection refused",
            "failed to resolve",
            "network error",
            "temporarily blocked",
        )

        return any(
            marker in message
            for marker in transient_markers
        )

    def _retry_delay(
        self,
        retry_number: int,
    ) -> float:
        """
        Calculate bounded exponential backoff.

        retry 1 -> 2 seconds
        retry 2 -> 4 seconds
        retry 3 -> 8 seconds

        The result is capped by retry_max_delay.
        """

        return min(
            self.retry_base_delay
            * (2 ** max(retry_number - 1, 0)),
            self.retry_max_delay,
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    async def execute(
        self,
        automation: Automation,
    ) -> AutomationRun:
        """
        Execute one automation with reliable transient-error
        recovery.

        The first attempt executes immediately.

        Transient failures are retried using bounded exponential
        backoff.

        Permanent failures are recorded immediately.

        Every attempt count is persisted to the AutomationRun.
        """

        run = AutomationRun(
            id=f"automation-run-{uuid4().hex[:12]}",
            automation_id=automation.id,
            user_id=automation.user_id,
            status=AutomationRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            attempts=1,
        )

        await self.state_store.save_run(
            run
        )

        action_type = str(
            automation.action_data.get(
                "type",
                "",
            )
        )

        # Initial attempt + configured retries.
        total_attempts = self.max_retries + 1

        for attempt in range(
            1,
            total_attempts + 1,
        ):
            run.attempts = attempt

            try:
                # ------------------------------------------------
                # NATIVE VAIRRIEN TASK
                # ------------------------------------------------

                if action_type == "vairrien_task":
                    result = await self._execute_vairrien_task(
                        automation
                    )

                # ------------------------------------------------
                # REGISTERED CUSTOM ACTION
                # ------------------------------------------------

                else:
                    handler = self._action_handlers.get(
                        action_type
                    )

                    if handler is None:
                        raise RuntimeError(
                            f"No automation handler registered "
                            f"for action type: {action_type}"
                        )

                    result = await handler(
                        automation
                    )

                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                run.mark_completed(
                    result
                )

                await self.state_store.save_run(
                    run
                )

                automation.record_success(
                    result
                )

                await self._update_schedule_after_success(
                    automation
                )

                return run

            except Exception as error:
                error_text = str(error)

                transient = self._is_transient_error(
                    error
                )

                retries_remaining = (
                    attempt < total_attempts
                )

                # ------------------------------------------------
                # TRANSIENT FAILURE
                # ------------------------------------------------

                if (
                    transient
                    and retries_remaining
                ):
                    run.status = (
                        AutomationRunStatus.RUNNING
                    )

                    run.error = error_text

                    # Persist the failed attempt before waiting.
                    await self.state_store.save_run(
                        run
                    )

                    delay = self._retry_delay(
                        attempt
                    )

                    await asyncio.sleep(
                        delay
                    )

                    continue

                # ------------------------------------------------
                # FINAL FAILURE
                # ------------------------------------------------

                run.mark_failed(
                    error_text
                )

                await self.state_store.save_run(
                    run
                )

                automation.record_failure(
                    error_text
                )

                # A failed one-time automation must not remain
                # scheduled for another execution.
                if (
                    automation.schedule_type
                    == AutomationScheduleType.ONCE
                ):
                    automation.next_run_at = None

                await self.state_store.save_automation(
                    automation
                )

                return run

    # ========================================================
    # SCHEDULE LIFECYCLE
    # ========================================================

    async def _update_schedule_after_success(
        self,
        automation: Automation,
    ) -> None:
        schedule_type = (
            automation.schedule_type
        )

        # ----------------------------------------------------
        # ONE-TIME
        # ----------------------------------------------------

        if (
            schedule_type
            == AutomationScheduleType.ONCE
        ):
            automation.mark_completed()
            automation.next_run_at = None

        # ----------------------------------------------------
        # INTERVAL
        # ----------------------------------------------------

        elif (
            schedule_type
            == AutomationScheduleType.INTERVAL
        ):
            interval_seconds = int(
                automation.schedule_data.get(
                    "interval_seconds",
                    0,
                )
            )

            if interval_seconds <= 0:
                automation.mark_failed(
                    "Invalid interval_seconds."
                )

                await self.state_store.save_automation(
                    automation
                )

                return

            automation.next_run_at = (
                datetime.now(timezone.utc)
                + timedelta(
                    seconds=interval_seconds
                )
            )

        # ----------------------------------------------------
        # CRON
        # ----------------------------------------------------

        elif (
            schedule_type
            == AutomationScheduleType.CRON
        ):
            cron_expression = str(
                automation.schedule_data.get(
                    "expression",
                    ""
                )
            ).strip()

            if not cron_expression:
                automation.mark_failed(
                    "CRON automation requires "
                    "schedule_data.expression."
                )

                await self.state_store.save_automation(
                    automation
                )

                return

            try:
                now = datetime.now(
                    timezone.utc
                )

                cron = croniter(
                    cron_expression,
                    now,
                )

                next_run = cron.get_next(
                    datetime
                )

                if next_run.tzinfo is None:
                    next_run = next_run.replace(
                        tzinfo=timezone.utc
                    )

                automation.next_run_at = (
                    next_run
                )

            except Exception as error:
                automation.mark_failed(
                    f"Invalid CRON expression: {error}"
                )

                await self.state_store.save_automation(
                    automation
                )

                return

        await self.state_store.save_automation(
            automation
        )

    # ========================================================
    # SCHEDULER CALLBACK
    # ========================================================

    async def handle_due_automation(
        self,
        automation: Automation,
    ) -> None:
        await self.execute(
            automation
        )

    # ========================================================
    # ENGINE LIFECYCLE
    # ========================================================

    async def start(self) -> None:
        await self.scheduler.start(
            self.handle_due_automation
        )

    async def stop(self) -> None:
        await self.scheduler.stop()

    async def run_forever(self) -> None:
        await self.scheduler.run(
            self.handle_due_automation
        )

    async def execute_once(
        self,
        automation: Automation,
    ) -> AutomationRun:
        return await self.execute(
            automation
        )