import asyncio
import uuid

from vairrien_ai.automation import (
    Automation,
    AutomationEngine,
    AutomationScheduleType,
)
from vairrien_ai.automation.state import AutomationStateStore
from vairrien_ai.context.engine import ContextEngine
from vairrien_ai.memory.manager import MemoryManager
from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.core.orchestrator import VairrienOrchestrator
from vairrien_ai.tools.registry import ToolRegistry


async def main():
    print("1. INITIALIZING VAIRRIEN COMPONENTS...")

    storage = SupabaseStorage()

    memory = MemoryManager(
        storage=storage,
    )

    tools = ToolRegistry()

    context = ContextEngine(
        memory=memory,
        tools=tools,
    )

    from vairrien_ai.model.openrouter import OpenRouterProvider

    model = OpenRouterProvider(
        model_name="nvidia/nemotron-3-ultra-550b-a55b:free"
    )

    orchestrator = VairrienOrchestrator(
        model=model,
        memory=memory,
        context=context,
        tools=tools,
    )

    state_store = AutomationStateStore(
        storage=storage,
    )

    engine = AutomationEngine(
        state_store=state_store,
        orchestrator=orchestrator,
    )

    print("   COMPONENTS: OK")

    # Supabase conversations.user_id and conversations.id
    # are UUID columns, so use real UUID values.
    user_id = str(uuid.uuid4())

    conversation_id = str(uuid.uuid4())

    automation_id = (
        f"automation-integration-{uuid.uuid4().hex[:8]}"
    )

    print("2. CREATING TEST CONVERSATION...")

    conversation = (
        await storage.get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )
    )

    print(
        f"   USER ID: {user_id}"
    )

    print(
        f"   CONVERSATION ID: {conversation_id}"
    )

    print(
        f"   CONVERSATION CREATED: "
        f"{conversation.get('id')}"
    )

    automation = Automation(
        id=automation_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name="Vairrien Integration Test",
        description=(
            "Test that an automation can invoke "
            "Vairrien's reasoning system."
        ),
        schedule_type=AutomationScheduleType.ONCE,
        schedule_data={},
        action_data={
            "type": "vairrien_task",
            "message": (
                "This is an automation integration test. "
                "Reply with exactly: "
                "VAIRRIEN AUTOMATION RESPONSE OK"
            ),
        },
    )

    print("3. SAVING AUTOMATION...")

    await state_store.save_automation(
        automation
    )

    print(
        f"   AUTOMATION ID: {automation_id}"
    )

    print("4. EXECUTING AUTOMATION...")

    result = await engine.execute(
        automation
    )

    print("5. AUTOMATION RESULT:")
    print(result)

    if result.status.value != "completed":
        raise RuntimeError(
            "Automation execution failed: "
            f"{result.error}"
        )

    print("6. VERIFYING LIFECYCLE...")

    loaded = await state_store.load_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    if loaded is None:
        raise RuntimeError(
            "Automation could not be reloaded."
        )

    print(
        f"   STATUS: {loaded.status.value}"
    )

    print(
        f"   RUN COUNT: {loaded.run_count}"
    )

    print(
        f"   NEXT RUN: {loaded.next_run_at}"
    )

    runs = await state_store.load_runs(
        user_id=user_id,
        automation_id=automation_id,
    )

    print(
        f"   RUN HISTORY: {len(runs)}"
    )

    if loaded.status.value != "completed":
        raise RuntimeError(
            "Automation did not complete: "
            f"{loaded.status.value}"
        )

    if loaded.run_count != 1:
        raise RuntimeError(
            "Expected run_count=1, "
            f"got {loaded.run_count}"
        )

    if len(runs) != 1:
        raise RuntimeError(
            "Expected one automation run, "
            f"got {len(runs)}"
        )

    if runs[0].status.value != "completed":
        raise RuntimeError(
            "Automation run was not completed: "
            f"{runs[0].error}"
        )

    print()
    print(
        "AUTOMATION → VAIRRIEN INTEGRATION: OK"
    )

    print("7. CLEANING UP...")

    await state_store.delete_automation(
        user_id=user_id,
        automation_id=automation_id,
    )

    print("   AUTOMATION CLEANUP: OK")


if __name__ == "__main__":
    asyncio.run(main())