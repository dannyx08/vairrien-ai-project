import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from vairrien_ai.automation import (
    Automation,
    AutomationEngine,
    AutomationScheduleType,
    AutomationStateStore,
)


async def main():
    store = AutomationStateStore()

    user_id = f"engine-test-user-{uuid4().hex[:8]}"
    conversation_id = (
        f"engine-test-conversation-{uuid4().hex[:8]}"
    )

    once_id = f"engine-once-{uuid4().hex[:8]}"
    interval_id = f"engine-interval-{uuid4().hex[:8]}"

    now = datetime.now(timezone.utc)

    once_automation = Automation(
        id=once_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name="One Time Engine Test",
        description="Tests one-time automation execution.",
        schedule_type=AutomationScheduleType.ONCE,
        schedule_data={
            "run_at": (
                now - timedelta(seconds=5)
            ).isoformat(),
        },
        action_data={
            "type": "test_action",
            "message": "One-time action executed.",
        },
        next_run_at=now - timedelta(seconds=5),
    )

    interval_automation = Automation(
        id=interval_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name="Interval Engine Test",
        description="Tests recurring interval scheduling.",
        schedule_type=AutomationScheduleType.INTERVAL,
        schedule_data={
            "interval_seconds": 60,
        },
        action_data={
            "type": "test_action",
            "message": "Interval action executed.",
        },
        next_run_at=now - timedelta(seconds=5),
    )

    await store.save_automation(
        once_automation
    )

    await store.save_automation(
        interval_automation
    )

    engine = AutomationEngine(
        state_store=store,
        poll_interval=1.0,
    )

    executions = []

    async def test_action(automation):
        executions.append(
            automation.id
        )

        return {
            "success": True,
            "automation_id": automation.id,
            "message": automation.action_data[
                "message"
            ],
        }

    engine.register_action(
        "test_action",
        test_action,
    )

    print("1. EXECUTING ONE-TIME AUTOMATION...")

    once_run = await engine.execute_once(
        once_automation
    )

    print(
        "   STATUS:",
        once_run.status.value,
    )

    assert once_run.status.value == "completed"
    assert once_id in executions

    print("   ONE-TIME EXECUTION: OK")

    print("2. VERIFYING ONE-TIME COMPLETION...")

    loaded_once = await store.load_automation(
        user_id=user_id,
        automation_id=once_id,
    )

    assert loaded_once is not None
    assert loaded_once.status.value == "completed"
    assert loaded_once.next_run_at is None

    print(
        "   STATUS:",
        loaded_once.status.value,
    )
    print(
        "   NEXT RUN:",
        loaded_once.next_run_at,
    )

    print("   ONE-TIME LIFECYCLE: OK")

    print("3. EXECUTING INTERVAL AUTOMATION...")

    interval_run = await engine.execute_once(
        interval_automation
    )

    print(
        "   STATUS:",
        interval_run.status.value,
    )

    assert interval_run.status.value == "completed"
    assert interval_id in executions

    print("   INTERVAL EXECUTION: OK")

    print("4. VERIFYING NEXT INTERVAL...")

    loaded_interval = await store.load_automation(
        user_id=user_id,
        automation_id=interval_id,
    )

    assert loaded_interval is not None
    assert loaded_interval.status.value == "active"
    assert loaded_interval.next_run_at is not None

    print(
        "   STATUS:",
        loaded_interval.status.value,
    )
    print(
        "   NEXT RUN:",
        loaded_interval.next_run_at,
    )

    assert (
        loaded_interval.next_run_at
        > now
    )

    print("   INTERVAL RESCHEDULING: OK")

    print("5. VERIFYING RUN HISTORY...")

    once_runs = await store.load_runs(
        user_id=user_id,
        automation_id=once_id,
    )

    interval_runs = await store.load_runs(
        user_id=user_id,
        automation_id=interval_id,
    )

    assert any(
        run.id == once_run.id
        for run in once_runs
    )

    assert any(
        run.id == interval_run.id
        for run in interval_runs
    )

    print(
        "   ONE-TIME RUNS:",
        len(once_runs),
    )

    print(
        "   INTERVAL RUNS:",
        len(interval_runs),
    )

    print("   RUN HISTORY: OK")

    print("6. CLEANING UP...")

    await store.delete_automation(
        user_id=user_id,
        automation_id=once_id,
    )

    await store.delete_automation(
        user_id=user_id,
        automation_id=interval_id,
    )

    print("   CLEANUP: OK")

    print()
    print("AUTOMATION ENGINE: OK")


if __name__ == "__main__":
    asyncio.run(main())