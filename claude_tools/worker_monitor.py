#!/usr/bin/env python3
"""
Worker Activity Monitor

A modular, thread-safe worker monitoring system for real-time activity display.
Can be used with various types of worker tasks beyond just breakdown loops.
"""

import threading
import time
import sys
from typing import Dict, Optional
from enum import Enum


class WorkerState(Enum):
    """Worker state enumeration"""
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class WorkerMonitor:
    """
    A modular worker monitoring system for real-time activity display.

    Features:
    - Thread-safe updates
    - Real-time display with line overwriting
    - Support for multiple workers
    - Generic interface for various task types
    """

    def __init__(self, max_workers: int = 1):
        """
        Initialize WorkerMonitor

        Args:
            max_workers: Maximum number of workers to monitor
        """
        self.max_workers = max_workers
        self._lock = threading.Lock()
        self._display_lock = threading.Lock()

        # Worker status data
        self._workers = {}
        for i in range(1, max_workers + 1):
            self._workers[i] = {
                'status': 'IDLE',
                'state': WorkerState.IDLE,
                'last_update': time.time()
            }

        # Display management
        self._display_active = False
        self._display_thread = None
        self._stop_display = threading.Event()

    def update_worker(self, worker_id: int, status: str, state: WorkerState = WorkerState.ACTIVE):
        """
        Update worker status and state

        Args:
            worker_id: ID of the worker (1-based)
            status: Status text to display
            state: Worker state (IDLE/ACTIVE/COMPLETED/ERROR)
        """
        if worker_id not in self._workers:
            print(f"[ERROR] Worker {worker_id} not found (max: {self.max_workers})")
            return

        with self._lock:
            self._workers[worker_id]['status'] = status
            self._workers[worker_id]['state'] = state
            self._workers[worker_id]['last_update'] = time.time()

    def set_worker_idle(self, worker_id: int):
        """Set worker to idle state"""
        self.update_worker(worker_id, "IDLE", WorkerState.IDLE)

    def set_worker_completed(self, worker_id: int, message: str = "[COMPLETED]"):
        """Set worker to completed state"""
        self.update_worker(worker_id, message, WorkerState.COMPLETED)

    def set_worker_error(self, worker_id: int, error_message: str):
        """Set worker to error state"""
        self.update_worker(worker_id, f"[ERROR] {error_message}", WorkerState.ERROR)

    def start_display(self):
        """Start simple display with periodic updates"""
        if self._display_active:
            return

        self._display_active = True
        self._stop_display.clear()

        print("\n=== WORKER ACTIVITY ===")
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()

    def stop_display(self):
        """Stop display and show final status"""
        if not self._display_active:
            return

        self._stop_display.set()
        if self._display_thread:
            self._display_thread.join(timeout=1.0)
        self._display_active = False

        # Final display
        self._display_workers()
        print("=====================\n")

    def _display_loop(self):
        """Display loop running in separate thread"""
        while not self._stop_display.is_set():
            time.sleep(2)  # Update every 2 seconds
            if not self._stop_display.is_set():
                self._display_workers()

    def _display_workers(self):
        """Display current worker status - simple multi-line approach"""
        if not self._display_active:
            return

        # Simple approach: just print workers on new lines
        # Each update will create new lines instead of overwriting
        # This ensures compatibility across all terminals

        # Display each worker on separate line with timestamp
        for worker_id in range(1, self.max_workers + 1):
            with self._lock:
                worker_data = self._workers[worker_id]
                status = worker_data['status']
                state = worker_data['state']

            # State display based on state
            if state == WorkerState.ACTIVE:
                state_display = "[ACTIVE]"
            elif state == WorkerState.COMPLETED:
                state_display = "[OK]"
            elif state == WorkerState.ERROR:
                state_display = "[ERROR]"
            else:
                state_display = "[IDLE]"

            # Clean and truncate status
            clean_status = status.replace('\n', ' ').replace('\r', '')
            if len(clean_status) > 40:
                clean_status = clean_status[:37] + "..."

            # Format: W1:status [STATE] | HH:MM:SS
            current_time = time.strftime("%H:%M:%S")
            worker_line = f"W{worker_id}:{clean_status} {state_display} | {current_time}"

            print(worker_line)

        # Print separator to distinguish updates
        print("-" * 60)

    def get_worker_count_by_state(self, state: WorkerState) -> int:
        """Get number of workers in specific state"""
        count = 0
        with self._lock:
            for worker_data in self._workers.values():
                if worker_data['state'] == state:
                    count += 1
        return count

    def get_summary(self) -> Dict[str, int]:
        """Get summary of worker states"""
        summary = {
            'IDLE': 0,
            'ACTIVE': 0,
            'COMPLETED': 0,
            'ERROR': 0
        }

        with self._lock:
            for worker_data in self._workers.values():
                state_name = worker_data['state'].name
                summary[state_name] += 1

        return summary

    def reset_all(self):
        """Reset all workers to idle state"""
        for worker_id in range(1, self.max_workers + 1):
            self.set_worker_idle(worker_id)

    def __enter__(self):
        """Context manager entry"""
        self.start_display()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_display()


# Example usage for reference
if __name__ == "__main__":
    # Demo of WorkerMonitor functionality
    with WorkerMonitor(max_workers=3) as monitor:
        monitor.update_worker(1, "Starting task...", WorkerState.ACTIVE)
        time.sleep(1)

        monitor.update_worker(2, "Processing file...", WorkerState.ACTIVE)
        time.sleep(1)

        monitor.update_worker(1, "Analyzing data...", WorkerState.ACTIVE)
        time.sleep(1)

        monitor.set_worker_completed(1, "Task completed successfully")
        time.sleep(0.5)

        monitor.update_worker(3, "Starting background task...", WorkerState.ACTIVE)
        time.sleep(1)

        monitor.set_worker_error(2, "File not found")
        time.sleep(0.5)

        monitor.set_worker_completed(3, "Background task done")
        time.sleep(1)