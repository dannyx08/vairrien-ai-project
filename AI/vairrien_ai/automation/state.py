from __future__ import annotations

from typing import Any

from vairrien_ai.automation.models import (
    Automation,
    AutomationRun,
)
from vairrien_ai.memory.supabase import SupabaseStorage


class AutomationStateStore:
    """
    Persistent state store for Vairrien automations.

    Provides:
    - save automation
    - load automation
    - list active automations
    - find due automations
    - delete automation
    - save automation runs
    - load automation run history
    """

    def __init__(
        self,
        storage: SupabaseStorage | None = None,
    ):
        self.storage = storage or SupabaseStorage()

    async def save_automation(
        self,
        automation: Automation,
    ) -> dict[str, Any]:
        return await self.storage.save_automation(
            user_id=automation.user_id,
            conversation_id=automation.conversation_id,
            automation_data=automation.to_dict(),
        )

    async def load_automation(
        self,
        *,
        user_id: str,
        automation_id: str,
    ) -> Automation | None:

        record = await self.storage.get_automation(
            user_id=user_id,
            automation_id=automation_id,
        )

        if record is None:
            return None

        return Automation.from_dict(record)

    async def load_active_automations(
        self,
        *,
        user_id: str,
    ) -> list[Automation]:

        records = await self.storage.get_active_automations(
            user_id=user_id,
        )

        return [
            Automation.from_dict(record)
            for record in records
        ]

    async def load_due_automations(
        self,
        *,
        before: str,
    ) -> list[Automation]:

        records = await self.storage.get_due_automations(
            before=before,
        )

        return [
            Automation.from_dict(record)
            for record in records
        ]

    async def delete_automation(
        self,
        *,
        user_id: str,
        automation_id: str,
    ) -> None:

        await self.storage.delete_automation(
            user_id=user_id,
            automation_id=automation_id,
        )

    async def save_run(
        self,
        run: AutomationRun,
    ) -> dict[str, Any]:

        return await self.storage.save_automation_run(
            run_data=run.to_dict(),
        )

    async def load_runs(
        self,
        *,
        user_id: str,
        automation_id: str,
        limit: int = 50,
    ) -> list[AutomationRun]:

        records = await self.storage.get_automation_runs(
            user_id=user_id,
            automation_id=automation_id,
            limit=limit,
        )

        return [
            AutomationRun.from_dict(record)
            for record in records
        ]