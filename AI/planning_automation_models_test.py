from __future__ import annotations

from datetime import datetime, timezone

from vairrien_ai.automation.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    AutomationScheduleType,
    AutomationStatus,
)


def main():
    now = datetime.now(timezone.utc)

    automation = Automation(
        id="automation-test-1",
        user_id="user-test-1",
        conversation_id="conversation-test-1",
        name="Daily research",
        description="Check for important updates every morning.",
        schedule_type=AutomationScheduleType.CRON,
        schedule_data={
            "expression": "0 9 * * *",
            "timezone": "Africa/Lagos",
        },
        action_data={
            "type": "ai_task",
            "instruction": "Check for important updates.",
        },
        next_run_at=now,
    )

    # Basic state
    assert automation.is_active()
    assert automation.status == AutomationStatus.ACTIVE
    assert automation.run_count == 0

    # Serialization
    data = automation.to_dict()

    restored = Automation.from_dict(data)

    assert restored.id == automation.id
    assert restored.user_id == automation.user_id
    assert restored.name == automation.name
    assert restored.schedule_type == AutomationScheduleType.CRON
    assert restored.schedule_data == automation.schedule_data
    assert restored.action_data == automation.action_data
    assert restored.status == AutomationStatus.ACTIVE

    # State transitions
    restored.mark_paused()

    assert restored.status == AutomationStatus.PAUSED
    assert not restored.is_active()

    restored.mark_active()

    assert restored.status == AutomationStatus.ACTIVE
    assert restored.is_active()

    # Record successful execution
    restored.record_success(
        {
            "message": "Automation executed successfully."
        }
    )

    assert restored.run_count == 1
    assert restored.last_result is not None
    assert restored.last_error is None
    assert restored.last_run_at is not None

    # Automation run
    run = AutomationRun(
        id="run-test-1",
        automation_id=restored.id,
        user_id=restored.user_id,
        status=AutomationRunStatus.RUNNING,
        started_at=now,
    )

    assert run.status == AutomationRunStatus.RUNNING

    run.mark_completed(
        {
            "message": "Run completed successfully."
        }
    )

    assert run.status == AutomationRunStatus.COMPLETED
    assert run.completed_at is not None
    assert run.result is not None
    assert run.error is None

    # Run serialization
    run_data = run.to_dict()
    restored_run = AutomationRun.from_dict(run_data)

    assert restored_run.id == run.id
    assert restored_run.automation_id == run.automation_id
    assert restored_run.status == AutomationRunStatus.COMPLETED
    assert restored_run.result == run.result

    print("AUTOMATION MODEL: OK")


if __name__ == "__main__":
    main()