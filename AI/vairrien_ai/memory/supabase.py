from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()


class SupabaseStorage:
    """
    Supabase persistent storage layer for Vairrien AI.

    Handles:

    - Profiles
    - Conversations
    - Messages
    - Long-term memories
    - AI memories
    - Task plans
    - Automations
    - Automation runs

    Uses the Supabase REST API directly.
    """

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL")
        self.service_role_key = os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY"
        )

        if not self.url:
            raise RuntimeError(
                "SUPABASE_URL environment variable is not set."
            )

        if not self.service_role_key:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY environment variable is not set."
            )

        self.rest_url = (
            f"{self.url.rstrip('/')}/rest/v1"
        )

    # ============================================================
    # HTTP
    # ============================================================

    def _headers(
        self,
        prefer: str | None = None,
    ) -> dict[str, str]:

        headers = {
            "apikey": self.service_role_key,
            "Authorization": (
                f"Bearer {self.service_role_key}"
            ),
            "Content-Type": "application/json",
        }

        if prefer:
            headers["Prefer"] = prefer

        return headers

    async def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> httpx.Response:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.request(
                method,
                f"{self.rest_url}/{table}",
                headers=self._headers(prefer),
                params=params,
                json=json,
            )

        return response

    @staticmethod
    def _raise_supabase_error(
        response: httpx.Response,
        table: str,
    ) -> None:

        if response.is_success:
            return

        try:
            error_body = response.json()
        except Exception:
            error_body = response.text

        raise RuntimeError(
            f"Supabase request failed for '{table}'. "
            f"HTTP {response.status_code}: {error_body}"
        )

    @staticmethod
    def _rows(
        response: httpx.Response,
        table: str,
    ) -> list[dict[str, Any]]:

        try:
            data = response.json()

        except Exception as exc:
            raise RuntimeError(
                f"Supabase returned invalid JSON for "
                f"'{table}': {response.text}"
            ) from exc

        if not isinstance(data, list):
            raise RuntimeError(
                f"Supabase returned an unexpected response "
                f"for '{table}': {data}"
            )

        return data

    # ============================================================
    # PROFILES
    # ============================================================

    async def get_profile(
        self,
        user_id: str,
    ) -> dict[str, Any] | None:

        response = await self._request(
            "GET",
            "profiles",
            params={
                "id": f"eq.{user_id}",
                "limit": "1",
            },
        )

        self._raise_supabase_error(
            response,
            "profiles",
        )

        rows = self._rows(
            response,
            "profiles",
        )

        return rows[0] if rows else None

    async def save_profile(
        self,
        user_id: str,
        full_name: str | None = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "id": user_id,
        }

        if full_name is not None:
            payload["full_name"] = full_name

        response = await self._request(
            "POST",
            "profiles",
            prefer=(
                "resolution=merge-duplicates,"
                "return=representation"
            ),
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "profiles",
        )

        rows = self._rows(
            response,
            "profiles",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved profile."
            )

        return rows[0]

    # ============================================================
    # CONVERSATIONS
    # ============================================================

    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:

        if conversation_id:

            response = await self._request(
                "GET",
                "conversations",
                params={
                    "id": f"eq.{conversation_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
            )

            self._raise_supabase_error(
                response,
                "conversations",
            )

            rows = self._rows(
                response,
                "conversations",
            )

            if rows:
                return rows[0]

        payload: dict[str, Any] = {
            "user_id": user_id,
        }

        if conversation_id:
            payload["id"] = conversation_id

        if title is not None:
            payload["title"] = title

        response = await self._request(
            "POST",
            "conversations",
            prefer=(
                "resolution=merge-duplicates,"
                "return=representation"
            ),
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "conversations",
        )

        rows = self._rows(
            response,
            "conversations",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the conversation."
            )

        return rows[0]

    async def get_conversation(
        self,
        user_id: str,
        conversation_id: str,
    ) -> dict[str, Any] | None:

        response = await self._request(
            "GET",
            "conversations",
            params={
                "id": f"eq.{conversation_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )

        self._raise_supabase_error(
            response,
            "conversations",
        )

        rows = self._rows(
            response,
            "conversations",
        )

        return rows[0] if rows else None

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        response = await self._request(
            "GET",
            "conversations",
            params={
                "user_id": f"eq.{user_id}",
                "order": "updated_at.desc",
                "limit": str(limit),
            },
        )

        self._raise_supabase_error(
            response,
            "conversations",
        )

        return self._rows(
            response,
            "conversations",
        )

    # ============================================================
    # MESSAGES
    # ============================================================

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:

        # --------------------------------------------------------
        # Resolve user_id from the conversation when necessary.
        #
        # The messages table stores:
        # conversation_id
        # user_id
        # role
        # content
        #
        # Metadata is intentionally not sent because the current
        # messages schema does not contain a metadata column.
        # --------------------------------------------------------

        if user_id is None:

            conversation_response = await self._request(
                "GET",
                "conversations",
                params={
                    "id": f"eq.{conversation_id}",
                    "limit": "1",
                },
            )

            self._raise_supabase_error(
                conversation_response,
                "conversations",
            )

            conversation_rows = self._rows(
                conversation_response,
                "conversations",
            )

            if not conversation_rows:
                raise RuntimeError(
                    "Cannot save message because conversation "
                    f"'{conversation_id}' was not found."
                )

            user_id = conversation_rows[0]["user_id"]

        payload = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }

        response = await self._request(
            "POST",
            "messages",
            prefer="return=representation",
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "messages",
        )

        rows = self._rows(
            response,
            "messages",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved message."
            )

        return rows[0]

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:

        params = {
            "conversation_id": f"eq.{conversation_id}",
            "order": "created_at.asc",
            "limit": str(limit),
        }

        # The orchestrator supplies user_id.
        # Keep it optional for compatibility with existing callers.
        if user_id is not None:
            params["user_id"] = f"eq.{user_id}"

        response = await self._request(
            "GET",
            "messages",
            params=params,
        )

        self._raise_supabase_error(
            response,
            "messages",
        )

        return self._rows(
            response,
            "messages",
        )

    # ============================================================
    # LONG-TERM MEMORY
    # ============================================================

    async def save_memory(
        self,
        user_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        memory_type: str | None = None,
    ) -> dict[str, Any]:

        metadata = metadata or {}

        if memory_type is None:

            possible_type = metadata.get(
                "memory_type"
            )

            if possible_type is not None:
                memory_type = str(
                    possible_type
                )

        payload: dict[str, Any] = {
            "user_id": user_id,
            "content": content,
            "metadata": metadata,
        }

        if memory_type is not None:
            payload["memory_type"] = memory_type

        response = await self._request(
            "POST",
            "memories",
            prefer="return=representation",
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "memories",
        )

        rows = self._rows(
            response,
            "memories",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved memory."
            )

        return rows[0]

    async def get_memories(
        self,
        user_id: str,
        limit: int = 20,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:

        params = {
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }

        if memory_type is not None:
            params["memory_type"] = (
                f"eq.{memory_type}"
            )

        response = await self._request(
            "GET",
            "memories",
            params=params,
        )

        self._raise_supabase_error(
            response,
            "memories",
        )

        return self._rows(
            response,
            "memories",
        )

    # ============================================================
    # AI MEMORY
    # ============================================================

    async def save_ai_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        importance: int = 1,
        business_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "user_id": user_id,
            "content": content,
            "memory_type": memory_type,
            "importance": int(importance),
        }

        if business_id is not None:
            payload["business_id"] = business_id

        if project_id is not None:
            payload["project_id"] = project_id

        response = await self._request(
            "POST",
            "ai_memory",
            prefer="return=representation",
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "ai_memory",
        )

        rows = self._rows(
            response,
            "ai_memory",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved AI memory."
            )

        return rows[0]

    async def get_ai_memories(
        self,
        user_id: str,
        limit: int = 50,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:

        params = {
            "user_id": f"eq.{user_id}",
            "order": "importance.desc,created_at.desc",
            "limit": str(limit),
        }

        if memory_type is not None:
            params["memory_type"] = (
                f"eq.{memory_type}"
            )

        response = await self._request(
            "GET",
            "ai_memory",
            params=params,
        )

        self._raise_supabase_error(
            response,
            "ai_memory",
        )

        return self._rows(
            response,
            "ai_memory",
        )

    # ============================================================
    # TASK PLANS
    # ============================================================

    async def save_task_plan(
        self,
        user_id: str,
        conversation_id: str,
        plan_data: dict[str, Any],
    ) -> dict[str, Any]:

        if "id" not in plan_data:
            raise ValueError(
                "Task plan must contain an 'id'."
            )

        payload = {
            "id": str(plan_data["id"]),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "goal": str(
                plan_data.get("goal", "")
            ),
            "status": str(
                plan_data.get(
                    "status",
                    "pending",
                )
            ),
            "plan_data": plan_data,
        }

        response = await self._request(
            "POST",
            "task_plans",
            prefer=(
                "resolution=merge-duplicates,"
                "return=representation"
            ),
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "task_plans",
        )

        rows = self._rows(
            response,
            "task_plans",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved task plan."
            )

        return rows[0]

    async def get_task_plan(
        self,
        user_id: str,
        plan_id: str,
    ) -> dict[str, Any] | None:

        response = await self._request(
            "GET",
            "task_plans",
            params={
                "id": f"eq.{plan_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )

        self._raise_supabase_error(
            response,
            "task_plans",
        )

        rows = self._rows(
            response,
            "task_plans",
        )

        return rows[0] if rows else None

    async def get_active_task_plan(
        self,
        user_id: str,
        conversation_id: str,
    ) -> dict[str, Any] | None:

        response = await self._request(
            "GET",
            "task_plans",
            params={
                "user_id": f"eq.{user_id}",
                "conversation_id": f"eq.{conversation_id}",
                "status": "in.(pending,active,paused)",
                "order": "updated_at.desc",
                "limit": "1",
            },
        )

        self._raise_supabase_error(
            response,
            "task_plans",
        )

        rows = self._rows(
            response,
            "task_plans",
        )

        return rows[0] if rows else None

    async def delete_task_plan(
        self,
        user_id: str,
        plan_id: str,
    ) -> None:

        response = await self._request(
            "DELETE",
            "task_plans",
            params={
                "id": f"eq.{plan_id}",
                "user_id": f"eq.{user_id}",
            },
        )

        self._raise_supabase_error(
            response,
            "task_plans",
        )

    # ============================================================
    # AUTOMATIONS
    # ============================================================

    async def save_automation(
        self,
        user_id: str,
        conversation_id: str,
        automation_data: dict[str, Any],
    ) -> dict[str, Any]:

        if "id" not in automation_data:
            raise ValueError(
                "Automation must contain an 'id'."
            )

        payload = {
            "id": str(
                automation_data["id"]
            ),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "name": str(
                automation_data.get(
                    "name",
                    "",
                )
            ),
            "description": str(
                automation_data.get(
                    "description",
                    "",
                )
            ),
            "schedule_type": str(
                automation_data.get(
                    "schedule_type",
                    "once",
                )
            ),
            "schedule_data": automation_data.get(
                "schedule_data",
                {},
            ),
            "action_data": automation_data.get(
                "action_data",
                {},
            ),
            "status": str(
                automation_data.get(
                    "status",
                    "active",
                )
            ),
            "next_run_at": automation_data.get(
                "next_run_at"
            ),
            "last_run_at": automation_data.get(
                "last_run_at"
            ),
            "run_count": int(
                automation_data.get(
                    "run_count",
                    0,
                )
            ),
            "last_result": automation_data.get(
                "last_result"
            ),
            "last_error": automation_data.get(
                "last_error"
            ),
        }

        response = await self._request(
            "POST",
            "automations",
            prefer=(
                "resolution=merge-duplicates,"
                "return=representation"
            ),
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "automations",
        )

        rows = self._rows(
            response,
            "automations",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved automation."
            )

        return rows[0]

    async def get_automation(
        self,
        user_id: str,
        automation_id: str,
    ) -> dict[str, Any] | None:

        response = await self._request(
            "GET",
            "automations",
            params={
                "id": f"eq.{automation_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )

        self._raise_supabase_error(
            response,
            "automations",
        )

        rows = self._rows(
            response,
            "automations",
        )

        return rows[0] if rows else None

    async def get_active_automations(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:

        response = await self._request(
            "GET",
            "automations",
            params={
                "user_id": f"eq.{user_id}",
                "status": "eq.active",
                "order": "next_run_at.asc",
            },
        )

        self._raise_supabase_error(
            response,
            "automations",
        )

        return self._rows(
            response,
            "automations",
        )

    async def get_due_automations(
        self,
        before: str,
    ) -> list[dict[str, Any]]:

        response = await self._request(
            "GET",
            "automations",
            params={
                "status": "eq.active",
                "next_run_at": f"lte.{before}",
                "order": "next_run_at.asc",
            },
        )

        self._raise_supabase_error(
            response,
            "automations",
        )

        return self._rows(
            response,
            "automations",
        )

    async def delete_automation(
        self,
        user_id: str,
        automation_id: str,
    ) -> None:

        response = await self._request(
            "DELETE",
            "automations",
            params={
                "id": f"eq.{automation_id}",
                "user_id": f"eq.{user_id}",
            },
        )

        self._raise_supabase_error(
            response,
            "automations",
        )

    # ============================================================
    # AUTOMATION RUNS
    # ============================================================

    async def save_automation_run(
        self,
        run_data: dict[str, Any],
    ) -> dict[str, Any]:

        required_fields = (
            "id",
            "automation_id",
            "user_id",
        )

        for field in required_fields:
            if field not in run_data:
                raise ValueError(
                    f"Automation run must contain '{field}'."
                )

        payload = {
            "id": str(run_data["id"]),
            "automation_id": str(
                run_data["automation_id"]
            ),
            "user_id": str(
                run_data["user_id"]
            ),
            "started_at": run_data.get(
                "started_at"
            ),
            "completed_at": run_data.get(
                "completed_at"
            ),
            "status": str(
                run_data.get(
                    "status",
                    "running",
                )
            ),
            "result": run_data.get(
                "result"
            ),
            "error": run_data.get(
                "error"
            ),
            "attempts": int(
                run_data.get(
                    "attempts",
                    1,
                )
            ),
        }

        response = await self._request(
            "POST",
            "automation_runs",
            prefer=(
                "resolution=merge-duplicates,"
                "return=representation"
            ),
            json=payload,
        )

        self._raise_supabase_error(
            response,
            "automation_runs",
        )

        rows = self._rows(
            response,
            "automation_runs",
        )

        if not rows:
            raise RuntimeError(
                "Supabase did not return the saved "
                "automation run."
            )

        return rows[0]

    async def get_automation_runs(
        self,
        user_id: str,
        automation_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        response = await self._request(
            "GET",
            "automation_runs",
            params={
                "user_id": f"eq.{user_id}",
                "automation_id": (
                    f"eq.{automation_id}"
                ),
                "order": "started_at.desc",
                "limit": str(limit),
            },
        )

        self._raise_supabase_error(
            response,
            "automation_runs",
        )

        return self._rows(
            response,
            "automation_runs",
        )
