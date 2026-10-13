import asyncio
import json

from vairrien_ai.planning.models import (
    Plan,
    PlanTask,
    TaskStatus,
)
from vairrien_ai.planning.executor import PlanExecutor
from vairrien_ai.planning.recovery import TaskRecovery


class IntegrationModel:
    """
    Deterministic model used only to test the planning/recovery chain.

    step-1 succeeds immediately.

    step-2 intentionally fails twice through a tool and then
    succeeds on the third attempt.

    step-3 succeeds only after step-2 has completed.
    """

    def __init__(self):
        self.step_2_attempts = 0

    async def generate(self, *, messages, tools=None):
        task_context = json.loads(
            messages[-1]["content"]
        )

        current_task = task_context["current_task"]
        task_id = current_task["id"]

        if task_id == "step-1":
            return {
                "role": "assistant",
                "content": "Step 1 completed successfully.",
                "tool_calls": [],
            }

        if task_id == "step-2":
            self.step_2_attempts += 1

            if self.step_2_attempts <= 2:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": (
                                f"step-2-call-"
                                f"{self.step_2_attempts}"
                            ),
                            "function": {
                                "name": "flaky_tool",
                                "arguments": "{}",
                            },
                        }
                    ],
                }

            return {
                "role": "assistant",
                "content": "Step 2 recovered successfully.",
                "tool_calls": [],
            }

        if task_id == "step-3":
            return {
                "role": "assistant",
                "content": (
                    "Step 3 executed after step-2 recovery."
                ),
                "tool_calls": [],
            }

        return {
            "role": "assistant",
            "content": "Task completed.",
            "tool_calls": [],
        }


class IntegrationToolRegistry:
    """
    Minimal tool registry containing one deliberately failing tool.

    The failure must propagate into TaskRecovery.
    """

    def list_tools(self):
        return [
            {
                "name": "flaky_tool",
                "description": (
                    "A deliberately failing test tool."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                "enabled": True,
            }
        ]

    async def execute(
        self,
        name,
        *,
        context,
        **arguments,
    ):
        return {
            "status": "error",
            "error": (
                "Intentional integration-test failure."
            ),
            "tool": name,
        }


async def main():
    model = IntegrationModel()
    tools = IntegrationToolRegistry()
    recovery = TaskRecovery(max_attempts=3)

    executor = PlanExecutor(
        model=model,
        tools=tools,
        recovery=recovery,
    )

    plan = Plan(
        id="integration-plan",
        goal=(
            "Verify multi-step execution with "
            "failure recovery."
        ),
        tasks=[
            PlanTask(
                id="step-1",
                title="Complete first step",
                description=(
                    "Complete the first task."
                ),
            ),
            PlanTask(
                id="step-2",
                title="Complete recoverable step",
                description=(
                    "This task intentionally fails "
                    "twice before succeeding."
                ),
                dependencies=["step-1"],
            ),
            PlanTask(
                id="step-3",
                title="Continue after recovery",
                description=(
                    "This task must execute after "
                    "step-2 recovers."
                ),
                dependencies=["step-2"],
            ),
        ],
    )

    results = await executor.execute_ready_tasks(
        plan=plan,
        user_id="integration-test-user",
        conversation_id="integration-test-conversation",
    )

    print("PLAN STATUS:")
    print(plan.status.value)

    print("\nTASK STATUSES:")

    for task in plan.tasks:
        print(
            f"{task.id}: "
            f"{task.status.value} "
            f"(attempts={task.attempts})"
        )

    print("\nTASK RESULTS:")

    for task in plan.tasks:
        print(
            f"{task.id}: "
            f"{task.result}"
        )

    print("\nEXECUTION RESULTS:")

    for result in results:
        print(result)

    # --------------------------------------------------------------
    # Structural assertions
    # --------------------------------------------------------------

    assert plan.status == plan.status.COMPLETED

    step_1 = plan.get_task("step-1")
    step_2 = plan.get_task("step-2")
    step_3 = plan.get_task("step-3")

    assert step_1 is not None
    assert step_2 is not None
    assert step_3 is not None

    # Every task must complete.
    assert step_1.status == TaskStatus.COMPLETED
    assert step_2.status == TaskStatus.COMPLETED
    assert step_3.status == TaskStatus.COMPLETED

    # Step 1 should run exactly once.
    assert step_1.attempts == 1

    # Step 2 must fail twice and succeed on attempt three.
    assert step_2.attempts == 3

    # Step 3 should execute exactly once after step 2 recovers.
    assert step_3.attempts == 1

    # Verify the actual results.
    assert (
        step_1.result["result"]
        == "Step 1 completed successfully."
    )

    assert (
        step_2.result["result"]
        == "Step 2 recovered successfully."
    )

    assert (
        step_3.result["result"]
        == "Step 3 executed after step-2 recovery."
    )

    # Verify execution order.
    task_ids = [
        result["task_id"]
        for result in results
    ]

    assert task_ids == [
        "step-1",
        "step-2",
        "step-3",
    ]

    # Verify that recovery actually happened on step 2.
    step_2_execution = next(
        result
        for result in results
        if result["task_id"] == "step-2"
    )

    assert step_2_execution["recovered"] is True
    assert step_2_execution["attempts"] == 3

    print(
        "\nPLANNING RECOVERY INTEGRATION: OK"
    )


if __name__ == "__main__":
    asyncio.run(main())