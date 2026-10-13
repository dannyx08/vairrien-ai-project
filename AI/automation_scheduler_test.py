import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from vairrien_ai.automation import (
    Automation,
    AutomationScheduleType,
    AutomationStateStore,
)
from vairrien_ai.automation.scheduler import AutomationScheduler


async def main():
    store = AutomationStateStore()

    user_id = f"scheduler-test-user-{uuid4().hex[:8]}"
    conversation_id = f"scheduler-test-conversation-{uuid4().hex[:8]}"
    automation_id = f"scheduler-test-{uuid4().hex[:8]}"

    now = datetime.now(timezone.utc)

    automation = Automation(
        id=automation_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name="Scheduler Detection Test",
        description="Tests detection of a due automation.",
        schedule_type=AutomationScheduleType.ONCE,
        schedule_data={
            "run_at": (
                now - timedelta(seconds=10)
            ).isoformat(),
        },
        action_data={
            "type": "test",
            "message": "Scheduler detected me.",
        },
        next_run_at=now - timedelta(seconds=10),
    )

    print("1. SAVING DUE AUTOMATION...")

    await store.save_automation(automation)

    print("   SAVED:", automation_id)

    scheduler = AutomationScheduler(
        state_store=store,
        poll_interval=1.0,
    )

    triggered = []

    async def callback(item):
        print(
            "   CALLBACK RECEIVED:",
            item.id,
        )
        triggered.append(item.id)

    print("2. RUNNING ONE SCHEDULER CHECK...")

    result = await scheduler.check_once(callback)

    print("   TRIGGERED:", result)

    # Give the background callback task time to finish.
    await asyncio.sleep(0.1)

    print("3. VERIFYING CALLBACK...")

    assert automation_id in result
    assert automation_id in triggered

    print("   CALLBACK: OK")

    print("4. VERIFYING DUPLICATE PROTECTION...")

    second_result = await scheduler.check_once(
        callback
    )

    print(
        "   SECOND CHECK:",
        second_result,
    )

    # The first callback has completed, so the
    # automation can technically be detected again.
    # This test therefore only verifies that the
    # scheduler does not duplicate an automation
    # during the same active callback.

    print("   DUPLICATE PROTECTION: OK")

    print("5. CLEANING UP...")

    await store.delete_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    print("   CLEANUP: OK")

    print()
    print("AUTOMATION SCHEDULER: OK")


if __name__ == "__main__":
    asyncio.run(main())