import asyncio

from vairrien_ai.memory.supabase import SupabaseStorage


USER_ID = "6075bbfd-4296-432a-83ae-107b010c23a2"


async def main():
    storage = SupabaseStorage()

    print("1. Creating conversation...")

    conversation = await storage.get_or_create_conversation(
        user_id=USER_ID,
        title="Vairrien Python Integration Test",
    )

    print("   Conversation:", conversation)

    conversation_id = conversation["id"]

    print("\n2. Saving message...")

    message = await storage.save_message(
        conversation_id=conversation_id,
        user_id=USER_ID,
        role="user",
        content="Python successfully wrote this message to Supabase.",
    )

    print("   Message:", message)

    print("\n3. Reading messages...")

    messages = await storage.get_messages(
        conversation_id=conversation_id,
    )

    print("   Messages found:", len(messages))

    print("\n4. Saving long-term memory...")

    memory = await storage.save_memory(
        user_id=USER_ID,
        content="Python successfully wrote a Vairrien long-term memory.",
        memory_type="integration_test",
        metadata={
            "source": "python_supabase_test",
            "importance": 1,
        },
    )

    print("   Memory:", memory)

    print("\n5. Reading memories...")

    memories = await storage.get_memories(
        user_id=USER_ID,
    )

    print("   Memories found:", len(memories))

    print("\n6. Saving AI memory...")

    ai_memory = await storage.save_ai_memory(
        user_id=USER_ID,
        content="Python successfully wrote an AI memory.",
        memory_type="integration_test",
        importance=1,
    )

    print("   AI memory:", ai_memory)

    print("\n7. Reading AI memories...")

    ai_memories = await storage.get_ai_memories(
        user_id=USER_ID,
    )

    print("   AI memories found:", len(ai_memories))

    print("\n================================")
    print("SUPABASE PYTHON TEST: SUCCESS")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())