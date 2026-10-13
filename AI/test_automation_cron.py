import asyncio
from datetime import datetime, timedelta, timezone

from vairrien_ai.automation import (
    Automation,
    AutomationEngine,
    AutomationScheduleType,
    AutomationStatus,
    AutomationStateStore,
)
from vairrien_ai.api.server import storage, orchestrator


USER_ID = "6075bbfd-4296-432a-83ae-107b010c23a2"


async def main():
    print("1. INITIALIZING CRON AUTOMATION...")

    state_store = AutomationStateStore(
        storage=storage
    )

    engine = AutomationEngine(
        orchestrator=orchestrator,
        state_store=state_store,
        poll_interval=1.0,
    )

    print("   CRON AUTOMATION: OK")

    print("2. CREATING CONVERSATION...")

    conversation = await storage.get_or_create_conversation(
        user_id=USER_ID
    )

    conversation_id = conversation["id"]

    print("   CONVERSATION:", conversation_id)

    print("3. CREATING CRON AUTOMATION...")

    automation = Automation(
        id="test-cron-vairrien",
        user_id=USER_ID,
        conversation_id=conversation_id,
        name="Vairrien CRON Test",
        description="CRON automation integration test",
        schedule_type=AutomationScheduleType.CRON,
        schedule_data={
            "expression": "* * * * *"
        },
        action_data={
            "type": "vairrien_task",
            "message": (
                "This is a CRON automation test. "
                "Reply with exactly: CRON automation executed."
            ),
        },
        status=AutomationStatus.ACTIVE,
        next_run_at=(
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ),
    )

    await state_store.save_automation(
        automation
    )

    print(
        "   AUTOMATION SAVED:",
        automation.id
    )

    print("4. LOADING DUE AUTOMATION...")

    due = await state_store.load_due_automations(
        before=datetime.now(timezone.utc).isoformat()
    )

    matching = [
        item
        for item in due
        if item.id == automation.id
    ]

    if not matching:
        raise RuntimeError(
            "CRON automation was not detected as due."
        )

    loaded = matching[0]

    print("   DUE AUTOMATION DETECTED")

    print("5. EXECUTING CRON AUTOMATION...")

    run = await engine.execute_once(
        loaded
    )

    print(
        "   RUN STATUS:",
        run.status.value
    )

    if run.result:
        print(
            "   RESULT:",
            run.result
        )

    if run.error:
        print(
            "   ERROR:",
            run.error
        )

    if run.status.value != "completed":
        raise RuntimeError(
            "CRON automation did not complete successfully."
        )

    print("6. VERIFYING NEXT CRON RUN...")

    updated = await state_store.load_automation(
        user_id=USER_ID,
        automation_id=automation.id,
    )

    if updated is None:
        raise RuntimeError(
            "Updated CRON automation could not be loaded."
        )

    print(
        "   STATUS:",
        updated.status.value
    )

    print(
        "   RUN COUNT:",
        updated.run_count
    )

    print(
        "   NEXT RUN:",
        updated.next_run_at
    )

    if updated.status != AutomationStatus.ACTIVE:
        raise RuntimeError(
            "CRON automation should remain active."
        )

    if updated.next_run_at is None:
        raise RuntimeError(
            "CRON automation did not receive a next_run_at."
        )

    print("7. VERIFYING RUN HISTORY...")

    runs = await state_store.load_runs(
        user_id=USER_ID,
        automation_id=automation.id,
    )

    print(
        "   RUN HISTORY COUNT:",
        len(runs)
    )

    if not runs:
        raise RuntimeError(
            "CRON automation run was not persisted."
        )

    print("8. CRON AUTOMATION TEST: SUCCESS")


if __name__ == "__main__":
    asyncio.run(main())