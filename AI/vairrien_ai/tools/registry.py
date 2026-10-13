from typing import Any, Callable


class ToolRegistry:
    """
    Central capability registry and execution layer for Vairrien AI.

    Every Vairrien action is registered here.

    The registry handles:
    - tool registration
    - tool discovery
    - tool schemas for the model
    - tool execution
    - trusted runtime context
    - enabled/disabled state
    - tool metadata
    """

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
        parameters: dict[str, Any] | None = None,
        *,
        category: str = "general",
        requires_approval: bool = False,
        enabled: bool = True,
    ) -> None:
        """
        Register a Vairrien capability.
        """

        if not name:
            raise ValueError(
                "Tool name cannot be empty."
            )

        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        if not callable(function):
            raise TypeError(
                f"Tool function must be callable: {name}"
            )

        self._tools[name] = {
            "name": name,
            "description": description,
            "function": function,
            "parameters": parameters or {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            },
            "category": category,
            "requires_approval": requires_approval,
            "enabled": enabled,
        }

    # ========================================================
    # MANAGEMENT
    # ========================================================

    def unregister(
        self,
        name: str,
    ) -> None:
        self._tools.pop(name, None)

    def enable(
        self,
        name: str,
    ) -> None:
        tool = self.get(name)

        if tool is None:
            raise ValueError(
                f"Unknown tool: {name}"
            )

        tool["enabled"] = True

    def disable(
        self,
        name: str,
    ) -> None:
        tool = self.get(name)

        if tool is None:
            raise ValueError(
                f"Unknown tool: {name}"
            )

        tool["enabled"] = False

    # ========================================================
    # DISCOVERY
    # ========================================================

    def get(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        return self._tools.get(name)

    def list_tools(
        self,
        *,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Return safe tool metadata.

        The actual Python function is never exposed to the model.
        """

        tools = []

        for tool in self._tools.values():

            if enabled_only and not tool["enabled"]:
                continue

            tools.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                    "category": tool["category"],
                    "requires_approval": tool[
                        "requires_approval"
                    ],
                    "enabled": tool["enabled"],
                }
            )

        return tools

    def list_categories(self) -> list[str]:
        return sorted(
            {
                tool["category"]
                for tool in self._tools.values()
            }
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    async def execute(
        self,
        name: str,
        *,
        context: dict[str, Any] | None = None,
        **arguments: Any,
    ) -> Any:
        """
        Execute a registered tool.

        Model-generated arguments:
            **arguments

        Trusted Vairrien runtime context:
            context

        The two are deliberately kept separate.
        """

        tool = self.get(name)

        if tool is None:
            raise ValueError(
                f"Unknown tool: {name}"
            )

        if not tool["enabled"]:
            raise RuntimeError(
                f"Tool is disabled: {name}"
            )

        function = tool["function"]

        execution_context = context or {}

        result = function(
            context=execution_context,
            **arguments,
        )

        if hasattr(result, "__await__"):
            result = await result

        return result

    # ========================================================
    # INFORMATION
    # ========================================================

    def count(
        self,
        *,
        enabled_only: bool = False,
    ) -> int:
        if enabled_only:
            return sum(
                1
                for tool in self._tools.values()
                if tool["enabled"]
            )

        return len(self._tools)

    def has(
        self,
        name: str,
    ) -> bool:
        return name in self._tools
