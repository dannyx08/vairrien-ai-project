from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from vairrien_ai.automation import (
    Automation,
    AutomationEngine,
    AutomationScheduleType,
    AutomationStateStore,
    AutomationStatus,
)


class AutomationTool:
    """
    Tool interface for creating and managing Vairrien automations.

    Runtime identity is supplied by trusted orchestrator context.
    The model must never control user_id or conversation_id.
    """

    def __init__(
        self,
        state_store: AutomationStateStore,
        engine: AutomationEngine | None = None,
    ):
        self.state_store = state_store
        self.engine = engine

    # ========================================================
    # CONTEXT
    # ========================================================

    @staticmethod
    def _require_context(
        context: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Extract trusted runtime identity from the orchestrator.

        The model must never control these values.
        """

        user_id = str(
            context.get("user_id", "")
        ).strip()

        conversation_id = str(
            context.get("conversation_id", "")
        ).strip()

        if not user_id:
            raise ValueError(
                "Automation tool requires user_id."
            )

        if not conversation_id:
            raise ValueError(
                "Automation tool requires conversation_id."
            )

        return user_id, conversation_id

    # ========================================================
    # CREATE
    # ========================================================

    async def create(
        self,
        *,
        context: dict[str, Any],
        name: str,
        description: str = "",
        schedule_type: str,
        schedule_data: dict[str, Any],
        message: str,
    ) -> dict[str, Any]:
        """
        Create a Vairrien scheduled task.

        The resulting automation executes a native
        `vairrien_task` action through AutomationEngine.
        """

        user_id, conversation_id = self._require_context(
            context
        )

        name = str(name).strip()
        description = str(description).strip()
        message = str(message).strip()

        if not name:
            raise ValueError(
                "Automation name cannot be empty."
            )

        if not message:
            raise ValueError(
                "Automation message cannot be empty."
            )

        try:
            schedule = AutomationScheduleType(
                str(schedule_type).strip().lower()
            )
        except ValueError as error:
            raise ValueError(
                "schedule_type must be one of: "
                "once, interval, cron."
            ) from error

        schedule_data = dict(
            schedule_data or {}
        )

        self._validate_schedule(
            schedule,
            schedule_data,
        )

        next_run_at = self._initial_next_run(
            schedule,
            schedule_data,
        )

        automation = Automation(
            id=f"automation-{uuid4().hex}",
            user_id=user_id,
            conversation_id=conversation_id,
            name=name,
            description=description,
            schedule_type=schedule,
            schedule_data=schedule_data,
            action_data={
                "type": "vairrien_task",
                "message": message,
            },
            status=AutomationStatus.ACTIVE,
            next_run_at=next_run_at,
        )

        await self.state_store.save_automation(
            automation
        )

        return {
            "status": "success",
            "automation": automation.to_dict(),
        }

    # ========================================================
    # LIST
    # ========================================================

    async def list(
        self,
        *,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        List active automations belonging to the
        authenticated runtime user.
        """

        user_id, _ = self._require_context(
            context
        )

        automations = (
            await self.state_store.load_active_automations(
                user_id=user_id
            )
        )

        return {
            "status": "success",
            "count": len(automations),
            "automations": [
                automation.to_dict()
                for automation in automations
            ],
        }

    # ========================================================
    # PAUSE
    # ========================================================

    async def pause(
        self,
        *,
        context: dict[str, Any],
        automation_id: str,
    ) -> dict[str, Any]:
        """
        Pause an automation.
        """

        user_id, _ = self._require_context(
            context
        )

        automation = await self.state_store.load_automation(
            user_id=user_id,
            automation_id=str(automation_id).strip(),
        )

        if automation is None:
            raise ValueError(
                "Automation not found."
            )

        automation.mark_paused()

        await self.state_store.save_automation(
            automation
        )

        return {
            "status": "success",
            "automation": automation.to_dict(),
        }

    # ========================================================
    # RESUME
    # ========================================================

    async def resume(
        self,
        *,
        context: dict[str, Any],
        automation_id: str,
    ) -> dict[str, Any]:
        """
        Resume a paused automation.
        """

        user_id, _ = self._require_context(
            context
        )

        automation = await self.state_store.load_automation(
            user_id=user_id,
            automation_id=str(automation_id).strip(),
        )

        if automation is None:
            raise ValueError(
                "Automation not found."
            )

        if automation.status == AutomationStatus.CANCELLED:
            raise ValueError(
                "Cancelled automations cannot be resumed."
            )

        automation.mark_active()

        now = datetime.now(timezone.utc)

        if (
            automation.next_run_at is None
            or automation.next_run_at <= now
        ):
            automation.next_run_at = (
                self._resume_next_run(automation)
            )

        await self.state_store.save_automation(
            automation
        )

        return {
            "status": "success",
            "automation": automation.to_dict(),
        }

    # ========================================================
    # CANCEL
    # ========================================================

    async def cancel(
        self,
        *,
        context: dict[str, Any],
        automation_id: str,
    ) -> dict[str, Any]:
        """
        Cancel an automation.
        """

        user_id, _ = self._require_context(
            context
        )

        automation = await self.state_store.load_automation(
            user_id=user_id,
            automation_id=str(automation_id).strip(),
        )

        if automation is None:
            raise ValueError(
                "Automation not found."
            )

        automation.mark_cancelled()
        automation.next_run_at = None

        await self.state_store.save_automation(
            automation
        )

        return {
            "status": "success",
            "automation": automation.to_dict(),
        }

    # ========================================================
    # RUN HISTORY
    # ========================================================

    async def runs(
        self,
        *,
        context: dict[str, Any],
        automation_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Return execution history for one automation.
        """

        user_id, _ = self._require_context(
            context
        )

        automation_id = str(
            automation_id
        ).strip()

        if not automation_id:
            raise ValueError(
                "automation_id cannot be empty."
            )

        try:
            limit = int(limit)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "limit must be an integer."
            ) from error

        limit = max(
            1,
            min(limit, 100),
        )

        automation = await self.state_store.load_automation(
            user_id=user_id,
            automation_id=automation_id,
        )

        if automation is None:
            raise ValueError(
                "Automation not found."
            )

        runs = await self.state_store.load_runs(
            user_id=user_id,
            automation_id=automation_id,
            limit=limit,
        )

        return {
            "status": "success",
            "automation_id": automation_id,
            "count": len(runs),
            "runs": [
                run.to_dict()
                for run in runs
            ],
        }

    # ========================================================
    # SCHEDULE VALIDATION
    # ========================================================

    @staticmethod
    def _validate_schedule(
        schedule_type: AutomationScheduleType,
        schedule_data: dict[str, Any],
    ) -> None:
        """
        Validate schedule configuration before anything
        is written to Supabase.
        """

        if schedule_type == AutomationScheduleType.ONCE:
            run_at = schedule_data.get("run_at")

            if not run_at:
                raise ValueError(
                    "ONCE automation requires "
                    "schedule_data.run_at."
                )

            try:
                parsed = datetime.fromisoformat(
                    str(run_at)
                )
            except ValueError as error:
                raise ValueError(
                    "schedule_data.run_at must be "
                    "a valid ISO datetime."
                ) from error

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            if parsed <= datetime.now(timezone.utc):
                raise ValueError(
                    "schedule_data.run_at must be "
                    "in the future."
                )

            return

        if schedule_type == AutomationScheduleType.INTERVAL:
            raw_interval = schedule_data.get(
                "interval_seconds"
            )

            try:
                interval = int(raw_interval)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "INTERVAL automation requires "
                    "a valid integer interval_seconds."
                ) from error

            if interval <= 0:
                raise ValueError(
                    "INTERVAL automation requires "
                    "a positive interval_seconds."
                )

            return

        if schedule_type == AutomationScheduleType.CRON:
            expression = str(
                schedule_data.get(
                    "expression",
                    "",
                )
            ).strip()

            if not expression:
                raise ValueError(
                    "CRON automation requires "
                    "schedule_data.expression."
                )

            try:
                from croniter import croniter

                croniter(
                    expression,
                    datetime.now(timezone.utc),
                )
            except Exception as error:
                raise ValueError(
                    "schedule_data.expression must be "
                    "a valid cron expression."
                ) from error

            return

        raise ValueError(
            "Unsupported automation schedule type."
        )

    # ========================================================
    # INITIAL SCHEDULE
    # ========================================================

    @staticmethod
    def _initial_next_run(
        schedule_type: AutomationScheduleType,
        schedule_data: dict[str, Any],
    ) -> datetime | None:
        """
        Calculate the first execution time.
        """

        if schedule_type == AutomationScheduleType.ONCE:
            value = schedule_data.get("run_at")

            if value is None:
                return None

            parsed = datetime.fromisoformat(
                str(value)
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        if schedule_type == AutomationScheduleType.INTERVAL:
            interval = int(
                schedule_data[
                    "interval_seconds"
                ]
            )

            return (
                datetime.now(timezone.utc)
                + timedelta(seconds=interval)
            )

        if schedule_type == AutomationScheduleType.CRON:
            from croniter import croniter

            expression = str(
                schedule_data["expression"]
            ).strip()

            cron = croniter(
                expression,
                datetime.now(timezone.utc),
            )

            next_run = cron.get_next(
                datetime
            )

            if next_run.tzinfo is None:
                next_run = next_run.replace(
                    tzinfo=timezone.utc
                )

            return next_run

        return None

    # ========================================================
    # RESUME SCHEDULE
    # ========================================================

    @staticmethod
    def _resume_next_run(
        automation: Automation,
    ) -> datetime:
        """
        Calculate the next valid execution after resume.
        """

        now = datetime.now(timezone.utc)

        if (
            automation.schedule_type
            == AutomationScheduleType.ONCE
        ):
            run_at = automation.schedule_data.get(
                "run_at"
            )

            if not run_at:
                raise ValueError(
                    "ONCE automation has no run_at value."
                )

            next_run = datetime.fromisoformat(
                str(run_at)
            )

            if next_run.tzinfo is None:
                next_run = next_run.replace(
                    tzinfo=timezone.utc
                )

            if next_run <= now:
                raise ValueError(
                    "The scheduled time for this "
                    "one-time automation has already passed."
                )

            return next_run

        if (
            automation.schedule_type
            == AutomationScheduleType.INTERVAL
        ):
            interval = int(
                automation.schedule_data.get(
                    "interval_seconds",
                    0,
                )
            )

            if interval <= 0:
                raise ValueError(
                    "Automation has an invalid "
                    "interval_seconds value."
                )

            return now + timedelta(
                seconds=interval
            )

        if (
            automation.schedule_type
            == AutomationScheduleType.CRON
        ):
            from croniter import croniter

            expression = str(
                automation.schedule_data.get(
                    "expression",
                    "",
                )
            ).strip()

            if not expression:
                raise ValueError(
                    "Automation has no cron expression."
                )

            cron = croniter(
                expression,
                now,
            )

            next_run = cron.get_next(
                datetime
            )

            if next_run.tzinfo is None:
                next_run = next_run.replace(
                    tzinfo=timezone.utc
                )

            return next_run

        raise ValueError(
            "Unsupported automation schedule type."
        )