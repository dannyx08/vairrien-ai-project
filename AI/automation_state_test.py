import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from vairrien_ai.automation import (
    Automation,
    AutomationRun,
    AutomationScheduleType,
    AutomationRunStatus,
    AutomationStateStore,
)


async def main():
    store = AutomationStateStore()

    user_id = f"automation-test-user-{uuid4().hex[:8]}"
    conversation_id = f"automation-test-conversation-{uuid4().hex[:8]}"
    automation_id = f"automation-test-{uuid4().hex[:8]}"
    run_id = f"automation-run-{uuid4().hex[:8]}"

    now = datetime.now(timezone.utc)

    automation = Automation(
        id=automation_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name="Persistence Test",
        description="Tests automation persistence in Supabase.",
        schedule_type=AutomationScheduleType.ONCE,
        schedule_data={
            "run_at": (now + timedelta(minutes=5)).isoformat(),
        },
        action_data={
            "type": "test",
            "message": "Automation persistence works.",
        },
        next_run_at=now + timedelta(minutes=5),
    )

    print("1. SAVING AUTOMATION...")
    saved = await store.save_automation(automation)
    print("   SAVED:", bool(saved))

    print("2. LOADING AUTOMATION...")
    loaded = await store.load_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    if loaded is None:
        raise RuntimeError("Automation could not be loaded from Supabase.")

    print("   LOADED:", loaded.id)
    print("   NAME:", loaded.name)
    print("   STATUS:", loaded.status.value)

    assert loaded.id == automation_id
    assert loaded.user_id == user_id
    assert loaded.conversation_id == conversation_id
    assert loaded.name == "Persistence Test"
    assert loaded.schedule_type == AutomationScheduleType.ONCE
    assert loaded.action_data["type"] == "test"

    print("3. TESTING ACTIVE AUTOMATIONS...")
    active = await store.load_active_automations(
        user_id=user_id,
    )

    matching = [
        item
        for item in active
        if item.id == automation_id
    ]

    assert matching, "Saved automation was not found in active automations."

    print("   ACTIVE LOOKUP: OK")

    print("4. SAVING AUTOMATION RUN...")

    run = AutomationRun(
        id=run_id,
        automation_id=automation_id,
        user_id=user_id,
        status=AutomationRunStatus.RUNNING,
        started_at=now,
        attempts=1,
    )

    await store.save_run(run)

    run.mark_completed(
        {
            "message": "Automation run completed.",
            "test": True,
        }
    )

    await store.save_run(run)

    print("   RUN SAVED")

    print("5. LOADING AUTOMATION RUN HISTORY...")

    runs = await store.load_runs(
        user_id=user_id,
        automation_id=automation_id,
    )

    matching_runs = [
        item
        for item in runs
        if item.id == run_id
    ]

    if not matching_runs:
        raise RuntimeError(
            "Automation run could not be loaded from Supabase."
        )

    loaded_run = matching_runs[0]

    print("   RUN ID:", loaded_run.id)
    print("   RUN STATUS:", loaded_run.status.value)
    print("   RUN RESULT:", loaded_run.result)

    assert loaded_run.id == run_id
    assert loaded_run.automation_id == automation_id
    assert loaded_run.status == AutomationRunStatus.COMPLETED
    assert loaded_run.result["test"] is True

    print("6. DELETING AUTOMATION...")

    await store.delete_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    deleted = await store.load_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    assert deleted is None

    print("   DELETE: OK")

    print()
    print("AUTOMATION PERSISTENCE: OK")


if __name__ == "__main__":
    asyncio.run(main())