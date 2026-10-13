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
    print("1. INITIALIZING AUTOMATION SYSTEM...")

    state_store = AutomationStateStore(storage=storage)

    engine = AutomationEngine(
        orchestrator=orchestrator,
        state_store=state_store,
        poll_interval=1.0,
    )

    print("   AUTOMATION SYSTEM: OK")

    print("2. CREATING CONVERSATION...")

    conversation = await storage.get_or_create_conversation(
        user_id=USER_ID
    )

    conversation_id = conversation["id"]

    print("   CONVERSATION:", conversation_id)

    print("3. CREATING ONE-TIME AUTOMATION...")

    automation = Automation(
        id="test-automation-vairrien",
        user_id=USER_ID,
        conversation_id=conversation_id,
        name="Vairrien Automation Test",
        description="End-to-end automation test",
        schedule_type=AutomationScheduleType.ONCE,
        schedule_data={
            "run_at": (
                datetime.now(timezone.utc)
                - timedelta(seconds=1)
            ).isoformat()
        },
        action_data={
            "type": "vairrien_task",
            "message": (
                "This is an automated Vairrien test. "
                "Reply with exactly: Automation executed successfully."
            ),
        },
        status=AutomationStatus.ACTIVE,
        next_run_at=(
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ),
    )

    await state_store.save_automation(automation)

    print("   AUTOMATION SAVED:", automation.id)

    print("4. READING AUTOMATION FROM SUPABASE...")

    loaded = await state_store.load_automation(
        user_id=USER_ID,
        automation_id=automation.id,
    )

    if loaded is None:
        raise RuntimeError(
            "Automation could not be loaded from Supabase."
        )

    print("   AUTOMATION LOADED:", loaded.id)
    print("   STATUS:", loaded.status.value)

    print("5. CHECKING DUE AUTOMATIONS...")

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
            "Test automation was not detected as due."
        )

    print("   DUE AUTOMATION DETECTED")

    print("6. EXECUTING AUTOMATION...")

    run = await engine.execute_once(loaded)

    print("   RUN STATUS:", run.status.value)

    if run.result:
        print("   RESULT:", run.result)

    if run.error:
        print("   ERROR:", run.error)

    print("7. VERIFYING AUTOMATION STATE...")

    updated = await state_store.load_automation(
        user_id=USER_ID,
        automation_id=automation.id,
    )

    if updated is None:
        raise RuntimeError(
            "Updated automation could not be loaded."
        )

    print("   FINAL STATUS:", updated.status.value)
    print("   RUN COUNT:", updated.run_count)

    print("8. VERIFYING RUN HISTORY...")

    runs = await state_store.load_runs(
        user_id=USER_ID,
        automation_id=automation.id,
    )

    print("   RUN HISTORY COUNT:", len(runs))

    if not runs:
        raise RuntimeError(
            "Automation run was not saved."
        )

    print("9. AUTOMATION INTEGRATION TEST: SUCCESS")


if __name__ == "__main__":
    asyncio.run(main())
