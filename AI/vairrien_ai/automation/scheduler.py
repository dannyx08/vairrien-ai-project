from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable

from vairrien_ai.automation.models import Automation
from vairrien_ai.automation.state import AutomationStateStore


AutomationCallback = Callable[
    [Automation],
    Awaitable[None],
]


class AutomationScheduler:
    """
    Native async scheduler for Vairrien automations.

    The scheduler:
    - checks persistent automation state
    - finds due automations
    - prevents duplicate in-process execution
    - hands due automations to the execution callback
    - continues running until stopped
    """

    def __init__(
        self,
        *,
        state_store: AutomationStateStore | None = None,
        poll_interval: float = 5.0,
    ):
        if poll_interval <= 0:
            raise ValueError(
                "poll_interval must be greater than zero."
            )

        self.state_store = (
            state_store or AutomationStateStore()
        )

        self.poll_interval = poll_interval

        self._running = False
        self._task: asyncio.Task | None = None

        self._active_automation_ids: set[str] = set()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_automation_ids(self) -> set[str]:
        return set(self._active_automation_ids)

    async def check_once(
        self,
        callback: AutomationCallback,
    ) -> list[str]:
        """
        Perform one scheduler cycle.

        Returns the IDs of automations handed to the callback.
        """

        now = datetime.now(timezone.utc)

        due_automations = (
            await self.state_store.load_due_automations(
                before=now.isoformat(),
            )
        )

        triggered: list[str] = []

        for automation in due_automations:
            if not automation.is_active():
                continue

            if (
                automation.id
                in self._active_automation_ids
            ):
                continue

            self._active_automation_ids.add(
                automation.id
            )

            triggered.append(automation.id)

            asyncio.create_task(
                self._run_callback(
                    automation,
                    callback,
                )
            )

        return triggered

    async def _run_callback(
        self,
        automation: Automation,
        callback: AutomationCallback,
    ) -> None:
        try:
            await callback(automation)
        finally:
            self._active_automation_ids.discard(
                automation.id
            )

    async def run(
        self,
        callback: AutomationCallback,
    ) -> None:
        """
        Run the scheduler continuously.
        """

        if self._running:
            return

        self._running = True

        try:
            while self._running:
                await self.check_once(callback)

                await asyncio.sleep(
                    self.poll_interval
                )

        except asyncio.CancelledError:
            raise

        finally:
            self._running = False

    async def start(
        self,
        callback: AutomationCallback,
    ) -> None:
        """
        Start the scheduler as a background task.
        """

        if self._running:
            return

        self._task = asyncio.create_task(
            self.run(callback)
        )

    async def stop(self) -> None:
        """
        Stop the scheduler cleanly.
        """

        self._running = False

        if self._task is not None:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        self._active_automation_ids.clear()