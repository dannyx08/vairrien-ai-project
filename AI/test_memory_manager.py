import asyncio

from vairrien_ai.memory.manager import MemoryManager
from vairrien_ai.memory.supabase import SupabaseStorage


USER_ID = "6075bbfd-4296-432a-83ae-107b010c23a2"


async def main():
    storage = SupabaseStorage()
    manager = MemoryManager(storage=storage)

    print("1. Saving Vairrien memory...")

    await manager.remember(
        user_id=USER_ID,
        content="Vairrien successfully remembered this through MemoryManager.",
        memory_type="integration_test",
        metadata={
            "source": "memory_manager_test",
            "importance": 1,
        },
    )

    print("   Memory saved.")

    print("\n2. Recalling memory...")

    memories = await manager.recall(
        query="Vairrien remembered MemoryManager",
        limit=5,
        user_id=USER_ID,
    )

    print("   Memories found:", len(memories))

    for index, memory in enumerate(memories, start=1):
        print(f"   {index}. {memory}")

    print("\n3. Saving AI memory...")

    ai_memory = await manager.remember_ai(
        user_id=USER_ID,
        content="Vairrien AI successfully stored an AI memory through MemoryManager.",
        memory_type="integration_test",
        importance=1,
    )

    print("   AI memory:", ai_memory)

    print("\n4. Recalling AI memories...")

    ai_memories = await manager.recall_ai(
        user_id=USER_ID,
        limit=5,
        memory_type="integration_test",
    )

    print("   AI memories found:", len(ai_memories))

    for index, memory in enumerate(ai_memories, start=1):
        print(f"   {index}. {memory}")

    print("\n5. Testing working memory...")

    await manager.remember(
        content="Temporary working memory test.",
        memory_type="working_test",
    )

    print("   Working memory entries:", len(manager.working_memory))

    manager.clear_working_memory()

    print("   Working memory after clear:", len(manager.working_memory))

    print("\n================================")
    print("MEMORY MANAGER TEST: SUCCESS")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())