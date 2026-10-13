from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.tools.automation import AutomationTool


USER_ID = "6075bbfd-4296-432a-83ae-107b010c23a2"


async def main() -> None:
    print("1. INITIALIZING STORAGE...")

    storage = SupabaseStorage()
    tool = AutomationTool(storage=storage)

    print("   STORAGE: OK")

    print("2. CREATING/LOADING CONVERSATION...")

    conversation = await storage.get_or_create_conversation(
        user_id=USER_ID,
        title="Live Automation Test",
    )

    conversation_id = conversation["id"]

    print(f"   CONVERSATION: {conversation_id}")

    print("3. CREATING LIVE AUTOMATION...")

    run_at = (
        datetime.now(timezone.utc) + timedelta(seconds=15)
    ).isoformat()

    result = await tool.create(
        context={
            "user_id": USER_ID,
            "conversation_id": conversation_id,
        },
        name="live-scheduler-test",
        description="Final live scheduler integration test",
        schedule_type="once",
        schedule_data={
            "run_at": run_at,
        },
        message="Reply with AUTOMATION LIVE TEST.",
    )

    print("   AUTOMATION CREATED")
    print(f"   ID: {result['id']}")
    print(f"   STATUS: {result['status']}")
    print(f"   NEXT RUN: {result['next_run_at']}")

    automation_id = result["id"]

    print()
    print("4. WAITING FOR LIVE SCHEDULER...")
    print("   The server should detect and execute this automation.")
    print("   Waiting 30 seconds...")

    await asyncio.sleep(30)

    print()
    print("5. VERIFYING AUTOMATION...")

    stored = await storage.get_automation(
        automation_id=automation_id,
        user_id=USER_ID,
    )

    if stored is None:
        print("   ERROR: AUTOMATION NOT FOUND")
        return

    print(f"   STATUS: {stored['status']}")
    print(f"   RUN COUNT: {stored.get('run_count', 0)}")
    print(f"   LAST RUN: {stored.get('last_run_at')}")
    print(f"   LAST ERROR: {stored.get('last_error')}")

    print()
    print("6. LOADING RUN HISTORY...")

    runs = await storage.get_automation_runs(
        automation_id=automation_id,
        user_id=USER_ID,
    )

    print(f"   RUN HISTORY COUNT: {len(runs)}")

    for run in runs:
        print(f"   RUN STATUS: {run.get('status')}")
        print(f"   RUN RESULT: {run.get('result')}")
        print(f"   RUN ERROR: {run.get('error')}")

    print()
    print("LIVE AUTOMATION TEST COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
