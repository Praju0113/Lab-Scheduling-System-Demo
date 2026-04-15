"""
Operations Research Scheduler using Google OR-Tools CP-SAT solver.
Optimizes patient flow through labs using mathematical constraints.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, date, timezone
from sqlalchemy.exc import IntegrityError

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ExplicitDependencies,
    Lab,
    QueueEntry,
    QueueEntryType,
    QueueStatus,
    Specialist,
    TestItem,
    TestStatus,
    Visit,
)


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
        return self.db.scalars(
            select(Lab).where(Lab.is_active == True)
        ).all()

    def get_pending_tests(self) -> list[TestItem]:
        """Get all tests that need scheduling (SCHEDULED status), excluding blocked tests.
        
        FIX 1.1: Uses FOR UPDATE lock to serialize concurrent optimization requests
        and prevent race conditions when creating queue entries.
        
        CRITICAL FIX: Exclude tests that already have:
        - An assigned lab (awaiting queue entry)
        - A queue entry (NEXT, CURRENT, or PENDING)
        
        This prevents re-fetching and re-assigning the same tests multiple times,
        which was causing only first 1-2 patients to get scheduled.
        """
        # Subquery: Find test IDs that already have queue entries
        has_queue_entry = select(QueueEntry.test_item_id)
        
        return self.db.scalars(
            select(TestItem)
            .where(
                TestItem.status == TestStatus.SCHEDULED,
                TestItem.queue_status == QueueStatus.WAITING,
                TestItem.is_blocked == False,
                TestItem.assigned_lab_id.is_(None),  # Not yet assigned to any lab
                ~TestItem.id.in_(has_queue_entry)  # No queue entry (NEXT, CURRENT, PENDING)
            )
            .with_for_update()  # Lock these rows to prevent concurrent modifications
        ).all()

    def get_test_dependencies(self, test_code: str) -> list[str]:
        """Get list of test codes that must complete before this test."""
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
                select(TestItem)
                .where(
                    TestItem.visit_id == test_item.visit_id,
                    TestItem.test_code == dep.depends_on_test_code,
                    TestItem.status == TestStatus.COMPLETED
                )
            )
            if not completed:
                return False
        return True

    def detect_unschedulable_tests(self, tests: list[TestItem], labs: list[Lab]) -> set[int]:
        """FIX 2.3: Detect tests that cannot be scheduled due to:
        - No compatible labs
        - Unsatisfiable dependencies
        - Constraint conflicts
        
        Returns set of unschedulable test IDs.
        """
        unschedulable = set()
        
        for test in tests:
            # Check 1: Can any lab accept this test?
            visit = self.db.get(Visit, test.visit_id)
            compatible_labs = [
                lab for lab in labs 
                if self.check_lab_compatibility(test, lab, visit)
            ]
            if not compatible_labs:
                unschedulable.add(test.id)
                continue
            
            # Check 2: Are dependencies satisfiable?
            deps = self.get_test_dependencies(test.test_code)
            for dep_code in deps:
                # Find if any test with dep_code exists for this patient
                dep_test = self.db.scalar(
                    select(TestItem)
                    .where(
                        TestItem.visit_id == test.visit_id,
                        TestItem.test_code == dep_code
                    )
                )
                if dep_test:
                    # Dependency exists, check if IT can be scheduled
                    if dep_test.id in unschedulable:
                        unschedulable.add(test.id)
                        break
                    # Check if dep_test can reach any compatible lab
                    dep_compatible_labs = [
                        lab for lab in labs 
                        if self.check_lab_compatibility(dep_test, lab, self.db.get(Visit, dep_test.visit_id))
                    ]
                    if not dep_compatible_labs:
                        unschedulable.add(test.id)
                        break
        
        return unschedulable

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
        # Use timezone-aware calculation to avoid UTC/local mismatch
        wait_minutes = (datetime.now().astimezone() - visit.arrival_time).total_seconds() / 60
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

        # Check if lab has specific supported_test_codes
        # If so, test_code must be in that list
        if lab.supported_test_codes:
            if test_item.test_code not in lab.supported_test_codes:
                return False
        else:
            # Otherwise, check if test category matches lab category
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
        
        FIX 1.3: Re-validates assignments after solving to catch patient movements
        during the optimization window.
        """
        model = cp_model.CpModel()
        
        # Get data
        labs = self.get_active_labs()
        all_tests = self.get_pending_tests()

        if not all_tests or not labs:
            return {}

        # FIX 2.3: Detect and exclude unschedulable tests
        unschedulable = self.detect_unschedulable_tests(all_tests, labs)
        tests = [t for t in all_tests if t.id not in unschedulable]
        
        if not tests:
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
        # FIX 2.2: Use timezone-aware datetimes for accurate comparisons
        now = datetime.now(timezone.utc).astimezone()  # Local timezone
        local_date = now.replace(hour=0, minute=0, second=0, microsecond=0).date()
        
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            for lab in labs:
                specialist = self.db.get(Specialist, lab.specialist_id)
                if specialist:
                    # Combine date with shift times, using same timezone as 'now'
                    shift_end_dt = datetime.combine(local_date, specialist.shift_end, tzinfo=now.tzinfo)
                    lab_close_dt = datetime.combine(local_date, lab.closing_time, tzinfo=now.tzinfo)
                    # Latest possible end time for the test
                    latest_end = min(shift_end_dt, lab_close_dt)
                    # Estimated start time (now or arrival time, whichever is later)
                    est_start = max(now, visit.arrival_time)
                    # Test must fit: start + duration + cleanup <= end time
                    total_duration = test.duration_minutes + lab.cleanup_duration_minutes
                    est_end = est_start + timedelta(minutes=total_duration)
                    if est_end > latest_end:
                        # Test doesn't fit in time window
                        model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 5: One Place at a Time Rule
        # A patient cannot be at multiple labs simultaneously
        # If patient is currently at a lab, they can only be assigned to that same lab
        current_lab_by_patient = {}
        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            if visit.id not in current_lab_by_patient:
                # Check if patient is currently at a specific lab (IN_PROGRESS or CURRENT)
                current_test = self.db.scalar(
                    select(TestItem)
                    .where(
                        TestItem.visit_id == visit.id,
                        TestItem.status == TestStatus.IN_PROGRESS,
                        TestItem.queue_status == QueueStatus.CURRENT,
                        TestItem.assigned_lab_id.isnot(None)
                    )
                )
                if current_test:
                    current_lab_by_patient[visit.id] = current_test.assigned_lab_id
                else:
                    current_lab_by_patient[visit.id] = None

        for test in tests:
            visit = self.db.get(Visit, test.visit_id)
            patient_current_lab = current_lab_by_patient.get(visit.id)
            if patient_current_lab is not None:
                # Patient is currently at a lab, can only assign to that same lab
                for lab in labs:
                    if lab.id != patient_current_lab:
                        model.Add(x[(test.id, lab.id)] == 0)

        # Constraint 6: Lab capacity (one test at a time per lab)
        # FIX: Account for tests already assigned to this lab waiting or in-progress
        # This prevents double-assignment and ensures proper queuing
        for lab in labs:
            # Count tests already assigned to this lab that haven't completed
            existing_assigned_tests = self.db.scalars(
                select(TestItem).where(
                    TestItem.assigned_lab_id == lab.id,
                    TestItem.status.in_([TestStatus.SCHEDULED, TestStatus.IN_PROGRESS]),
                    TestItem.is_blocked == False
                )
            ).all()
            existing_assigned = len(existing_assigned_tests)
            
            new_assignments = sum(x[(test.id, lab.id)] for test in tests)
            
            # Lab can only accept new assignments if it's currently free
            # Capacity = 1, so if existing_assigned=1, new_assignments must be 0
            model.Add(new_assignments <= (1 - existing_assigned))

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

        assignments = {}
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for test in tests:
                for lab in labs:
                    if solver.Value(x[(test.id, lab.id)]) == 1:
                        assignments[test.id] = lab.id
                        break

        # FIX 1.3: Re-validate assignments after solving
        # Check if patient moved to different lab during optimization window
        validated_assignments = {}
        for test_id, assigned_lab_id in assignments.items():
            test_item = self.db.get(TestItem, test_id)
            if not test_item:
                continue
            
            visit = self.db.get(Visit, test_item.visit_id)
            
            # Check: Is patient currently at a different lab?
            current_test = self.db.scalar(
                select(TestItem)
                .where(
                    TestItem.visit_id == visit.id,
                    TestItem.status == TestStatus.IN_PROGRESS,
                    TestItem.queue_status == QueueStatus.CURRENT,
                    TestItem.assigned_lab_id.isnot(None)
                )
            )
            
            if current_test and current_test.assigned_lab_id != assigned_lab_id:
                # Patient moved! Skip this assignment
                continue
            
            validated_assignments[test_id] = assigned_lab_id

        return validated_assignments

    def apply_schedule(self, assignments: dict) -> None:
        """
        Apply the optimized schedule to the database.
        Updates test assignments and creates queue entries.
        Ensures each patient has only ONE NEXT test at a time.
        Other tests remain assigned but unqueued until their predecessor completes.
        
        FIX 1.4: Validates test status before assignment to prevent corrupting completed tests.
        FIX 1.2: Uses try-catch for atomic QueueEntry creation.
        """
        
        # First pass: assign labs to all tests with status validation
        # FIX 1.4: Only update if test is still SCHEDULED (not completed)
        for test_id, lab_id in assignments.items():
            test_item = self.db.get(TestItem, test_id)
            if test_item and test_item.status == TestStatus.SCHEDULED:
                test_item.assigned_lab_id = lab_id
                test_item.queue_status = QueueStatus.WAITING
        
        # Flush to persist assignments before creating queue entries
        self.db.flush()
        
        # Second pass: create NEXT queue entries (only one per patient)
        # Track which patients already have a NEXT entry
        patients_with_next = set()
        
        # Find all existing NEXT entries
        existing_next_entries = self.db.scalars(
            select(QueueEntry).where(QueueEntry.queue_type == QueueEntryType.NEXT)
        ).all()
        for entry in existing_next_entries:
            patients_with_next.add(entry.visit_id)
        
        # Create NEXT entries only for tests whose patients don't have one yet
        # Process in order of assignment (which respects dependencies)
        assigned_tests = [self.db.get(TestItem, tid) for tid in assignments.keys()]
        assigned_tests.sort(key=lambda t: t.id)  # Stable ordering
        
        for test_item in assigned_tests:
            if test_item and test_item.visit_id not in patients_with_next:
                # This patient doesn't have a NEXT test yet, check if this one exists
                existing = self.db.scalar(
                    select(QueueEntry).where(QueueEntry.test_item_id == test_item.id)
                )
                if not existing:
                    # Only add NEXT entry if dependencies are satisfied
                    if self.check_dependency_satisfied(test_item):
                        # FIX 1.2: Try-catch for atomic check-and-create
                        # If another process created this entry, we gracefully skip
                        try:
                            queue_entry = QueueEntry(
                                lab_id=test_item.assigned_lab_id,
                                visit_id=test_item.visit_id,
                                test_item_id=test_item.id,
                                queue_type=QueueEntryType.NEXT,
                                position=None
                            )
                            self.db.add(queue_entry)
                            self.db.flush()  # Flush to detect constraint violations early
                            patients_with_next.add(test_item.visit_id)
                        except IntegrityError as e:
                            # Another process already created this QueueEntry - that's OK
                            self.db.rollback()
                            patients_with_next.add(test_item.visit_id)

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
