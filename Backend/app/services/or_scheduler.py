"""
Operations Research Scheduler using Google OR-Tools CP-SAT solver.
Optimizes patient flow through labs using mathematical constraints.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lab, Specialist, TestItem, Visit

if TYPE_CHECKING:
    pass


class TestConstraints:
    """Mathematical constraints for the OR solver."""

    # Priority weights for objective function
    PRIORITY_WEIGHTS = {
        'EMERGENCY': 1000,
        'FASTING': 500,
        'ELDERLY': 300,  # Age >= 50
        'NORMAL': 100,
    }

    # Test category weights
    CATEGORY_WEIGHTS = {
        'Strict Fasting Blood': 400,
        'Dual-Phase (Done Twice)': 300,
        'Multi-Sample (GTT)': 300,
        'default': 100,
    }

    # Patient mobility weights (for movement penalty)
    MOBILITY_WEIGHTS = {
        'high': 50,   # Young, mobile patients
        'medium': 20, # Normal mobility
        'low': 5,     # Elderly or mobility issues
    }


class ORScheduler:
    """
    OR-Tools based scheduler that optimizes lab assignments.
    Replaces rule-based heuristics with mathematical optimization.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.constraints = TestConstraints()

    def get_active_labs(self) -> list[Lab]:
        """Get all active labs with their specialists."""
        from app.models import Lab
        return self.db.scalars(
            select(Lab).where(Lab.is_active == True)
        ).all()

    def get_pending_tests(self) -> list[TestItem]:
        """Get all tests that need scheduling (SCHEDULED status)."""
        from app.models import TestItem, TestStatus, QueueStatus
        return self.db.scalars(
            select(TestItem)
            .where(
                TestItem.status == TestStatus.SCHEDULED,
                TestItem.queue_status == QueueStatus.NOT_QUEUED
            )
        ).all()

    def get_test_dependencies(self, test_code: str) -> list[str]:
        """Get list of test codes that must complete before this test."""
        from app.models import ExplicitDependencies
        deps = self.db.scalars(
            select(ExplicitDependencies.depends_on_test_code)
            .where(
                ExplicitDependencies.test_code == test_code,
                ExplicitDependencies.dependency_type == 'must_complete_before',
                ExplicitDependencies.is_strict == True
            )
        ).all()
        return list(deps)

    def check_dependency_satisfied(self, test_item: TestItem) -> bool:
        """Check if all dependencies for a test are completed."""
        from app.models import ExplicitDependencies, TestItem as TestItemModel, TestStatus
        
        # Get dependencies from ExplicitDependencies table
        deps = self.db.scalars(
            select(ExplicitDependencies)
            .where(
                ExplicitDependencies.test_code == test_item.test_code,
                ExplicitDependencies.is_strict == True
            )
        ).all()
        
        if not deps:
            return True

        for dep in deps:
            # Check if the dependent test is completed
            completed = self.db.scalar(
                select(TestItemModel)
                .where(
                    TestItemModel.visit_id == test_item.visit_id,
                    TestItemModel.test_code == dep.depends_on_test_code,
                    TestItemModel.status == TestStatus.COMPLETED
                )
            )
            if not completed:
                return False
        return True

    def calculate_priority_score(self, visit: Visit, test_item: TestItem) -> int:
        """
        Calculate priority score for objective function.
        Higher score = higher priority for scheduling.
        """
        score = 0
        
        # Base priority weight
        priority_weight = self.constraints.PRIORITY_WEIGHTS.get(
            visit.priority_type, 
            self.constraints.PRIORITY_WEIGHTS['NORMAL']
        )
        score += priority_weight

        # Age-based mobility consideration
        if visit.patient_age >= 50:
            score += self.constraints.PRIORITY_WEIGHTS['ELDERLY']

        # Category weight
        category_weight = self.constraints.CATEGORY_WEIGHTS.get(
            test_item.category,
            self.constraints.CATEGORY_WEIGHTS['default']
        )
        score += category_weight

        # Wait time bonus (longer wait = higher priority)
        arrival_naive = visit.arrival_time.replace(tzinfo=None)
        wait_minutes = (datetime.now() - arrival_naive).total_seconds() / 60
        score += int(wait_minutes * 10)  # 10 points per minute waited

        return score

    def check_lab_compatibility(
        self, 
        test_item: TestItem, 
        lab: Lab, 
        visit: Visit
    ) -> bool:
        """
        Check if a test can be performed at a lab.
        Returns True if compatible (acts as binary multiplier in OR).
        """
        from app.models import Specialist
        
        # Check lab is active
        if not lab.is_active:
            return False

        # Check specialist is active
        specialist = self.db.get(Specialist, lab.specialist_id)
        if specialist and not specialist.is_active:
            return False

        # Check gender requirements (e.g., Pap Smear needs female specialist)
        if test_item.category == 'Pap Smear Test':
            if specialist and specialist.gender != 'Female':
                return False

        # Check if test category matches lab category
        # Using lab_type mapping from database
        if lab.category != test_item.category:
            return False

        return True

    def calculate_movement_penalty(
        self, 
        visit: Visit, 
        current_lab: Lab | None, 
        proposed_lab: Lab
    ) -> int:
        """
        Calculate penalty for moving patient between labs.
        Lower penalty = better (OR solver minimizes this).
        """
        if current_lab is None:
            return 0  # First test, no movement

        if current_lab.id == proposed_lab.id:
            return 0  # Same lab, no movement

        # Floor change penalty
        floor_changes = 0
        if current_lab.floor != proposed_lab.floor:
            floor_changes = 1

        # Age-based mobility weight
        if visit.patient_age >= 50:
            mobility_weight = self.constraints.MOBILITY_WEIGHTS['low']
        elif visit.patient_age >= 30:
            mobility_weight = self.constraints.MOBILITY_WEIGHTS['medium']
        else:
            mobility_weight = self.constraints.MOBILITY_WEIGHTS['high']

        return floor_changes * mobility_weight

    def optimize_schedule(self) -> dict:
        """
        Main OR optimization function.
        Returns optimal assignments as {test_item_id: lab_id}.
        """
        model = cp_model.CpModel()
        
        # Get data
        labs = self.get_active_labs()
        tests = self.get_pending_tests()

        if not tests or not labs:
            return {}

        # Create decision variables: x[test_id][lab_id] = 1 if test assigned to lab
        x = {}
        for test in tests:
            for lab in labs:
                x[(test.id, lab.id)] = model.NewBoolVar(f'x_{test.id}_{lab.id}')

        # Constraint 1: Each test assigned to exactly one lab
        for test in tests:
            model.Add(sum(x[(test.id, lab.id)] for lab in labs) == 1)

        # Constraint 2: Lab compatibility (binary constraint)
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            for lab in labs:
                if not self.check_lab_compatibility(test, lab, visit):
                    model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 3: Dependency satisfaction
        for test in tests:
            if not self.check_dependency_satisfied(test):
                # Cannot schedule if dependencies not met
                for lab in labs:
                    model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 4: Time Window Fitting (shift end, lab closing, cleanup)
        # A test must fit within specialist shift and lab hours
        now = datetime.now()
        from datetime import date
        today = date.today()
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            for lab in labs:
                specialist = self.db.get(Specialist, lab.specialist_id)
                if specialist:
                    # Check if test fits within shift end time
                    # Combine date with time for comparison
                    shift_end_dt = datetime.combine(today, specialist.shift_end)
                    lab_close_dt = datetime.combine(today, lab.closing_time)
                    # Latest possible end time for the test
                    latest_end = min(shift_end_dt, lab_close_dt)
                    # Estimated start time (now or arrival time)
                    est_start = max(now, visit.arrival_time.replace(tzinfo=None))
                    # Test must fit: start + duration + cleanup <= end time
                    total_duration = test.duration_minutes + lab.cleanup_duration_minutes
                    est_end = est_start + timedelta(minutes=total_duration)
                    if est_end.time() > latest_end.time():
                        # Test doesn't fit in time window
                        model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 5: One Place at a Time Rule
        # A patient cannot have multiple tests IN_PROGRESS or WAITING across different labs
        # Get active tests for each patient (already in progress or waiting)
        from app.models import TestStatus, QueueStatus
        active_tests_by_patient = {}
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            if visit.id not in active_tests_by_patient:
                # Check for existing active tests for this patient
                active_existing = self.db.scalars(
                    select(TestItem)
                    .where(
                        TestItem.visit_id == visit.id,
                        TestItem.status.in_([TestStatus.IN_PROGRESS]),
                        TestItem.queue_status.in_([QueueStatus.CURRENT, QueueStatus.WAITING])
                    )
                ).all()
                active_tests_by_patient[visit.id] = len(active_existing)

        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            if active_tests_by_patient.get(visit.id, 0) > 0:
                # Patient already has active tests, can't assign new ones
                for lab in labs:
                    model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 6: Lab capacity (one test at a time per lab)
        for lab in labs:
            model.Add(sum(x[(test.id, lab.id)] for test in tests) <= 1)

        # Objective function: Maximize priority scores, minimize movement
        objective_terms = []
        
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            priority_score = self.calculate_priority_score(visit, test)
            
            # Find current lab assignment (if any)
            current_lab = None
            if test.assigned_lab_id:
                current_lab = self.db.get(Lab, test.assigned_lab_id)

            for lab in labs:
                # Priority bonus for assigning
                objective_terms.append(priority_score * x[(test.id, lab.id)])
                
                # Movement penalty (subtracted)
                movement_penalty = self.calculate_movement_penalty(visit, current_lab, lab)
                objective_terms.append(-movement_penalty * x[(test.id, lab.id)])

        model.Maximize(sum(objective_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0  # Max 5 seconds
        solver.parameters.num_search_workers = 4
        
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            assignments = {}
            for test in tests:
                for lab in labs:
                    if solver.Value(x[(test.id, lab.id)]) == 1:
                        assignments[test.id] = lab.id
                        break
            return assignments

        return {}  # No feasible solution

    def apply_schedule(self, assignments: dict) -> None:
        """
        Apply the optimized schedule to the database.
        Updates test assignments and creates queue entries.
        """
        from app.models import TestItem, QueueEntry, QueueEntryType, QueueStatus
        
        for test_id, lab_id in assignments.items():
            test_item = self.db.get(TestItem, test_id)
            if test_item:
                # Update assignment
                test_item.assigned_lab_id = lab_id
                test_item.queue_status = QueueStatus.WAITING
                
                # Create queue entry
                existing = self.db.scalar(
                    select(QueueEntry).where(QueueEntry.test_item_id == test_id)
                )
                if not existing:
                    queue_entry = QueueEntry(
                        lab_id=lab_id,
                        visit_id=test_item.visit_id,
                        test_item_id=test_id,
                        queue_type=QueueEntryType.PENDING,
                        position=None
                    )
                    self.db.add(queue_entry)

        self.db.commit()

    def run_optimization(self) -> dict:
        """Run full optimization cycle and return results."""
        assignments = self.optimize_schedule()
        if assignments:
            self.apply_schedule(assignments)
        return {
            'assignments_made': len(assignments),
            'assignments': assignments,
            'timestamp': datetime.now().isoformat()
        }
