import asyncio

from vairrien_ai.model.openrouter import OpenRouterProvider
from vairrien_ai.planning import VairrienPlanner


async def main():
    model = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free"
    )

    planner = VairrienPlanner(model)

    plan = await planner.create_plan(
        """
        Research the current state of renewable energy adoption in Nigeria,
        compare the major findings from multiple reliable sources, identify
        the main challenges, and give me a concise evidence-based conclusion.
        """
    )

    print("PLAN GOAL:")
    print(plan.goal)

    print("\nTASKS:")

    for task in plan.tasks:
        print(f"{task.id}: {task.title}")
        print(f"  Dependencies: {task.dependencies}")
        print(f"  Capabilities: {task.capabilities}")

    print("\nREADY TASKS:")
    print([task.id for task in plan.ready_tasks()])

    print("\nPLANNER: OK")


if __name__ == "__main__":
    asyncio.run(main())