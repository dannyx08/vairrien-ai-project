from __future__ import annotations

from typing import Any

from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.planning.models import Plan, TaskStatus


class TaskStateStore:
    """
    Persistent state store for Vairrien task plans.

    Uses the existing Supabase storage layer.

    Handles:
    - saving plans
    - loading plans
    - finding active plans
    - resuming interrupted plans
    - deleting plans
    """

    def __init__(
        self,
        storage: SupabaseStorage | None = None,
    ):
        self.storage = storage or SupabaseStorage()

    async def save_plan(
        self,
        *,
        user_id: str,
        conversation_id: str,
        plan: Plan,
    ) -> dict[str, Any]:
        return await self.storage.save_task_plan(
            user_id=user_id,
            conversation_id=conversation_id,
            plan_data=plan.to_dict(),
        )

    async def load_plan(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> Plan | None:
        record = await self.storage.get_task_plan(
            user_id=user_id,
            plan_id=plan_id,
        )

        if record is None:
            return None

        plan_data = record.get("plan_data")

        if not isinstance(plan_data, dict):
            raise RuntimeError(
                "Stored task plan contains invalid plan data."
            )

        return Plan.from_dict(plan_data)

    async def load_active_plan(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> Plan | None:
        record = await self.storage.get_active_task_plan(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if record is None:
            return None

        plan_data = record.get("plan_data")

        if not isinstance(plan_data, dict):
            raise RuntimeError(
                "Stored active task plan contains invalid plan data."
            )

        return Plan.from_dict(plan_data)

    async def resume_plan(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> Plan | None:
        plan = await self.load_plan(
            user_id=user_id,
            plan_id=plan_id,
        )

        if plan is None:
            return None

        # A process can terminate while a task is marked
        # in_progress. On resume, that task must become
        # runnable again instead of remaining permanently
        # stuck.
        for task in plan.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.PENDING
                task.error = None

        return plan

    async def delete_plan(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> None:
        await self.storage.delete_task_plan(
            user_id=user_id,
            plan_id=plan_id,
        )