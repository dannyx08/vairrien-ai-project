from typing import Any
import re


class MemoryManager:
    """
    Vairrien persistent memory manager.

    Working memory exists locally during a request.
    Persistent long-term memories are stored in Supabase.

    The manager supports both:
    - `memories`: Vairrien structured long-term memory
    - `ai_memory`: AI/model-oriented memory storage
    """

    def __init__(self, storage: Any = None):
        self.storage = storage
        self._working_memory: list[dict[str, Any]] = []

    async def remember(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Store a memory in working memory and, when available,
        persist it to Supabase.
        """

        memory = {
            "content": content,
            "memory_type": memory_type,
            "metadata": metadata or {},
        }

        self._working_memory.append(memory)

        if self.storage is not None and user_id is not None:
            await self.storage.save_memory(
                user_id=user_id,
                content=content,
                memory_type=memory_type,
                metadata=metadata,
            )

    async def remember_ai(
        self,
        content: str,
        memory_type: str = "conversation",
        importance: int = 1,
        user_id: str | None = None,
        business_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Store an AI-oriented memory in the Supabase `ai_memory` table.

        Returns the stored row when persistence is available.
        """

        if self.storage is None or user_id is None:
            return None

        return await self.storage.save_ai_memory(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            business_id=business_id,
            project_id=project_id,
        )

    async def recall(
        self,
        query: str | None = None,
        limit: int = 10,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recall relevant Vairrien long-term memories.

        Working memory and persistent `memories` are combined,
        then ranked using lightweight lexical matching.
        """

        memories = list(self._working_memory)

        if self.storage is not None and user_id is not None:
            persistent_memories = await self.storage.get_memories(
                user_id=user_id,
                limit=50,
            )

            memories.extend(persistent_memories)

        if not query:
            return memories[-limit:]

        query_words = {
            word.lower()
            for word in re.findall(
                r"\b[a-zA-Z0-9]+\b",
                query,
            )
            if len(word) > 2
        }

        if not query_words:
            return memories[-limit:]

        scored_memories = []

        for index, memory in enumerate(memories):
            content = str(
                memory.get("content", "")
            ).lower()

            content_words = {
                word
                for word in re.findall(
                    r"\b[a-zA-Z0-9]+\b",
                    content,
                )
                if len(word) > 2
            }

            overlap = query_words.intersection(content_words)
            score = len(overlap)

            if score > 0:
                scored_memories.append(
                    (
                        score,
                        index,
                        memory,
                    )
                )

        scored_memories.sort(
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )

        return [
            memory
            for _, _, memory in scored_memories[:limit]
        ]

    async def recall_ai(
        self,
        limit: int = 10,
        user_id: str | None = None,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve AI-oriented memories from Supabase.
        """

        if self.storage is None or user_id is None:
            return []

        return await self.storage.get_ai_memories(
            user_id=user_id,
            limit=limit,
            memory_type=memory_type,
        )

    def clear_working_memory(self) -> None:
        """
        Clear only the current in-process working memory.

        Persistent Supabase memories are not deleted.
        """

        self._working_memory.clear()

    @property
    def working_memory(self) -> list[dict[str, Any]]:
        """
        Return a copy of the current working memory.
        """

        return list(self._working_memory)