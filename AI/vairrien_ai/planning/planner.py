from __future__ import annotations

import json
from typing import Any

from vairrien_ai.planning.models import (
    Plan,
    PlanTask,
    TaskStatus,
)


class VairrienPlanner:
    """
    Converts complex user goals into structured executable plans.

    The planner is responsible for:
    - deciding whether a task needs multiple steps
    - generating ordered/dependent tasks
    - identifying required capabilities
    - validating the resulting plan

    The planner does NOT execute tools or tasks.
    Execution remains the responsibility of the orchestrator.
    """

    PLANNER_SYSTEM_PROMPT = """
You are the planning engine inside Vairrien AI.

Your job is to decompose a user's goal into a clear, executable
multi-step plan when multiple steps are genuinely required.

Do not solve the user's task yourself.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
  "goal": "the user's overall goal",
  "tasks": [
    {
      "id": "step-1",
      "title": "short task title",
      "description": "what this step must accomplish",
      "dependencies": [],
      "capabilities": []
    }
  ]
}

PLANNING RULES

1. Break genuinely complex goals into logical steps.
2. Do not create unnecessary steps.
3. Every task must have a unique ID.
4. IDs must use the format step-1, step-2, step-3, etc.
5. Dependencies must reference existing task IDs.
6. A task may depend on multiple earlier tasks.
7. Tasks with no dependencies can run first.
8. Put tasks in logical execution order.
9. Identify the Vairrien capabilities needed for each task.

Available capabilities may include:

- web_search
- web_fetch
- web_read
- web_research
- document_extract
- multimodal_understand_image
- audio_transcribe
- multimodal_understand_video
- memory
- reasoning
- planning

Do not invent capabilities that are not listed.

10. Do not create a task merely for "thinking" or "reasoning" unless
that reasoning represents a meaningful separate stage of the user's goal.

11. If the request is simple and requires only one meaningful action,
return one task.

12. Do not perform tools or claim that tools were used.

13. Do not include markdown fences.

14. Return JSON only.
""".strip()

    def __init__(self, model: Any):
        if model is None:
            raise ValueError("A model provider is required.")

        self.model = model

    def _build_messages(self, goal: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": self.PLANNER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": goal,
            },
        ]

    def _extract_content(self, response: Any) -> str:
        if isinstance(response, dict):
            content = response.get("content")
        else:
            content = getattr(response, "content", None)

        if content is None:
            raise ValueError(
                "Planner model returned no content."
            )

        if not isinstance(content, str):
            content = str(content)

        return content.strip()

    def _clean_json(self, content: str) -> str:
        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(lines).strip()

            if content.lower().startswith("json"):
                content = content[4:].strip()

        return content

    def _parse_plan(
        self,
        raw_content: str,
        goal: str,
    ) -> Plan:
        content = self._clean_json(raw_content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Planner model returned invalid JSON: "
                f"{error}"
            ) from error

        if not isinstance(data, dict):
            raise ValueError(
                "Planner response must be a JSON object."
            )

        tasks_data = data.get("tasks")

        if not isinstance(tasks_data, list):
            raise ValueError(
                "Planner response must contain a 'tasks' list."
            )

        if not tasks_data:
            raise ValueError(
                "Planner returned an empty task list."
            )

        plan_goal = str(
            data.get("goal") or goal
        ).strip()

        if not plan_goal:
            plan_goal = goal

        tasks: list[PlanTask] = []
        task_ids: set[str] = set()

        for index, task_data in enumerate(tasks_data, start=1):
            if not isinstance(task_data, dict):
                raise ValueError(
                    f"Planner task {index} is not an object."
                )

            task_id = str(
                task_data.get("id") or f"step-{index}"
            ).strip()

            title = str(
                task_data.get("title") or ""
            ).strip()

            description = str(
                task_data.get("description") or ""
            ).strip()

            if not title:
                raise ValueError(
                    f"Planner task {task_id} has no title."
                )

            if task_id in task_ids:
                raise ValueError(
                    f"Duplicate planner task ID: {task_id}"
                )

            dependencies = task_data.get(
                "dependencies",
                [],
            )

            if not isinstance(dependencies, list):
                raise ValueError(
                    f"Dependencies for {task_id} must be a list."
                )

            capabilities = task_data.get(
                "capabilities",
                [],
            )

            if not isinstance(capabilities, list):
                raise ValueError(
                    f"Capabilities for {task_id} must be a list."
                )

            tasks.append(
                PlanTask(
                    id=task_id,
                    title=title,
                    description=description,
                    status=TaskStatus.PENDING,
                    dependencies=[
                        str(dependency)
                        for dependency in dependencies
                    ],
                    capabilities=[
                        str(capability)
                        for capability in capabilities
                    ],
                )
            )

            task_ids.add(task_id)

        for task in tasks:
            for dependency in task.dependencies:
                if dependency not in task_ids:
                    raise ValueError(
                        f"Task '{task.id}' depends on unknown "
                        f"task '{dependency}'."
                    )

                if dependency == task.id:
                    raise ValueError(
                        f"Task '{task.id}' cannot depend on itself."
                    )

        self._validate_no_cycles(tasks)

        return Plan(
            id="generated-plan",
            goal=plan_goal,
            tasks=tasks,
        )

    def _validate_no_cycles(
        self,
        tasks: list[PlanTask],
    ) -> None:
        dependencies = {
            task.id: set(task.dependencies)
            for task in tasks
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visited:
                return

            if task_id in visiting:
                raise ValueError(
                    "Planner generated a dependency cycle."
                )

            visiting.add(task_id)

            for dependency in dependencies.get(task_id, set()):
                visit(dependency)

            visiting.remove(task_id)
            visited.add(task_id)

        for task in dependencies:
            visit(task)

    async def create_plan(
        self,
        goal: str,
    ) -> Plan:
        if not goal or not goal.strip():
            raise ValueError(
                "Cannot create a plan without a goal."
            )

        response = await self.model.generate(
            messages=self._build_messages(goal.strip()),
        )

        content = self._extract_content(response)

        return self._parse_plan(
            raw_content=content,
            goal=goal.strip(),
        )