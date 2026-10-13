from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class PlanTask:
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    result: Any | None = None
    error: str | None = None
    attempts: int = 0

    def is_ready(self, completed_task_ids: set[str]) -> bool:
        if self.status not in {
            TaskStatus.PENDING,
            TaskStatus.READY,
        }:
            return False

        return all(
            dependency in completed_task_ids
            for dependency in self.dependencies
        )

    def mark_in_progress(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.attempts += 1
        self.error = None

    def mark_completed(self, result: Any = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.error = None

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error

    def mark_blocked(self, reason: str | None = None) -> None:
        self.status = TaskStatus.BLOCKED
        self.error = reason

    def mark_skipped(self, reason: str | None = None) -> None:
        self.status = TaskStatus.SKIPPED
        self.error = reason

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanTask":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            dependencies=list(data.get("dependencies", [])),
            capabilities=list(data.get("capabilities", [])),
            result=data.get("result"),
            error=data.get("error"),
            attempts=int(data.get("attempts", 0)),
        )


@dataclass
class Plan:
    id: str
    goal: str
    tasks: list[PlanTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_task(self, task_id: str) -> PlanTask | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def completed_task_ids(self) -> set[str]:
        return {
            task.id
            for task in self.tasks
            if task.status == TaskStatus.COMPLETED
        }

    def ready_tasks(self) -> list[PlanTask]:
        completed = self.completed_task_ids()

        return [
            task
            for task in self.tasks
            if task.is_ready(completed)
        ]

    def mark_active(self) -> None:
        self.status = PlanStatus.ACTIVE

    def mark_completed(self) -> None:
        self.status = PlanStatus.COMPLETED

    def mark_failed(self) -> None:
        self.status = PlanStatus.FAILED

    def mark_paused(self) -> None:
        self.status = PlanStatus.PAUSED

    def mark_cancelled(self) -> None:
        self.status = PlanStatus.CANCELLED

    def is_complete(self) -> bool:
        if not self.tasks:
            return False

        return all(
            task.status in {
                TaskStatus.COMPLETED,
                TaskStatus.SKIPPED,
            }
            for task in self.tasks
        )

    def has_failed_tasks(self) -> bool:
        return any(
            task.status == TaskStatus.FAILED
            for task in self.tasks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "tasks": [
                task.to_dict()
                for task in self.tasks
            ],
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            id=str(data["id"]),
            goal=str(data["goal"]),
            tasks=[
                PlanTask.from_dict(task)
                for task in data.get("tasks", [])
            ],
            status=PlanStatus(
                data.get(
                    "status",
                    PlanStatus.PENDING.value,
                )
            ),
            metadata=dict(data.get("metadata", {})),
        )