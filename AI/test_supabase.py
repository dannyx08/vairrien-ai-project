import asyncio

from dotenv import load_dotenv
from vairrien_ai.memory.supabase import SupabaseStorage

load_dotenv()


async def main():
    storage = SupabaseStorage()

    user_id = "6075bbfd-4296-432a-83ae-107b010c23a2"

    print("Testing Supabase persistent memory...")

    await storage.save_memory(
        user_id=user_id,
        content="VAIRRIEN PERSISTENCE TEST",
        memory_type="system_test",
        metadata={"test": True},
    )

    memories = await storage.get_memories(
        user_id=user_id,
        limit=5,
    )

    print("Memory test successful.")
    print("Memories returned:")

    for memory in memories:
        print(memory)


if __name__ == "__main__":
    asyncio.run(main())