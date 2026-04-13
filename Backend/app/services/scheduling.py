from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.or_scheduler import ORScheduler


class SchedulingService:
    """
    DEPRECATED: This class now acts as a thin wrapper around ORScheduler.
    All rule-based logic has been replaced by OR-Tools mathematical optimization.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._or_scheduler = ORScheduler(session)

    def schedule_visit(self, visit_id: int, reason: str = 'visit scheduling') -> list:
        """Delegated to OR optimizer."""
        # Run OR optimization which handles all constraints automatically
        self._or_scheduler.run_optimization()
        return []

    def reschedule_for_lab(self, lab_id: int, reason: str = 'lab change') -> None:
        """No-op: OR solver handles this automatically on next run."""
        pass

    def reschedule_for_specialist(self, specialist_id: int, reason: str = 'specialist change') -> None:
        """No-op: OR solver handles this automatically on next run."""
        pass

    def refill_lab_queue(self, lab_id: int) -> None:
        """DEPRECATED: NEXT queue is managed by OR solver."""
        pass

    def refill_all_queues(self) -> None:
        """DEPRECATED: All queues are managed by OR solver."""
        pass

    def schedule_all(self) -> None:
        """Run OR optimization for all pending tests."""
        self._or_scheduler.run_optimization()

    def rebuild_for_visit(self, visit_id: int, reason: str = 'visit changed') -> None:
        """No-op: OR solver handles dependency changes automatically."""
        pass
