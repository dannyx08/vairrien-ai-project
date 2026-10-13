Get-ChildItem -Recurse -File vairrien_ai | Select-Object FullNameimport asyncio

from vairrien_ai.context.engine import ContextEngine
from vairrien_ai.memory.manager import MemoryManager
from vairrien_ai.memory.supabase import SupabaseStorage


USER_ID = "6075bbfd-4296-432a-83ae-107b010c23a2"


async def main():
    print("1. INITIALIZING SUPABASE STORAGE...")
    storage = SupabaseStorage()
    print("   SUPABASE STORAGE: OK")

    print("2. INITIALIZING MEMORY MANAGER...")
    memory = MemoryManager(
        storage=storage,
    )
    print("   MEMORY MANAGER: OK")

    print("3. SAVING TEST MEMORY...")
    await memory.remember(
        "Vairrien AI is being developed as a persistent multimodal AI assistant.",
        user_id=USER_ID,
    )
    print("   MEMORY SAVED")

    print("4. INITIALIZING CONTEXT ENGINE...")
    context_engine = ContextEngine(
        memory=memory,
    )
    print("   CONTEXT ENGINE: OK")

    print("5. BUILDING MODEL CONTEXT...")

    context = await context_engine.build(
        message="What do you know about the Vairrien AI project?",
        user_id=USER_ID,
        memory_limit=50,
        conversation=[
            {
                "role": "user",
                "content": "I am building Vairrien AI.",
            },
            {
                "role": "assistant",
                "content": "I understand.",
            },
        ],
    )

    print("6. GENERATED CONTEXT:")
    print()

    for index, message in enumerate(context, start=1):
        print(f"   MESSAGE {index}")
        print(f"   ROLE: {message['role']}")
        print(f"   CONTENT: {message['content']}")
        print()

    print("7. VALIDATING CONTEXT...")

    assert context[-1]["role"] == "user"
    assert (
        context[-1]["content"]
        == "What do you know about the Vairrien AI project?"
    )

    assert any(
        message["role"] == "system"
        and "Relevant information remembered" in message["content"]
        for message in context
    )

    assert any(
        message["role"] == "user"
        and message["content"] == "I am building Vairrien AI."
        for message in context
    )

    assert any(
        message["role"] == "assistant"
        and message["content"] == "I understand."
        for message in context
    )

    print("   CURRENT USER MESSAGE: OK")
    print("   MEMORY CONTEXT: OK")
    print("   CONVERSATION HISTORY: OK")

    print()
    print("CONTEXT ENGINE INTEGRATION TEST: SUCCESS")


if __name__ == "__main__":
    asyncio.run(main())
