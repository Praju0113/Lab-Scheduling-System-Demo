"""
Planning Poker service for collaborative estimation.
Team members vote on test durations and complexity weights using consensus.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    pass


class VotingStatus(str, Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


@dataclass
class Vote:
    """Individual vote in a planning poker session."""
    user_id: str
    username: str
    value: int | None = None  # None = card not yet played
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EstimationSession:
    """Planning poker session for estimating a specific value."""
    id: str
    item_type: str  # 'test_duration', 'complexity_weight', 'mobility_weight'
    item_id: str  # test_code or category name
    item_name: str  # display name
    description: str
    votes: dict[str, Vote] = field(default_factory=dict)
    status: VotingStatus = VotingStatus.IN_PROGRESS
    final_value: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class PlanningPokerService:
    """
    Collaborative estimation using Planning Poker methodology.
    Team members vote on Fibonacci sequence to reach consensus.
    """
    
    # Standard Planning Poker Fibonacci sequence
    FIBONACCI_SEQUENCE = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
    
    # In-memory store for active sessions
    _sessions: dict[str, EstimationSession] = {}

    def __init__(self, db: Session) -> None:
        self.db = db

    @classmethod
    def get_session(cls, session_id: str) -> EstimationSession | None:
        """Get an active estimation session by ID."""
        return cls._sessions.get(session_id)

    @classmethod
    def list_sessions(cls, status: VotingStatus | None = None) -> list[EstimationSession]:
        """List all sessions, optionally filtered by status."""
        sessions = list(cls._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    def create_session(
        self, 
        item_type: str, 
        item_id: str, 
        item_name: str, 
        description: str = ""
    ) -> EstimationSession:
        """
        Create a new planning poker estimation session.
        
        Args:
            item_type: Type of item being estimated ('test_duration', 'complexity_weight')
            item_id: Unique identifier for the item
            item_name: Display name
            description: Additional context for voters
        """
        session_id = str(uuid.uuid4())[:8]
        session = EstimationSession(
            id=session_id,
            item_type=item_type,
            item_id=item_id,
            item_name=item_name,
            description=description
        )
        self._sessions[session_id] = session
        return session

    def join_session(self, session_id: str, user_id: str, username: str) -> EstimationSession:
        """Add a user to an estimation session."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != VotingStatus.IN_PROGRESS:
            raise ValueError(f"Session {session_id} is not in progress")

        if user_id not in session.votes:
            session.votes[user_id] = Vote(user_id=user_id, username=username)
        
        return session

    def cast_vote(self, session_id: str, user_id: str, value: int) -> EstimationSession:
        """
        Cast a vote in a planning poker session.
        Value must be in the Fibonacci sequence.
        """
        if value not in self.FIBONACCI_SEQUENCE:
            raise ValueError(f"Vote must be one of: {self.FIBONACCI_SEQUENCE}")

        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != VotingStatus.IN_PROGRESS:
            raise ValueError(f"Session {session_id} is not accepting votes")

        if user_id not in session.votes:
            raise ValueError(f"User {user_id} has not joined session {session_id}")

        session.votes[user_id].value = value
        session.votes[user_id].timestamp = datetime.now()
        
        return session

    def reveal_votes(self, session_id: str) -> EstimationSession:
        """Reveal all votes in a session (flip the cards)."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check all participants have voted
        not_voted = [v.username for v in session.votes.values() if v.value is None]
        if not_voted:
            raise ValueError(f"Waiting for votes from: {', '.join(not_voted)}")

        return session

    def calculate_consensus(self, votes: list[int]) -> int:
        """
        Calculate consensus value from votes.
        Uses median for robustness against outliers.
        Rounds to nearest Fibonacci number.
        """
        if not votes:
            raise ValueError("No votes to calculate consensus")

        sorted_votes = sorted(votes)
        n = len(sorted_votes)
        
        # Calculate median
        if n % 2 == 1:
            median = sorted_votes[n // 2]
        else:
            median = (sorted_votes[n // 2 - 1] + sorted_votes[n // 2]) // 2

        # Round to nearest Fibonacci
        return self._round_to_fibonacci(median)

    def _round_to_fibonacci(self, value: int) -> int:
        """Round a value to the nearest Fibonacci number."""
        if value <= self.FIBONACCI_SEQUENCE[0]:
            return self.FIBONACCI_SEQUENCE[0]
        if value >= self.FIBONACCI_SEQUENCE[-1]:
            return self.FIBONACCI_SEQUENCE[-1]

        # Find closest Fibonacci
        closest = self.FIBONACCI_SEQUENCE[0]
        min_diff = abs(value - closest)
        
        for fib in self.FIBONACCI_SEQUENCE:
            diff = abs(value - fib)
            if diff < min_diff:
                min_diff = diff
                closest = fib

        return closest

    def complete_session(self, session_id: str) -> EstimationSession:
        """
        Complete a planning poker session and calculate final value.
        Saves the consensus to the database.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        votes = [v.value for v in session.votes.values() if v.value is not None]
        if not votes:
            raise ValueError("No votes to calculate consensus")

        final_value = self.calculate_consensus(votes)
        session.final_value = final_value
        session.status = VotingStatus.COMPLETED
        session.completed_at = datetime.now()

        # Save to database based on item type
        self._save_consensus(session)

        return session

    def _save_consensus(self, session: EstimationSession) -> None:
        """Save the consensus value to the appropriate database table."""
        if session.item_type == 'test_duration':
            # Update test duration in TestItem or related table
            pass  # Implement based on your schema
        elif session.item_type == 'complexity_weight':
            # Update complexity weight
            pass
        elif session.item_type == 'mobility_weight':
            # Update mobility weight
            pass

    def cancel_session(self, session_id: str) -> EstimationSession:
        """Cancel an in-progress session."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.status = VotingStatus.CANCELLED
        return session

    def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for a session."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        votes = [v.value for v in session.votes.values() if v.value is not None]
        
        if not votes:
            return {
                'session_id': session_id,
                'status': session.status,
                'participants': len(session.votes),
                'votes_cast': 0,
            }

        return {
            'session_id': session_id,
            'status': session.status,
            'participants': len(session.votes),
            'votes_cast': len(votes),
            'min_vote': min(votes),
            'max_vote': max(votes),
            'average': sum(votes) / len(votes),
            'consensus': self.calculate_consensus(votes) if len(votes) >= 2 else votes[0] if votes else None,
            'fibonacci_sequence': self.FIBONACCI_SEQUENCE,
        }

    def create_test_duration_session(self, test_code: str, test_name: str) -> EstimationSession:
        """Convenience method to create a session for estimating test duration."""
        return self.create_session(
            item_type='test_duration',
            item_id=test_code,
            item_name=test_name,
            description=f"Estimate duration (in minutes) for test: {test_name}"
        )

    def create_complexity_session(self, category: str, description: str = "") -> EstimationSession:
        """Convenience method to create a session for estimating category complexity."""
        return self.create_session(
            item_type='complexity_weight',
            item_id=category,
            item_name=category,
            description=description or f"Estimate complexity weight for category: {category}"
        )
