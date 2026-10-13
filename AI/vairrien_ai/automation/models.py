from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AutomationStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AutomationScheduleType(str, Enum):
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


class AutomationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Automation:
    id: str
    user_id: str
    conversation_id: str

    name: str
    description: str

    schedule_type: AutomationScheduleType
    schedule_data: dict[str, Any]

    action_data: dict[str, Any]

    status: AutomationStatus = AutomationStatus.ACTIVE

    next_run_at: datetime | None = None
    last_run_at: datetime | None = None

    run_count: int = 0

    last_result: dict[str, Any] | None = None
    last_error: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status == AutomationStatus.ACTIVE

    def mark_paused(self) -> None:
        self.status = AutomationStatus.PAUSED

    def mark_active(self) -> None:
        self.status = AutomationStatus.ACTIVE
        self.last_error = None

    def mark_cancelled(self) -> None:
        self.status = AutomationStatus.CANCELLED

    def mark_completed(self) -> None:
        self.status = AutomationStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        self.status = AutomationStatus.FAILED
        self.last_error = error

    def record_success(
        self,
        result: dict[str, Any] | None = None,
    ) -> None:
        self.run_count += 1
        self.last_run_at = datetime.now().astimezone()
        self.last_result = result
        self.last_error = None

    def record_failure(self, error: str) -> None:
        self.run_count += 1
        self.last_run_at = datetime.now().astimezone()
        self.last_error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type.value,
            "schedule_data": self.schedule_data,
            "action_data": self.action_data,
            "status": self.status.value,
            "next_run_at": (
                self.next_run_at.isoformat()
                if self.next_run_at
                else None
            ),
            "last_run_at": (
                self.last_run_at.isoformat()
                if self.last_run_at
                else None
            ),
            "run_count": self.run_count,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Automation":
        def parse_datetime(
            value: Any,
        ) -> datetime | None:
            if not value:
                return None

            if isinstance(value, datetime):
                return value

            return datetime.fromisoformat(str(value))

        return cls(
            id=str(data["id"]),
            user_id=str(data["user_id"]),
            conversation_id=str(data["conversation_id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            schedule_type=AutomationScheduleType(
                data["schedule_type"]
            ),
            schedule_data=dict(
                data.get("schedule_data") or {}
            ),
            action_data=dict(
                data.get("action_data") or {}
            ),
            status=AutomationStatus(
                data.get(
                    "status",
                    AutomationStatus.ACTIVE.value,
                )
            ),
            next_run_at=parse_datetime(
                data.get("next_run_at")
            ),
            last_run_at=parse_datetime(
                data.get("last_run_at")
            ),
            run_count=int(
                data.get("run_count", 0)
            ),
            last_result=data.get("last_result"),
            last_error=data.get("last_error"),
            created_at=parse_datetime(
                data.get("created_at")
            ),
            updated_at=parse_datetime(
                data.get("updated_at")
            ),
            metadata=dict(
                data.get("metadata") or {}
            ),
        )


@dataclass
class AutomationRun:
    id: str
    automation_id: str
    user_id: str

    status: AutomationRunStatus

    started_at: datetime | None = None
    completed_at: datetime | None = None

    result: dict[str, Any] | None = None
    error: str | None = None

    attempts: int = 1

    def mark_completed(
        self,
        result: dict[str, Any] | None = None,
    ) -> None:
        self.status = AutomationRunStatus.COMPLETED
        self.completed_at = datetime.now().astimezone()
        self.result = result
        self.error = None

    def mark_failed(
        self,
        error: str,
    ) -> None:
        self.status = AutomationRunStatus.FAILED
        self.completed_at = datetime.now().astimezone()
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "user_id": self.user_id,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "AutomationRun":
        def parse_datetime(
            value: Any,
        ) -> datetime | None:
            if not value:
                return None

            if isinstance(value, datetime):
                return value

            return datetime.fromisoformat(str(value))

        return cls(
            id=str(data["id"]),
            automation_id=str(
                data["automation_id"]
            ),
            user_id=str(data["user_id"]),
            status=AutomationRunStatus(
                data.get(
                    "status",
                    AutomationRunStatus.RUNNING.value,
                )
            ),
            started_at=parse_datetime(
                data.get("started_at")
            ),
            completed_at=parse_datetime(
                data.get("completed_at")
            ),
            result=data.get("result"),
            error=data.get("error"),
            attempts=int(
                data.get("attempts", 1)
            ),
        )