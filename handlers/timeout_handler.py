"""
Timeout Handler V2 - Graceful Timeout with Partial Output
==========================================================

Fixes Issue #5: Timeout Errors Causing Failures

Key improvements:
- Graceful timeout handling - never lose all work
- Checkpoint system saves progress as we go
- Warning before timeout hits to wrap up gracefully
- Always outputs something (even if partial)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeoutManager:
    """
    Manages operation timeouts with graceful degradation.

    Instead of hard failures at timeout, this:
    1. Tracks elapsed time
    2. Warns when approaching limit
    3. Allows graceful wrap-up
    4. Saves checkpoints for partial output
    """

    def __init__(
        self,
        max_seconds: int = 300,
        warning_at: int = 240,
        critical_at: Optional[int] = None
    ):
        """
        Initialize timeout manager.

        Args:
            max_seconds: Maximum time allowed (default 5 minutes)
            warning_at: When to start warning (default 4 minutes)
            critical_at: When to force stop (default max_seconds - 30)
        """
        self.max_seconds = max_seconds
        self.warning_at = warning_at
        self.critical_at = critical_at or (max_seconds - 30)
        self.start_time: Optional[datetime] = None
        self.completed_items: List[Any] = []
        self.checkpoints: List[Dict[str, Any]] = []

    def start(self):
        """Start the timeout timer."""
        self.start_time = datetime.now()
        self.completed_items = []
        self.checkpoints = []
        logger.info(f"Timeout timer started: {self.max_seconds}s limit")

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()

    def remaining(self) -> float:
        """Get remaining time in seconds."""
        return max(0, self.max_seconds - self.elapsed())

    def should_wrap_up(self) -> bool:
        """Return True if we should start wrapping up."""
        return self.elapsed() >= self.warning_at

    def is_critical(self) -> bool:
        """Return True if we must stop immediately."""
        return self.elapsed() >= self.critical_at

    def is_expired(self) -> bool:
        """Return True if we've exceeded max time."""
        return self.elapsed() >= self.max_seconds

    def checkpoint(self, item: Any, metadata: Optional[Dict] = None):
        """
        Save completed work as a checkpoint.

        Args:
            item: The completed item to save
            metadata: Optional metadata about the item
        """
        self.completed_items.append(item)
        self.checkpoints.append({
            "item": item,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "elapsed": self.elapsed()
        })

    def get_partial_output(self) -> List[Any]:
        """Return whatever work was completed."""
        return self.completed_items

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Return detailed checkpoint history."""
        return self.checkpoints

    def get_status(self) -> Dict[str, Any]:
        """Get current timeout status."""
        elapsed = self.elapsed()
        return {
            "elapsed_seconds": elapsed,
            "remaining_seconds": self.remaining(),
            "completed_items": len(self.completed_items),
            "should_wrap_up": self.should_wrap_up(),
            "is_critical": self.is_critical(),
            "is_expired": self.is_expired(),
            "percent_complete": (elapsed / self.max_seconds) * 100
        }


def process_with_timeout(
    items: List[Any],
    process_func: Callable[[Any], Any],
    config: Optional[Dict[str, Any]] = None,
    max_seconds: int = 300,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    on_warning: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Process items with graceful timeout handling.

    Fixes Issue #5: Timeout Errors Causing Failures

    Instead of failing completely:
    1. Processes items sequentially
    2. Saves progress after each item
    3. Warns when time is running out
    4. Returns partial results if timeout hits

    Args:
        items: List of items to process
        process_func: Function to call on each item
        config: Optional config dict passed to process_func
        max_seconds: Maximum time allowed
        on_progress: Callback(current, total, status_message)
        on_warning: Callback(warning_message)

    Returns:
        Dict with:
        - processed: List of successfully processed items
        - failed: List of items that failed
        - skipped: List of items skipped due to timeout
        - partial: bool - True if not all items processed
        - elapsed: Total time taken
    """
    timeout = TimeoutManager(
        max_seconds=max_seconds,
        warning_at=max_seconds - 60,  # Warn 1 minute before
        critical_at=max_seconds - 30   # Stop 30 seconds before
    )
    timeout.start()

    processed = []
    failed = []
    skipped = []

    total = len(items)

    for i, item in enumerate(items):
        # Check timeout status
        if timeout.is_critical():
            warning_msg = f"Time limit reached. Processed {len(processed)} of {total} items."
            logger.warning(warning_msg)
            if on_warning:
                on_warning(warning_msg)
            # Skip remaining items
            skipped.extend(items[i:])
            break

        if timeout.should_wrap_up():
            remaining = timeout.remaining()
            warning_msg = f"Approaching time limit ({remaining:.0f}s remaining). Wrapping up..."
            logger.warning(warning_msg)
            if on_warning:
                on_warning(warning_msg)

        # Progress callback
        if on_progress:
            on_progress(i + 1, total, f"Processing item {i + 1}/{total}")

        # Process item
        try:
            if config:
                result = process_func(item, config)
            else:
                result = process_func(item)

            processed.append({
                "item": item,
                "result": result,
                "success": True
            })
            timeout.checkpoint(item)

        except Exception as e:
            logger.warning(f"Failed to process item {i + 1}: {e}")
            failed.append({
                "item": item,
                "error": str(e),
                "success": False
            })

    # Build result
    result = {
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "partial": len(skipped) > 0,
        "total_items": total,
        "processed_count": len(processed),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "elapsed_seconds": timeout.elapsed(),
        "status": timeout.get_status()
    }

    if result["partial"]:
        logger.warning(f"Partial output: {len(processed)}/{total} items completed")
    else:
        logger.info(f"Complete: {len(processed)}/{total} items processed in {timeout.elapsed():.1f}s")

    return result


class ProgressTracker:
    """
    Track multi-step processing progress with timeout awareness.
    """

    def __init__(
        self,
        steps: List[str],
        max_seconds: int = 300
    ):
        """
        Initialize progress tracker.

        Args:
            steps: List of step names
            max_seconds: Maximum time for all steps
        """
        self.steps = steps
        self.current_step = 0
        self.step_progress: Dict[str, float] = {step: 0.0 for step in steps}
        self.step_status: Dict[str, str] = {step: "pending" for step in steps}
        self.timeout = TimeoutManager(max_seconds=max_seconds)

    def start(self):
        """Start tracking."""
        self.timeout.start()

    def begin_step(self, step_name: str):
        """Mark a step as in progress."""
        if step_name in self.step_status:
            self.step_status[step_name] = "running"
            logger.info(f"Starting step: {step_name}")

    def update_step_progress(self, step_name: str, percent: float):
        """Update progress for a step (0-100)."""
        if step_name in self.step_progress:
            self.step_progress[step_name] = min(100, max(0, percent))

    def complete_step(self, step_name: str):
        """Mark a step as completed."""
        if step_name in self.step_status:
            self.step_status[step_name] = "completed"
            self.step_progress[step_name] = 100.0
            logger.info(f"Completed step: {step_name}")

    def fail_step(self, step_name: str, error: str):
        """Mark a step as failed."""
        if step_name in self.step_status:
            self.step_status[step_name] = f"failed: {error}"
            logger.error(f"Failed step {step_name}: {error}")

    def get_overall_progress(self) -> float:
        """Get overall progress (0-100)."""
        if not self.steps:
            return 100.0
        total = sum(self.step_progress.values())
        return total / len(self.steps)

    def should_abort(self) -> bool:
        """Check if we should abort due to timeout."""
        return self.timeout.is_critical()

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "steps": self.step_status,
            "progress": self.step_progress,
            "overall_progress": self.get_overall_progress(),
            "timeout_status": self.timeout.get_status()
        }
