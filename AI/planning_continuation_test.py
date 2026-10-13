from __future__ import annotations

import asyncio
import uuid

from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.planning.executor.engine import PlanExecutor
from vairrien_ai.planning.models import Plan, PlanTask, TaskStatus
from vairrien_ai.planning.state import TaskStateStore


class FakeModel:
    """
    Minimal model used only for testing task continuation.

    It returns a successful response for whichever task the
    executor asks it to perform.
    """

    async def generate(self, messages, **kwargs):
        task_id = "unknown"

        for message in messages:
            content = str(message.get("content", ""))

            if "step-1" in content:
                task_id = "step-1"
                break

            if "step-2" in content:
                task_id = "step-2"
                break

            if "step-3" in content:
                task_id = "step-3"
                break

        return {
            "role": "assistant",
            "content": f"{task_id} completed successfully.",
            "tool_calls": [],
        }


async def main():
    user_id = f"continuation-test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conversation-{uuid.uuid4().hex[:8]}"
    plan_id = f"continuation-plan-{uuid.uuid4().hex[:8]}"

    storage = SupabaseStorage()
    state_store = TaskStateStore(storage=storage)

    model = FakeModel()

    # ---------------------------------------------------------
    # 1. Create a three-step dependent plan
    # ---------------------------------------------------------

    plan = Plan(
        id=plan_id,
        goal="Test interruption and continuation of a multi-step task",
        tasks=[
            PlanTask(
                id="step-1",
                title="Complete first step",
                description="Complete the first step.",
            ),
            PlanTask(
                id="step-2",
                title="Complete second step",
                description="Complete the second step.",
                dependencies=["step-1"],
            ),
            PlanTask(
                id="step-3",
                title="Complete third step",
                description="Complete the third step.",
                dependencies=["step-2"],
            ),
        ],
    )

    await state_store.save_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan=plan,
    )

    print("INITIAL PLAN SAVED")
    print(f"PLAN ID: {plan.id}")

    # ---------------------------------------------------------
    # 2. Start execution
    # ---------------------------------------------------------

    executor = PlanExecutor(
        model=model,
        tools=None,
        state_store=state_store,
    )

    first_task = plan.get_task("step-1")

    if first_task is None:
        raise RuntimeError("step-1 was not found.")

    result = await executor.execute_task(
        plan=plan,
        task=first_task,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if result.get("status") != "success":
        raise RuntimeError(
            f"step-1 failed: {result}"
        )

    await state_store.save_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan=plan,
    )

    print(
        f"STEP-1 STATUS: "
        f"{first_task.status.value}"
    )

    if first_task.status != TaskStatus.COMPLETED:
        raise RuntimeError(
            "step-1 did not complete."
        )

    # ---------------------------------------------------------
    # 3. Simulate an interruption during step-2
    # ---------------------------------------------------------

    second_task = plan.get_task("step-2")

    if second_task is None:
        raise RuntimeError("step-2 was not found.")

    second_task.mark_in_progress()

    await state_store.save_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan=plan,
    )

    print("SIMULATED INTERRUPTION")

    # ---------------------------------------------------------
    # 4. Verify the interrupted state survived persistence
    # ---------------------------------------------------------

    reload_store = TaskStateStore(
        storage=SupabaseStorage()
    )

    persisted_plan = await reload_store.load_plan(
        user_id=user_id,
        plan_id=plan_id,
    )

    if persisted_plan is None:
        raise RuntimeError(
            "Persisted plan could not be reloaded."
        )

    persisted_step_1 = persisted_plan.get_task("step-1")
    persisted_step_2 = persisted_plan.get_task("step-2")

    if persisted_step_1 is None:
        raise RuntimeError(
            "Persisted step-1 was not found."
        )

    if persisted_step_2 is None:
        raise RuntimeError(
            "Persisted step-2 was not found."
        )

    print(
        f"PERSISTED STEP-1: "
        f"{persisted_step_1.status.value}"
    )

    print(
        f"PERSISTED STEP-2: "
        f"{persisted_step_2.status.value}"
    )

    if persisted_step_1.status != TaskStatus.COMPLETED:
        raise RuntimeError(
            "Persisted step-1 is not completed."
        )

    if persisted_step_2.status != TaskStatus.IN_PROGRESS:
        raise RuntimeError(
            "step-2 was not persisted as in_progress."
        )

    # ---------------------------------------------------------
    # 5. Simulate a completely new application process
    # ---------------------------------------------------------

    resumed_store = TaskStateStore(
        storage=SupabaseStorage()
    )

    resumed_executor = PlanExecutor(
        model=FakeModel(),
        tools=None,
        state_store=resumed_store,
    )

    # ---------------------------------------------------------
    # 6. Resume the interrupted plan
    # ---------------------------------------------------------

    execution_results = await resumed_executor.resume_plan(
        user_id=user_id,
        conversation_id=conversation_id,
        plan_id=plan_id,
    )

    print("RESUME EXECUTION RESULTS:")

    for execution_result in execution_results:
        print(execution_result)

    # ---------------------------------------------------------
    # 7. Reload the final persisted state
    # ---------------------------------------------------------

    final_plan = await resumed_store.load_plan(
        user_id=user_id,
        plan_id=plan_id,
    )

    if final_plan is None:
        raise RuntimeError(
            "Final persisted plan could not be reloaded."
        )

    print(
        f"RESUMED PLAN STATUS: "
        f"{final_plan.status.value}"
    )

    print("FINAL TASK STATUSES:")

    for task in final_plan.tasks:
        print(
            f"{task.id}: "
            f"{task.status.value} "
            f"(attempts={task.attempts})"
        )

    # ---------------------------------------------------------
    # 8. Verify complete continuation
    # ---------------------------------------------------------

    if final_plan.status.value != "completed":
        raise RuntimeError(
            "Resumed plan did not reach completed status."
        )

    for task in final_plan.tasks:
        if task.status != TaskStatus.COMPLETED:
            raise RuntimeError(
                f"{task.id} did not complete after resume."
            )

    # ---------------------------------------------------------
    # 9. Success
    # ---------------------------------------------------------

    print("PLANNING CONTINUATION: OK")


if __name__ == "__main__":
    asyncio.run(main())