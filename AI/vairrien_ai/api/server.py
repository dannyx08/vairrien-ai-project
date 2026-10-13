from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from vairrien_ai.automation import (
    AutomationEngine,
    AutomationStateStore,
)
from vairrien_ai.automation.scheduler import AutomationScheduler
from vairrien_ai.config.settings import settings
from vairrien_ai.context.engine import ContextEngine
from vairrien_ai.core.orchestrator import VairrienOrchestrator
from vairrien_ai.documents.tools import DocumentTool
from vairrien_ai.memory.manager import MemoryManager
from vairrien_ai.memory.supabase import SupabaseStorage
from vairrien_ai.model.openrouter import OpenRouterProvider
from vairrien_ai.multimodal.inference import MultimodalInference
from vairrien_ai.providers.jina import JinaSearchProvider
from vairrien_ai.providers.reader import JinaReaderProvider
from vairrien_ai.tools.audio import AudioTool
from vairrien_ai.tools.automation import AutomationTool
from vairrien_ai.tools.multimodal import MultimodalTool
from vairrien_ai.tools.registry import ToolRegistry
from vairrien_ai.tools.web import WebTool


# ============================================================
# VAIRRIEN CORE
# ============================================================

model = OpenRouterProvider(
    model_name=settings.model_name,
    api_key=settings.model_api_key,
)

# Dedicated multimodal reasoning model.
#
# This is separate from MultimodalInference. The purpose here is
# to allow the orchestrator to send the complete structured
# multimodal conversation directly to the configured Omni model.
#
# Normal text requests continue using the primary model above.
multimodal_model = OpenRouterProvider(
    model_name=settings.vision_model_name,
    api_key=(
        settings.vision_api_key
        or settings.model_api_key
        or None
    ),
)

storage = SupabaseStorage()

memory = MemoryManager(
    storage=storage,
)

tools = ToolRegistry()


# ============================================================
# AUTOMATION STATE
# ============================================================

automation_state = AutomationStateStore(
    storage=storage,
)


# ============================================================
# WEB CAPABILITY
# ============================================================

jina_search = JinaSearchProvider()
jina_reader = JinaReaderProvider()

web_tool = WebTool(
    search_provider=jina_search,
    reader_provider=jina_reader,
)


# ============================================================
# DOCUMENT CAPABILITY
# ============================================================

document_tool = DocumentTool()


# ============================================================
# MULTIMODAL CAPABILITY
# ============================================================

multimodal_inference = MultimodalInference()

multimodal_tool = MultimodalTool(
    inference=multimodal_inference,
)


# ============================================================
# AUDIO CAPABILITY
# ============================================================

audio_tool = AudioTool()


# ============================================================
# MEMORY TOOL
# ============================================================

async def remember_information(
    content: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    user_id = context.get("user_id")
    conversation_id = context.get("conversation_id")

    if not user_id:
        raise ValueError(
            "Missing user_id in tool execution context."
        )

    await memory.remember(
        content=content,
        memory_type="explicit_memory",
        user_id=user_id,
        metadata={
            "conversation_id": conversation_id,
            "source": "remember_information",
        },
    )

    return {
        "status": "success",
        "action": "remembered",
        "content": content,
    }


tools.register(
    name="remember_information",
    description=(
        "Save important information provided by the user "
        "to persistent memory for future conversations."
    ),
    function=remember_information,
    parameters={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "The information that should be remembered."
                ),
            },
        },
        "required": ["content"],
        "additionalProperties": False,
    },
    category="memory",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# WEB SEARCH
# ============================================================

async def web_search(
    query: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await web_tool.search(
        query=query,
    )


tools.register(
    name="web_search",
    description=(
        "Search the internet for information. "
        "Use this when the user asks for current, "
        "external, or web-based information."
    ),
    function=web_search,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The internet search query.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    category="web",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# WEB FETCH
# ============================================================

async def web_fetch(
    url: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await web_tool.fetch(
        url=url,
    )


tools.register(
    name="web_fetch",
    description=(
        "Fetch the raw contents of a specific webpage."
    ),
    function=web_fetch,
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The HTTP or HTTPS URL.",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
    category="web",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# WEB READER
# ============================================================

async def web_read(
    url: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await web_tool.read(
        url=url,
    )


tools.register(
    name="web_read",
    description=(
        "Read a webpage as structured, readable content. "
        "Use this when the user wants information from a "
        "specific webpage rather than raw HTML."
    ),
    function=web_read,
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The webpage URL to read.",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    },
    category="web",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# WEB RESEARCH
# ============================================================

async def web_research(
    query: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await web_tool.research(
        query=query,
    )


tools.register(
    name="web_research",
    description=(
        "Perform multi-source web research. "
        "Search for relevant information, collect multiple "
        "sources, read usable sources, and return structured "
        "research evidence. Use this for research questions, "
        "cross-checking, comparisons, current information, "
        "or questions requiring several sources."
    ),
    function=web_research,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The research question or topic."
                ),
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    category="web",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

async def document_extract(
    file_path: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await document_tool.extract(
        file_path=file_path,
    )


tools.register(
    name="document_extract",
    description=(
        "Extract and read the contents of a document file. "
        "Supported formats include TXT, PDF, DOCX, CSV, XLSX, "
        "and PPTX. Use this when the user needs Vairrien to "
        "read, understand, summarize, or analyze a document."
    ),
    function=document_extract,
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "The local path to the document file."
                ),
            },
        },
        "required": ["file_path"],
        "additionalProperties": False,
    },
    category="documents",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# MULTIMODAL IMAGE UNDERSTANDING
# ============================================================

async def multimodal_understand_image(
    file_path: str,
    instruction: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await multimodal_tool.understand_image(
        file_path=file_path,
        instruction=instruction,
    )


tools.register(
    name="multimodal_understand_image",
    description=(
        "Understand and analyze an image using Vairrien's "
        "multimodal model. Use this when an image needs "
        "to be examined for objects, scenes, visible text, "
        "visual details, screenshots, diagrams, photos, "
        "or other information contained in it."
    ),
    function=multimodal_understand_image,
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "The local path to the image that should "
                    "be analyzed."
                ),
            },
            "instruction": {
                "type": "string",
                "description": (
                    "What should be identified, described, "
                    "read, or analyzed in the image."
                ),
            },
        },
        "required": [
            "file_path",
            "instruction",
        ],
        "additionalProperties": False,
    },
    category="multimodal",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# NATIVE AUDIO TRANSCRIPTION
# ============================================================

async def audio_transcribe(
    file_path: str,
    language: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await audio_tool.transcribe_audio(
        file_path=file_path,
        language=language,
    )


tools.register(
    name="audio_transcribe",
    description=(
        "Transcribe spoken content from an audio file using "
        "Vairrien's native local audio engine. Use this when "
        "the user provides a voice note, recording, interview, "
        "conversation, speech, or other audio containing spoken "
        "language that needs to be transcribed or understood."
    ),
    function=audio_transcribe,
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "The local path to the audio file "
                    "that should be transcribed."
                ),
            },
            "language": {
                "type": [
                    "string",
                    "null",
                ],
                "description": (
                    "Optional ISO language code such as 'en'. "
                    "Use null for automatic language detection."
                ),
            },
        },
        "required": [
            "file_path",
            "language",
        ],
        "additionalProperties": False,
    },
    category="audio",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# MULTIMODAL VIDEO UNDERSTANDING
# ============================================================

async def multimodal_understand_video(
    file_path: str,
    instruction: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await multimodal_tool.understand_video(
        file_path=file_path,
        instruction=instruction,
    )


tools.register(
    name="multimodal_understand_video",
    description=(
        "Understand and analyze a video file using "
        "Vairrien's multimodal model. Use this to examine "
        "video scenes, actions, visible text, events, "
        "objects, spoken or contextual information, and "
        "other content contained in the video."
    ),
    function=multimodal_understand_video,
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "The local path to the video file that "
                    "should be analyzed."
                ),
            },
            "instruction": {
                "type": "string",
                "description": (
                    "What should be identified, described, "
                    "read, or analyzed in the video."
                ),
            },
        },
        "required": [
            "file_path",
            "instruction",
        ],
        "additionalProperties": False,
    },
    category="multimodal",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# CONTEXT ENGINE
# ============================================================

context_engine = ContextEngine(
    memory=memory,
    tools=tools,
)


# ============================================================
# ORCHESTRATOR
# ============================================================

orchestrator = VairrienOrchestrator(
    model=model,
    multimodal_model=multimodal_model,
    memory=memory,
    context=context_engine,
    tools=tools,
)


# ============================================================
# AUTOMATION ENGINE
# ============================================================

automation_engine = AutomationEngine(
    orchestrator=orchestrator,
    state_store=automation_state,
)

automation_scheduler = AutomationScheduler(
    state_store=automation_state,
    poll_interval=5.0,
)

automation_tool = AutomationTool(
    state_store=automation_state,
    engine=automation_engine,
)


# ============================================================
# AUTOMATION: CREATE
# ============================================================

async def automation_create(
    name: str,
    description: str,
    schedule_type: str,
    schedule_data: dict[str, Any],
    message: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await automation_tool.create(
        context=context,
        name=name,
        description=description,
        schedule_type=schedule_type,
        schedule_data=schedule_data,
        message=message,
    )


tools.register(
    name="automation_create",
    description=(
        "Create a scheduled Vairrien task. "
        "Use this when the user explicitly asks Vairrien "
        "to remember, remind, check, perform, or execute "
        "something at a future time or repeatedly. "
        "Use schedule_type='once' for one future execution, "
        "schedule_type='interval' for repeated execution "
        "using interval_seconds, or schedule_type='cron' "
        "for a cron expression. "
        "The message is the instruction Vairrien executes "
        "when the automation fires."
    ),
    function=automation_create,
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": (
                    "A short, human-readable name for the automation."
                ),
            },
            "description": {
                "type": "string",
                "description": (
                    "A short description of the scheduled task."
                ),
            },
            "schedule_type": {
                "type": "string",
                "enum": [
                    "once",
                    "interval",
                    "cron",
                ],
                "description": (
                    "The scheduling mode."
                ),
            },
            "schedule_data": {
                "type": "object",
                "description": (
                    "Schedule configuration. "
                    "For once use run_at as an ISO datetime. "
                    "For interval use interval_seconds. "
                    "For cron use expression."
                ),
                "additionalProperties": True,
            },
            "message": {
                "type": "string",
                "description": (
                    "The instruction Vairrien should execute "
                    "when the automation runs."
                ),
            },
        },
        "required": [
            "name",
            "description",
            "schedule_type",
            "schedule_data",
            "message",
        ],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# AUTOMATION: LIST
# ============================================================

async def automation_list(
    context: dict[str, Any],
) -> dict[str, Any]:

    return await automation_tool.list(
        context=context,
    )


tools.register(
    name="automation_list",
    description=(
        "List the user's active scheduled automations. "
        "Use this when the user asks what scheduled tasks "
        "or reminders are currently active."
    ),
    function=automation_list,
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# AUTOMATION: PAUSE
# ============================================================

async def automation_pause(
    automation_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await automation_tool.pause(
        context=context,
        automation_id=automation_id,
    )


tools.register(
    name="automation_pause",
    description=(
        "Pause an active scheduled automation so it will "
        "temporarily stop executing."
    ),
    function=automation_pause,
    parameters={
        "type": "object",
        "properties": {
            "automation_id": {
                "type": "string",
                "description": (
                    "The ID of the automation to pause."
                ),
            },
        },
        "required": [
            "automation_id",
        ],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# AUTOMATION: RESUME
# ============================================================

async def automation_resume(
    automation_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await automation_tool.resume(
        context=context,
        automation_id=automation_id,
    )


tools.register(
    name="automation_resume",
    description=(
        "Resume a paused scheduled automation."
    ),
    function=automation_resume,
    parameters={
        "type": "object",
        "properties": {
            "automation_id": {
                "type": "string",
                "description": (
                    "The ID of the automation to resume."
                ),
            },
        },
        "required": [
            "automation_id",
        ],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# AUTOMATION: CANCEL
# ============================================================

async def automation_cancel(
    automation_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:

    return await automation_tool.cancel(
        context=context,
        automation_id=automation_id,
    )


tools.register(
    name="automation_cancel",
    description=(
        "Cancel a scheduled automation so it will no longer run. "
        "Use this when the user explicitly asks to cancel, remove, "
        "or stop a scheduled automation."
    ),
    function=automation_cancel,
    parameters={
        "type": "object",
        "properties": {
            "automation_id": {
                "type": "string",
                "description": (
                    "The ID of the automation to cancel."
                ),
            },
        },
        "required": [
            "automation_id",
        ],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# AUTOMATION: RUN HISTORY
# ============================================================

async def automation_runs(
    automation_id: str,
    limit: int = 20,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:

    if context is None:
        context = {}

    return await automation_tool.runs(
        context=context,
        automation_id=automation_id,
        limit=limit,
    )


tools.register(
    name="automation_runs",
    description=(
        "Inspect execution history for a scheduled automation. "
        "Use this when the user asks whether an automation ran, "
        "what happened during previous executions, or whether "
        "a scheduled task succeeded or failed."
    ),
    function=automation_runs,
    parameters={
        "type": "object",
        "properties": {
            "automation_id": {
                "type": "string",
                "description": (
                    "The ID of the automation."
                ),
            },
            "limit": {
                "type": "integer",
                "description": (
                    "Maximum number of execution records "
                    "to return. Defaults to 20."
                ),
                "minimum": 1,
                "maximum": 100,
                "default": 20,
            },
        },
        "required": [
            "automation_id",
        ],
        "additionalProperties": False,
    },
    category="automation",
    requires_approval=False,
    enabled=True,
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Vairrien AI backend API. "
        "Provides conversational intelligence, persistent "
        "memory, unified multimodal reasoning, web capabilities, "
        "document intelligence, native audio intelligence, "
        "and scheduled automation."
    ),
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API MODELS
# ============================================================

class ChatRequest(BaseModel):
    user_id: str
    conversation_id: str

    # Supports ordinary text as well as structured multimodal
    # content such as text + image/audio/video content.
    message: str | list[dict[str, Any]]

    conversation: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    response: str


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health() -> dict[str, Any]:

    try:
        model_available = await model.health()
    except Exception:
        model_available = False

    try:
        multimodal_model_available = (
            await multimodal_model.health()
        )
    except Exception:
        multimodal_model_available = False

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,

        # Main model
        "model": settings.model_name,
        "model_provider": settings.model_provider,
        "model_available": model_available,

        # Multimodal reasoning model
        "vision_model": settings.vision_model_name,
        "vision_provider": settings.vision_provider,
        "multimodal_model_available": (
            multimodal_model_available
        ),
        "multimodal": True,
        "unified_multimodal_reasoning": True,
        "image_understanding": True,

        # Native audio
        "audio_understanding": True,
        "audio_transcription": True,
        "audio_provider": "local",
        "audio_model": "faster-whisper",

        # Video
        "video_understanding": True,

        # Memory
        "memory": True,
        "persistent_memory": storage is not None,

        # Context
        "context": True,

        # Web
        "web": True,
        "web_search": True,
        "web_reader": True,
        "web_research": True,

        # Documents
        "documents": True,
        "document_extraction": True,

        # Automation
        "automation": True,
        "automation_scheduler": True,
        "automation_poll_interval": 5.0,

        # Tools
        "tools": tools.count(
            enabled_only=True
        ),
        "tool_categories": tools.list_categories(),
    }


# ============================================================
# CHAT
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:

    # --------------------------------------------------------
    # Validate request
    # --------------------------------------------------------

    if not request.user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="user_id is required.",
        )

    if not request.conversation_id.strip():
        raise HTTPException(
            status_code=400,
            detail="conversation_id is required.",
        )

    if isinstance(request.message, str):

        if not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty.",
            )

    elif isinstance(request.message, list):

        if not request.message:
            raise HTTPException(
                status_code=400,
                detail="Message content cannot be empty.",
            )

        for item in request.message:

            if not isinstance(item, dict):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Each multimodal message item "
                        "must be an object."
                    ),
                )

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Message must be text or structured "
                "multimodal content."
            ),
        )

    # --------------------------------------------------------
    # Run Vairrien
    # --------------------------------------------------------

    try:

        result = await orchestrator.respond(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            message=request.message,
            conversation=request.conversation,
        )

        if not isinstance(result, dict):
            raise ValueError(
                "Invalid orchestrator response."
            )

        response_text = result.get(
            "response",
            "",
        )

        if response_text is None:
            response_text = ""

        return ChatResponse(
            response=str(response_text),
        )

    except HTTPException:
        raise

    except Exception as error:

        print("=" * 60)
        print("VAIRRIEN CHAT ERROR")
        print("=" * 60)
        print(type(error).__name__)
        print(str(error))
        print("=" * 60)

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    print()
    print("=" * 60)
    print("VAIRRIEN AI")
    print("=" * 60)

    print(
        f"Environment: "
        f"{settings.environment}"
    )

    print(
        f"Provider: "
        f"{settings.model_provider}"
    )

    print(
        f"Model: "
        f"{settings.model_name}"
    )

    print(
        f"Vision Provider: "
        f"{settings.vision_provider}"
    )

    print(
        f"Vision Model: "
        f"{settings.vision_model_name}"
    )

    print(
        f"Tools: "
        f"{tools.count(enabled_only=True)}"
    )

    print(
        f"Tool categories: "
        f"{tools.list_categories()}"
    )

    print("Memory: Enabled")

    print(
        f"Persistent memory: "
        f"{storage is not None}"
    )

    print("Context engine: Enabled")

    print("Web search: Enabled")
    print("Web reader: Enabled")
    print("Web research: Enabled")

    print("Documents: Enabled")
    print("Document extraction: Enabled")

    print("Multimodal: Enabled")
    print("Unified multimodal context: Enabled")
    print("Unified multimodal reasoning: Enabled")
    print("Image understanding: Enabled")

    print(
        "Audio understanding: "
        "Enabled (native local)"
    )

    print("Audio transcription: Enabled")
    print("Audio model: faster-whisper")
    print("Audio provider: Local")

    print("Video understanding: Enabled")

    # --------------------------------------------------------
    # Start automation scheduler
    # --------------------------------------------------------

    await automation_scheduler.start(
        automation_engine.handle_due_automation
    )

    print("Automation engine: Enabled")
    print("Automation scheduler: Enabled")
    print("Automation poll interval: 5 seconds")

    print("=" * 60)
    print("VAIRRIEN READY")
    print("=" * 60)
    print()


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():

    print()
    print("=" * 60)
    print("VAIRRIEN SHUTDOWN")
    print("=" * 60)

    await automation_scheduler.stop()

    print("Automation scheduler: Stopped")
    print("VAIRRIEN STOPPED")
    print("=" * 60)
    print()
