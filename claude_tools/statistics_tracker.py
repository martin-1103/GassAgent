#!/usr/bin/env python3
"""
Statistics Tracker

Shared statistics tracking class for run.py, break.py, and init.py
"""

from datetime import datetime
from typing import Dict, Any, Optional


class StatisticsTracker:
    """Shared statistics tracking for all operations"""

    def __init__(self, operation_name: str):
        """
        Initialize statistics tracker

        Args:
            operation_name: Name of the operation being tracked
        """
        self.operation_name = operation_name
        self.start_time = None
        self.total_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.completed_items = 0
        self.error_items = 0

    def start_timing(self):
        """Start timing the operation"""
        self.start_time = datetime.now()

    def increment_total(self):
        """Increment total items count"""
        self.total_items += 1

    def increment_success(self):
        """Increment successful items count"""
        self.successful_items += 1

    def increment_failure(self):
        """Increment failed items count"""
        self.failed_items += 1

    def increment_completed(self):
        """Increment completed items count"""
        self.completed_items += 1

    def increment_error(self):
        """Increment error items count"""
        self.error_items += 1

    def update_success(self, success: bool):
        """
        Update statistics based on success status

        Args:
            success: Whether the operation was successful
        """
        self.increment_total()
        if success:
            self.increment_success()
        else:
            self.increment_failure()

    def get_elapsed_time(self) -> Optional[str]:
        """
        Get elapsed time as formatted string

        Returns:
            Formatted elapsed time string or None if not started
        """
        if not self.start_time:
            return None

        elapsed = datetime.now() - self.start_time
        total_seconds = int(elapsed.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_success_rate(self) -> float:
        """
        Calculate success rate as percentage

        Returns:
            Success rate percentage (0-100)
        """
        if self.total_items == 0:
            return 0.0
        return (self.successful_items / self.total_items) * 100

    def get_summary_dict(self) -> Dict[str, Any]:
        """
        Get statistics summary as dictionary

        Returns:
            Dictionary with all statistics
        """
        return {
            'operation': self.operation_name,
            'total': self.total_items,
            'successful': self.successful_items,
            'failed': self.failed_items,
            'completed': self.completed_items,
            'errors': self.error_items,
            'success_rate': self.get_success_rate(),
            'elapsed_time': self.get_elapsed_time(),
            'start_time': self.start_time.isoformat() if self.start_time else None
        }

    def print_summary(self):
        """Print formatted statistics summary"""
        print(f"\n--- {self.operation_name.title()} Summary ---")
        print(f"Total items: {self.total_items}")
        print(f"Successful: {self.successful_items}")
        print(f"Failed: {self.failed_items}")
        if self.completed_items != self.total_items:
            print(f"Completed: {self.completed_items}")
        if self.error_items > 0:
            print(f"Errors: {self.error_items}")

        if self.start_time:
            print(f"Elapsed time: {self.get_elapsed_time()}")

        success_rate = self.get_success_rate()
        print(f"Success rate: {success_rate:.1f}%")

    def print_progress(self, current_item: Optional[str] = None):
        """
        Print current progress

        Args:
            current_item: Description of current item being processed
        """
        if current_item:
            print(f"Progress: {self.successful_items + self.failed_items}/{self.total_items} - {current_item}")
        else:
            print(f"Progress: {self.successful_items + self.failed_items}/{self.total_items}")

    def reset(self):
        """Reset all statistics"""
        self.start_time = None
        self.total_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.completed_items = 0
        self.error_items = 0

    def is_complete(self) -> bool:
        """
        Check if all items have been processed

        Returns:
            True if all items processed, False otherwise
        """
        return self.total_items > 0 and (self.successful_items + self.failed_items) >= self.total_items

    def get_status_message(self) -> str:
        """
        Get status message based on current statistics

        Returns:
            Status message string
        """
        if self.total_items == 0:
            return "No items processed"
        elif self.failed_items == 0:
            return "All operations completed successfully"
        elif self.successful_items == 0:
            return "All operations failed"
        else:
            return f"Operations completed with {self.failed_items} failures"