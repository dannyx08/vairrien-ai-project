import asyncio
import uuid

from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.planning.models import (
    Plan,
    PlanTask,
    TaskStatus,
)
from vairrien_ai.planning.state import TaskStateStore


async def main():
    storage = SupabaseStorage()
    state_store = TaskStateStore(storage)

    user_id = "task-state-test-user"
    conversation_id = "task-state-test-conversation"

    plan = Plan(
        id=f"state-test-{uuid.uuid4().hex[:8]}",
        goal="Test persistent task state",
        tasks=[
            PlanTask(
                id="step-1",
                title="Complete first task",
            ),
            PlanTask(
                id="step-2",
                title="Complete second task",
                dependencies=["step-1"],
            ),
        ],
    )

    # --------------------------------------------------------
    # SAVE INITIAL PLAN
    # --------------------------------------------------------

    await state_store.save_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan=plan,
    )

    print("INITIAL PLAN SAVED")
    print("PLAN ID:", plan.id)

    # --------------------------------------------------------
    # CHANGE TASK STATE
    # --------------------------------------------------------

    step_1 = plan.get_task("step-1")

    if step_1 is None:
        raise RuntimeError("step-1 was not found.")

    step_1.mark_in_progress()
    step_1.mark_completed(
        {
            "message": "First task completed.",
        }
    )

    await state_store.save_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan=plan,
    )

    print("UPDATED PLAN SAVED")
    print("STEP-1 STATUS:", step_1.status.value)

    # --------------------------------------------------------
    # RELOAD FROM SUPABASE
    # --------------------------------------------------------

    loaded_plan = await state_store.load_plan(
        user_id=user_id,
        plan_id=plan.id,
    )

    if loaded_plan is None:
        raise RuntimeError(
            "Plan could not be loaded from Supabase."
        )

    loaded_step_1 = loaded_plan.get_task("step-1")

    if loaded_step_1 is None:
        raise RuntimeError(
            "step-1 was not found after reload."
        )

    print("PLAN RELOADED")
    print(
        "RELOADED STEP-1 STATUS:",
        loaded_step_1.status.value,
    )
    print(
        "RELOADED STEP-1 RESULT:",
        loaded_step_1.result,
    )

    # --------------------------------------------------------
    # VERIFY PERSISTENCE
    # --------------------------------------------------------

    assert loaded_plan.id == plan.id
    assert loaded_plan.goal == plan.goal

    assert (
        loaded_step_1.status
        == TaskStatus.COMPLETED
    )

    assert loaded_step_1.result == {
        "message": "First task completed.",
    }

    # --------------------------------------------------------
    # VERIFY CONTINUATION
    # --------------------------------------------------------

    ready_tasks = loaded_plan.ready_tasks()

    print(
        "READY TASKS:",
        [task.id for task in ready_tasks],
    )

    assert "step-2" in [
        task.id for task in ready_tasks
    ]

    print()
    print("TASK STATE PERSISTENCE: OK")


if __name__ == "__main__":
    asyncio.run(main())