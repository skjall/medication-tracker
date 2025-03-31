"""
Task scheduler module for running periodic background tasks.

This module provides a robust framework for scheduling and managing
background tasks in the Flask application.
"""

import threading
import logging
import atexit
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PeriodicTask:
    """A task that runs periodically at fixed intervals."""

    def __init__(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        args: Optional[List] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a periodic task.

        Args:
            name: Name of the task for identification and logging
            func: Function to call when executing the task
            interval_seconds: How often to run the task in seconds
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
        """
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.args = args or []
        self.kwargs = kwargs or {}
        self.last_run: Optional[datetime] = None
        self.is_running = False
        self.error_count = 0

    def run(self) -> None:
        """Execute the task function with the specified arguments."""
        if self.is_running:
            logger.warning(
                f"Task {self.name} is already running, skipping this execution"
            )
            return

        try:
            self.is_running = True
            logger.info(f"Running task: {self.name}")
            self.func(*self.args, **self.kwargs)
            self.last_run = datetime.now(timezone.utc)
            self.error_count = 0  # Reset error count on successful execution
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error executing task {self.name}: {e}", exc_info=True)
        finally:
            self.is_running = False

    def should_run(self, current_time: datetime) -> bool:
        """
        Check if the task should run based on its interval and specific time constraints.

        Args:
            current_time: Current datetime for comparison

        Returns:
            True if task should run, False otherwise
        """
        # First run
        if self.last_run is None:
            # Special handling for specific interval tasks
            if self.interval_seconds == 43200:  # 12-hour task
                return (
                    current_time.hour in [9, 21]
                    and current_time.minute == 0
                    and current_time.second < 10
                )

            # Standard hourly task handling
            if self.interval_seconds == 3600:
                return current_time.minute == 0 and current_time.second < 10

            # Fallback to standard interval check
            return True

        # Calculate seconds since last run
        time_since_last_run = (current_time - self.last_run).total_seconds()

        # Specific handling for 12-hour tasks
        if self.interval_seconds == 43200:  # 12-hour interval
            return (
                current_time.hour in [9, 21]
                and current_time.minute == 0
                and current_time.second < 10
                and time_since_last_run >= 43100
            )  # Allow some flexibility

        # For hourly tasks
        if self.interval_seconds == 3600:
            return (
                current_time.minute == 0
                and current_time.second < 10
                and time_since_last_run >= 3550
            )

        # Fallback to standard interval check for other tasks
        return time_since_last_run >= self.interval_seconds


class TaskScheduler:
    """Scheduler for managing and executing periodic tasks."""

    def __init__(self, app=None):
        """
        Initialize the task scheduler.

        Args:
            app: Optional Flask application to initialize with
        """
        self.tasks: Dict[str, PeriodicTask] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._sleep_interval = 1  # Check tasks every second
        self._shutdown_event = threading.Event()

        # Keep track of app reference
        self.app = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        """
        Initialize the scheduler with a Flask application.

        Args:
            app: Flask application instance
        """
        self.app = app

        # Register shutdown function
        atexit.register(self.shutdown)

        # Create healthcheck endpoint
        @app.route("/api/scheduler/status")
        def scheduler_status():
            from flask import jsonify

            status = {
                "running": self.running,
                "tasks": [
                    {
                        "name": name,
                        "last_run": (
                            task.last_run.isoformat() if task.last_run else None
                        ),
                        "interval_seconds": task.interval_seconds,
                        "is_running": task.is_running,
                        "error_count": task.error_count,
                    }
                    for name, task in self.tasks.items()
                ],
            }
            return jsonify(status)

        # Add configuration from app
        app.config.setdefault("SCHEDULER_AUTO_START", True)

        # Auto-start if configured
        if app.config["SCHEDULER_AUTO_START"]:
            with app.app_context():
                self.start()

        # Store reference in app
        app.scheduler = self

    def add_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        args: Optional[List] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a new task to the scheduler.

        Args:
            name: Unique name for the task
            func: Function to execute
            interval_seconds: How often to run the task in seconds
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        if name in self.tasks:
            logger.warning(f"Task {name} already exists, replacing it")

        task = PeriodicTask(name, func, interval_seconds, args, kwargs)
        self.tasks[name] = task
        logger.info(f"Added task '{name}' with interval {interval_seconds} seconds")

    def remove_task(self, name: str) -> bool:
        """
        Remove a task from the scheduler.

        Args:
            name: Name of the task to remove

        Returns:
            True if task was removed, False if not found
        """
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed task '{name}'")
            return True
        return False

    def start(self) -> None:
        """Start the scheduler if it's not already running."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting task scheduler")
        self.running = True
        self._shutdown_event.clear()  # Clear the shutdown event
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def shutdown(self) -> None:
        """Stop the scheduler gracefully."""
        if not self.running:
            return

        try:
            logger.info("Shutting down task scheduler")
        except Exception:
            # Ignore errors that happen during logging shutdown
            pass

        self.running = False
        self._shutdown_event.set()  # Signal the thread to exit

        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=5)
            except Exception:
                # Ignore thread join errors during shutdown
                pass

    def _run_scheduler(self) -> None:
        """Main scheduler loop to check and execute tasks."""
        try:
            logger.info("Scheduler thread started")

            while self.running and not self._shutdown_event.is_set():
                current_time = datetime.now(timezone.utc)

                for name, task in self.tasks.items():
                    # Skip if shutdown was requested
                    if self._shutdown_event.is_set():
                        break

                    # Check if this task should run now
                    if task.should_run(current_time):
                        if self.app:
                            # Run within app context if we have an app
                            with self.app.app_context():
                                task.run()
                        else:
                            task.run()

                # Sleep until next check, but allow for early interrupt
                self._shutdown_event.wait(timeout=self._sleep_interval)

            try:
                logger.info("Scheduler thread stopped")
            except Exception:
                # Ignore errors that happen during logging shutdown
                pass

        except Exception as e:
            # Catch all exceptions to avoid thread crashes
            try:
                logger.error(f"Scheduler thread error: {e}", exc_info=True)
            except Exception:
                # Ignore errors that happen during logging shutdown
                pass

    def restart(self) -> None:
        """
        Restart the scheduler by stopping and starting it again.

        This will gracefully shut down the current thread and start a new one.
        """
        logger.info("Restarting task scheduler")

        # Shut down if running
        if self.running:
            self.shutdown()

        # Start again
        self.start()

        logger.info("Task scheduler restarted")
