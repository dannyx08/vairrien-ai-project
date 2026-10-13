from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class VairrienOrchestrator:
    """
    Central reasoning and execution controller for Vairrien AI.

    Responsibilities:
    - Load conversation history
    - Build model context through ContextEngine
    - Apply Single Heart context
    - Expose registered tools to the model
    - Execute model-requested tools
    - Support multiple tool-use rounds
    - Generate the final response
    - Persist conversation messages
    - Route multimodal requests to the multimodal reasoning model

    User messages may contain normal text or structured multimodal
    content. Structured content is preserved through ContextEngine
    and passed to the selected model without being converted to a
    string.

    Architecture:

        User message
              ↓
        Orchestrator
              ↓
        ContextEngine
          ├── Conversation history
          ├── Persistent memory
          └── Multimodal content
              ↓
        ┌───────────────────────────┐
        │ Text → main model         │
        │ Multimodal → omni model   │
        └───────────────────────────┘
              ↓
        Tool loop when required
              ↓
        Final response
              ↓
        Supabase conversation persistence
    """

    MAX_TOOL_ROUNDS = 8

    def __init__(
        self,
        model: Any,
        multimodal_model: Any = None,
        memory: Any = None,
        context: Any = None,
        tools: Any = None,
        single_heart: Any = None,
    ):
        self.model = model
        self.multimodal_model = multimodal_model
        self.memory = memory
        self.context = context
        self.tools = tools
        self.single_heart = single_heart

    # ========================================================
    # MULTIMODAL DETECTION
    # ========================================================

    def _is_multimodal_message(
        self,
        message: Any,
    ) -> bool:
        """
        Determine whether the incoming user message contains
        structured non-text multimodal content.

        The complete structured message is preserved and sent to
        the multimodal reasoning model when one is configured.
        """

        if not isinstance(message, list):
            return False

        multimodal_types = {
            "image_url",
            "input_image",
            "image",
            "audio_url",
            "input_audio",
            "audio",
            "video_url",
            "input_video",
            "video",
        }

        def contains_multimodal(
            value: Any,
        ) -> bool:
            if isinstance(value, dict):
                if value.get("type") in multimodal_types:
                    return True

                return any(
                    contains_multimodal(item)
                    for item in value.values()
                )

            if isinstance(value, list):
                return any(
                    contains_multimodal(item)
                    for item in value
                )

            return False

        return contains_multimodal(message)

    def _message_requires_multimodal_model(
        self,
        message: str | list[dict[str, Any]],
    ) -> bool:
        """
        Compatibility helper used to determine whether a request
        requires the multimodal reasoning model.
        """

        return self._is_multimodal_message(message)

    # ========================================================
    # MODEL SELECTION
    # ========================================================

    def _select_model(
        self,
        message: str | list[dict[str, Any]],
    ) -> Any:
        """
        Select the reasoning model for the current request.

        Normal text requests use the primary text model.

        Structured multimodal requests use the configured
        multimodal model when available.

        If no multimodal model is configured, raise an error
        rather than silently sending multimodal content to a
        text-only model.
        """

        if self._message_requires_multimodal_model(
            message
        ):
            if self.multimodal_model is None:
                raise RuntimeError(
                    "A multimodal model is required for structured "
                    "multimodal input."
                )

            return self.multimodal_model

        return self.model

    # ========================================================
    # TOOL DEFINITIONS
    # ========================================================

    def _build_tool_definitions(
        self,
    ) -> list[dict[str, Any]]:
        """
        Convert registered Vairrien tools into the
        OpenAI-compatible tool format expected by the model.
        """

        if self.tools is None:
            return []

        definitions: list[dict[str, Any]] = []

        for tool in self.tools.list_tools():
            if not tool.get("enabled", True):
                continue

            definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get(
                            "description",
                            "",
                        ),
                        "parameters": tool.get(
                            "parameters",
                            {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        ),
                    },
                }
            )

        return definitions

    # ========================================================
    # RESPONSE HELPERS
    # ========================================================

    def _normalize_assistant_message(
        self,
        response: Any,
    ) -> dict[str, Any]:
        """
        Normalize the model response into a message that can
        be supplied to the next model/tool round.
        """

        if isinstance(response, dict):
            content = response.get("content")
            tool_calls = response.get(
                "tool_calls",
                [],
            )
            role = response.get(
                "role",
                "assistant",
            )

        else:
            content = getattr(
                response,
                "content",
                None,
            )

            tool_calls = getattr(
                response,
                "tool_calls",
                [],
            )

            role = getattr(
                response,
                "role",
                "assistant",
            )

        normalized: dict[str, Any] = {
            "role": role,
            "content": content,
        }

        if tool_calls:
            normalized["tool_calls"] = tool_calls

        return normalized

    def _get_tool_calls(
        self,
        response: Any,
    ) -> list[Any]:
        """
        Extract tool calls from a model response.
        """

        if isinstance(response, dict):
            tool_calls = response.get(
                "tool_calls",
                [],
            )
        else:
            tool_calls = getattr(
                response,
                "tool_calls",
                [],
            )

        if isinstance(tool_calls, list):
            return tool_calls

        return []

    # ========================================================
    # TOOL CALL HELPERS
    # ========================================================

    def _get_tool_call_id(
        self,
        tool_call: Any,
    ) -> str | None:

        if isinstance(tool_call, dict):
            return tool_call.get("id")

        return getattr(
            tool_call,
            "id",
            None,
        )

    def _get_tool_call_function(
        self,
        tool_call: Any,
    ) -> Any:

        if isinstance(tool_call, dict):
            return tool_call.get("function")

        return getattr(
            tool_call,
            "function",
            None,
        )

    def _get_function_value(
        self,
        function: Any,
        key: str,
        default: Any = None,
    ) -> Any:

        if isinstance(function, dict):
            return function.get(
                key,
                default,
            )

        return getattr(
            function,
            key,
            default,
        )

    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    async def _execute_tool_calls(
        self,
        tool_calls: list[Any],
        *,
        user_id: str,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        """
        Execute model-requested tools through ToolRegistry.
        """

        if self.tools is None:
            return []

        execution_context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
        }

        results: list[dict[str, Any]] = []

        for tool_call in tool_calls:

            tool_call_id = self._get_tool_call_id(
                tool_call
            )

            function = self._get_tool_call_function(
                tool_call
            )

            if function is None:
                continue

            tool_name = self._get_function_value(
                function,
                "name",
            )

            raw_arguments = self._get_function_value(
                function,
                "arguments",
                "{}",
            )

            if not tool_name:
                continue

            # ------------------------------------------------
            # Parse arguments
            # ------------------------------------------------

            try:
                arguments = json.loads(
                    raw_arguments or "{}"
                )

                if not isinstance(
                    arguments,
                    dict,
                ):
                    arguments = {}

            except (
                json.JSONDecodeError,
                TypeError,
            ):
                arguments = {}

            # ------------------------------------------------
            # Execute tool
            # ------------------------------------------------

            try:
                result = await self.tools.execute(
                    tool_name,
                    context=execution_context,
                    **arguments,
                )

            except Exception as exc:
                result = {
                    "status": "error",
                    "error": str(exc),
                    "tool": tool_name,
                }

            results.append(
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "result": result,
                }
            )

        return results

    # ========================================================
    # SYSTEM INSTRUCTIONS
    # ========================================================

    def _build_system_instructions(
        self,
        *,
        heart_context: Any = None,
    ) -> str:
        """
        Build Vairrien's core behavioral instructions.

        Persistent memory is intentionally NOT inserted here.
        ContextEngine is responsible for constructing the
        memory-aware context.
        """

        current_utc = datetime.now(
            timezone.utc
        ).isoformat()

        instructions = f"""
You are Vairrien AI.

You are an intelligent general-purpose AI assistant designed to
understand users, reason about their requests, maintain context,
remember important information, use capabilities, research the web,
work with documents, and help users complete tasks.

CORE BEHAVIOR

- Understand the user's actual intent before responding.
- Use conversation history when relevant.
- Reason carefully before answering.
- Give useful, direct answers.
- Do not invent facts, actions, tool results, or sources.
- If a registered tool can meaningfully accomplish the user's request,
  use it instead of pretending to perform the action yourself.
- You may use multiple tools in sequence when necessary.
- After receiving a tool result, continue reasoning and complete the
  user's request.
- Do not claim that a tool was used unless it actually returned a result.
- Do not expose internal implementation details unless the user asks.

MULTIMODAL INPUT

User messages may contain text, images, audio, video, or combinations
of these modalities.

When multimodal information is provided:
- Treat all supplied modalities as part of the same user request.
- Reason across the available modalities together.
- Connect information between modalities when relevant.
- Do not treat each modality as an unrelated request.
- Use available multimodal tools when additional understanding is
  required.
- Do not claim to have perceived or analyzed a modality that was not
  actually provided or processed.
- When an image, audio input, video input, or other supported modality
  is directly provided, use the supplied multimodal content as part of
  your reasoning rather than assuming it is unrelated context.

DOCUMENTS

When the user asks you to read, inspect, summarize, analyze, extract,
or understand a local supported document, use the document_extract
tool.

Do not pretend to have read a document without actually using the
document_extract tool.

Supported document formats include TXT, PDF, DOCX, CSV, XLSX, and PPTX.

MEMORY

Conversation history and long-term memory are different things.

Conversation history is persisted separately and should be used to
maintain conversational context.

Do NOT store every user message or assistant response as long-term
memory.

Use the remember_information tool when:

- The user explicitly asks you to remember something.
- The user gives a durable preference that should remain useful later.
- The user gives an important personal fact that is genuinely useful
  for future assistance.
- The user establishes an ongoing goal, project fact, or stable
  instruction that should persist across conversations.

Do NOT use long-term memory for:

- Temporary questions.
- Ordinary answers.
- One-off calculations.
- Casual conversation.
- Temporary details that have no future value.

Never claim that something was remembered unless the
remember_information tool actually succeeded.

WEB AND RESEARCH

When current, external, or source-backed information is needed,
use the available web tools.

Use web_search when you need to discover relevant sources.

Use web_read or web_fetch when you need information from a specific
web page.

Use web_research when the request requires gathering information from
multiple sources.

Do not claim to have searched the web unless a web tool actually
returned results.

SCHEDULING AND AUTOMATIONS

The current UTC date and time is: {current_utc}

When the user asks you to create a scheduled or recurring task, use the
appropriate automation tool.

For a one-time automation:
- Use schedule_type="once".
- schedule_data.run_at MUST be an ISO-8601 UTC timestamp.
- For relative requests such as "in 20 seconds", calculate the future
timestamp from the current UTC date and time above.
- Never invent a historical date or use a stale date.
- The resulting run_at must be in the future.

For repeated tasks:
- Use schedule_type="interval" with interval_seconds when the user
specifies a duration or repeating interval.
- Use schedule_type="cron" when the user explicitly specifies a
cron-like recurring schedule.

The message passed to the automation is the instruction Vairrien
executes when the automation fires.

TOOL USE

Use tools when they are useful for the user's request.

Tool arguments should contain only information necessary for the tool.
Trusted runtime information such as user identity and conversation
identity is supplied by the Vairrien runtime.

If a tool fails, do not pretend it succeeded. Explain the result or
continue using another appropriate capability when possible.

RESPONSE QUALITY

Prefer accurate and useful answers over unnecessary verbosity.

When the task requires multiple steps, complete the necessary steps
before giving the final answer.

When information is uncertain, say so clearly.

When the user's request is ambiguous and the ambiguity materially
affects the result, ask a concise clarification.

You are Vairrien AI. Your job is to understand, reason, remember,
research, use capabilities, and help the user accomplish meaningful
tasks.
""".strip()

        if heart_context:
            instructions += (
                "\n\nSINGLE HEART CONTEXT:\n"
                + str(heart_context)
            )

        return instructions

    # ========================================================
    # MAIN RESPONSE PIPELINE
    # ========================================================

    async def respond(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str | list[dict[str, Any]],
        conversation: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Main Vairrien reasoning and execution pipeline.

        The message may be normal text or structured multimodal
        content. Structured content is preserved and passed through
        ContextEngine to the selected reasoning model.
        """

        # ====================================================
        # 1. VALIDATE REQUEST
        # ====================================================

        if not user_id or not user_id.strip():
            raise ValueError(
                "user_id is required."
            )

        if not conversation_id or not conversation_id.strip():
            raise ValueError(
                "conversation_id is required."
            )

        if not message:
            raise ValueError(
                "message is required."
            )

        if isinstance(message, str):
            if not message.strip():
                raise ValueError(
                    "message is required."
                )

        elif isinstance(message, list):
            if not message:
                raise ValueError(
                    "message is required."
                )

        else:
            raise TypeError(
                "message must be a string or structured "
                "multimodal content list."
            )

        # ====================================================
        # 2. ENSURE CONVERSATION
        # ====================================================

        storage = None

        if self.memory is not None:
            storage = getattr(
                self.memory,
                "storage",
                None,
            )

        if storage is not None:
            await storage.get_or_create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
            )

        # ====================================================
        # 3. LOAD CONVERSATION HISTORY
        # ====================================================

        if conversation is None and storage is not None:
            conversation = await storage.get_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=50,
            )

        conversation = conversation or []

        # ====================================================
        # 4. SINGLE HEART
        # ====================================================

        heart_context = None

        if self.single_heart is not None:
            try:
                if hasattr(
                    self.single_heart,
                    "build_context",
                ):
                    heart_context = (
                        await self.single_heart.build_context(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=message,
                        )
                    )

                elif hasattr(
                    self.single_heart,
                    "get_context",
                ):
                    heart_context = (
                        await self.single_heart.get_context(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=message,
                        )
                    )

            except Exception:
                heart_context = None

        # ====================================================
        # 5. BUILD SYSTEM INSTRUCTIONS
        # ====================================================

        system_instructions = (
            self._build_system_instructions(
                heart_context=heart_context,
            )
        )

        # ====================================================
        # 6. BUILD CONTEXT
        # ====================================================

        if self.context is not None:
            context_messages = await self.context.build(
                message=message,
                conversation=conversation,
                user_id=user_id,
            )

            messages: list[dict[str, Any]] = [
                {
                    "role": "system",
                    "content": system_instructions,
                }
            ]

            messages.extend(
                context_messages
            )

        else:
            messages = [
                {
                    "role": "system",
                    "content": system_instructions,
                }
            ]

            messages.extend(
                conversation
            )

            messages.append(
                {
                    "role": "user",
                    "content": message,
                }
            )

        # ====================================================
        # 7. TOOL DEFINITIONS
        # ====================================================

        tool_definitions = (
            self._build_tool_definitions()
        )

        # ====================================================
        # 8. SELECT REASONING MODEL
        # ====================================================

        active_model = self._select_model(
            message
        )

        # ====================================================
        # 9. MODEL + TOOL LOOP
        # ====================================================

        final_response: str | None = None
        usage = None
        tool_rounds = 0
        tools_used = False

        for round_number in range(
            self.MAX_TOOL_ROUNDS
        ):
            tool_rounds = round_number + 1

            response = await active_model.generate(
                messages=messages,
                tools=tool_definitions or None,
            )

            # ------------------------------------------------
            # Usage
            # ------------------------------------------------

            if isinstance(response, dict):
                usage = response.get(
                    "usage"
                )
            else:
                usage = getattr(
                    response,
                    "usage",
                    None,
                )

            # ------------------------------------------------
            # Normalize response
            # ------------------------------------------------

            normalized_assistant = (
                self._normalize_assistant_message(
                    response
                )
            )

            # ------------------------------------------------
            # Extract tool calls
            # ------------------------------------------------

            tool_calls = self._get_tool_calls(
                response
            )

            # ------------------------------------------------
            # Final response
            # ------------------------------------------------

            if not tool_calls:
                content = normalized_assistant.get(
                    "content"
                )

                if content is None:
                    final_response = ""
                elif isinstance(content, str):
                    final_response = content
                else:
                    final_response = str(content)

                break

            # ------------------------------------------------
            # Tool calls occurred
            # ------------------------------------------------

            tools_used = True

            messages.append(
                normalized_assistant
            )

            tool_results = (
                await self._execute_tool_calls(
                    tool_calls,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
            )

            # ------------------------------------------------
            # Add tool results to model context
            # ------------------------------------------------

            for tool_result in tool_results:
                tool_call_id = tool_result.get(
                    "tool_call_id"
                )

                if not tool_call_id:
                    continue

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_result[
                            "tool_name"
                        ],
                        "content": json.dumps(
                            tool_result[
                                "result"
                            ],
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                )

        # ====================================================
        # 10. FALLBACK
        # ====================================================

        if final_response is None:
            final_response = (
                "I wasn't able to complete the request."
            )

        # ====================================================
        # 11. PERSIST CONVERSATION
        # ====================================================

        if storage is not None:
            try:
                await storage.save_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="user",
                    content=(
                        message
                        if isinstance(message, str)
                        else json.dumps(
                            message,
                            ensure_ascii=False,
                            default=str,
                        )
                    ),
                )

                await storage.save_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_response,
                )

            except Exception as exc:
                # Conversation persistence should not destroy
                # an otherwise successful model response.
                print(
                    "VAIRRIEN CONVERSATION PERSISTENCE ERROR:"
                )
                print(
                    type(exc).__name__,
                    str(exc),
                )

        # ====================================================
        # 12. RETURN
        # ====================================================

        return {
            "response": final_response,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "tool_rounds": tool_rounds,
            "tools_used": tools_used,
            "usage": usage,
        }