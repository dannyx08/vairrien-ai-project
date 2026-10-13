from __future__ import annotations

from typing import Any, Awaitable, Callable


class TaskRecovery:
    """
    Recovery controller for Vairrien's multi-step task execution.

    Responsibilities:
    - Detect failed tasks
    - Retry recoverable failures
    - Track retry attempts
    - Preserve task state
    - Continue execution after successful recovery
    - Stop when a task cannot be recovered
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
    ):
        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1."
            )

        self.max_attempts = max_attempts

    # ========================================================
    # ERROR CLASSIFICATION
    # ========================================================

    def is_recoverable(
        self,
        error: Any,
    ) -> bool:
        """
        Determine whether a failed task should be retried.

        Most runtime/tool failures are considered recoverable.
        Explicitly unrecoverable failures include invalid task
        definitions and permission/security failures.
        """

        if error is None:
            return False

        error_text = str(error).lower()

        unrecoverable_patterns = (
            "permission denied",
            "not authorized",
            "unauthorized",
            "forbidden",
            "invalid task",
            "invalid arguments",
            "missing required argument",
            "security violation",
        )

        return not any(
            pattern in error_text
            for pattern in unrecoverable_patterns
        )

    # ========================================================
    # RETRY CHECK
    # ========================================================

    def can_retry(
        self,
        task: Any,
    ) -> bool:
        """
        Determine whether a task has remaining retry attempts.
        """

        attempts = getattr(
            task,
            "attempts",
            0,
        )

        return attempts < self.max_attempts

    # ========================================================
    # RECORD FAILURE
    # ========================================================

    def record_failure(
        self,
        task: Any,
        error: Any,
    ) -> None:
        """
        Record a task failure without immediately abandoning
        the task.
        """

        if hasattr(task, "mark_failed"):
            task.mark_failed(
                str(error)
            )
            return

        task.error = str(error)

        if hasattr(
            task,
            "status",
        ):
            task.status = "failed"

    # ========================================================
    # RECOVERY
    # ========================================================

    async def recover(
        self,
        task: Any,
        execute: Callable[[], Awaitable[Any]],
    ) -> dict[str, Any]:
        """
        Execute a task with automatic recovery.

        The execute callback performs the actual task execution.

        Returns a structured result describing:
        - success
        - attempts
        - recovery
        - final result/error
        """

        attempts = 0
        last_error = None

        while attempts < self.max_attempts:
            attempts += 1

            # ----------------------------------------------
            # Track attempt
            # ----------------------------------------------

            if hasattr(task, "attempts"):
                task.attempts = attempts

            try:
                result = await execute()

                # ------------------------------------------
                # Successful execution
                # ------------------------------------------

                if hasattr(
                    task,
                    "mark_completed",
                ):
                    task.mark_completed(
                        result
                    )
                else:
                    task.result = result

                    if hasattr(
                        task,
                        "status",
                    ):
                        task.status = "completed"

                return {
                    "status": "success",
                    "task_id": getattr(
                        task,
                        "id",
                        None,
                    ),
                    "attempts": attempts,
                    "recovered": attempts > 1,
                    "result": result,
                }

            except Exception as error:
                last_error = error

                self.record_failure(
                    task,
                    error,
                )

                # ------------------------------------------
                # Determine whether recovery is possible
                # ------------------------------------------

                if not self.is_recoverable(
                    error
                ):
                    break

                if not self.can_retry(
                    task
                ):
                    break

        # ====================================================
        # RECOVERY FAILED
        # ====================================================

        return {
            "status": "error",
            "task_id": getattr(
                task,
                "id",
                None,
            ),
            "attempts": attempts,
            "recovered": False,
            "error": str(last_error),
        }