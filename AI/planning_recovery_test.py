import asyncio

from vairrien_ai.planning import (
    Plan,
    PlanTask,
)

from vairrien_ai.planning.recovery import (
    TaskRecovery,
)


async def main():
    task = PlanTask(
        id="step-1",
        title="Recoverable task",
    )

    recovery = TaskRecovery(
        max_attempts=3,
    )

    attempts = 0

    async def execute():
        nonlocal attempts

        attempts += 1

        print(
            f"EXECUTION ATTEMPT: {attempts}"
        )

        if attempts < 3:
            raise RuntimeError(
                "Temporary execution failure"
            )

        return {
            "message": "Task succeeded after recovery."
        }

    result = await recovery.recover(
        task,
        execute,
    )

    print()
    print("RECOVERY RESULT:")
    print(result)

    print()
    print("TASK STATUS:")
    print(task.status)

    print()
    print("TASK ATTEMPTS:")
    print(task.attempts)


if __name__ == "__main__":
    asyncio.run(main())