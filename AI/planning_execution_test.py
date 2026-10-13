import asyncio

from vairrien_ai.model.openrouter import OpenRouterProvider
from vairrien_ai.planning import (
    Plan,
    PlanExecutor,
    PlanTask,
)


async def main():
    model = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free"
    )

    plan = Plan(
        id="execution-test",
        goal="Answer a simple research question.",
        tasks=[
            PlanTask(
                id="step-1",
                title="Answer the user's question",
                description=(
                    "Provide a clear answer to: "
                    "What is the capital of Nigeria?"
                ),
                capabilities=["reasoning"],
            ),
        ],
    )

    executor = PlanExecutor(
        model=model,
        tools=None,
    )

    results = await executor.execute_ready_tasks(
        plan=plan,
        user_id="planning-test-user",
        conversation_id="planning-test-conversation",
    )

    print("PLAN STATUS:")
    print(plan.status.value)

    print("\nTASK STATUS:")
    print(plan.tasks[0].status.value)

    print("\nTASK RESULT:")
    print(plan.tasks[0].result)

    print("\nEXECUTION RESULTS:")
    print(results)

    print("\nPLAN EXECUTOR: OK")


if __name__ == "__main__":
    asyncio.run(main())