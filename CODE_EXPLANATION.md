# Code Explanation - Personal Guide

This document explains how the Lab Scheduling System code works, written for your understanding.

---

## The Big Picture

This system has 3 main parts:
1. **Frontend** - React app that users see (receptionist, doctors, admin dashboards)
2. **Backend** - FastAPI server that handles logic and database
3. **Database** - PostgreSQL storing patients, tests, labs, queue state

The magic happens in the **OR Scheduler** - it uses Google's OR-Tools to mathematically decide which patient goes to which lab.

---

## How Data Flows

### When a New Patient Arrives:

1. **Frontend** → User fills form, clicks "Add Patient"
2. **Backend** (`POST /api/frontend/patients`) → Creates records in database
3. **OR Scheduler** → Runs optimization algorithm
4. **Backend** → Assigns patient to optimal lab (could be any lab: 1, 2, 3, etc.)
5. **WebSocket** → Notifies all connected dashboards
6. **Frontend** → Updates display showing patient assigned to their assigned lab

---

## Key Files Explained

### 1. `Backend/app/main.py` - The API Server

This is where HTTP endpoints live. Think of it as the reception desk - it takes requests and routes them to the right service.

**Key sections:**

```python
@app.post('/api/frontend/patients')
async def create_frontend_patient(payload: FrontendPatientPayload, db: Session = Depends(get_db)):
    # 1. Validate input (needs at least one test)
    if not payload.test_names:
        raise HTTPException(status_code=400, detail='At least one test is required')
    
    # 2. Create visit record
    visit = Visit(...)
    db.add(visit)
    db.flush()  # Get the ID without committing
    
    # 3. Create test items
    for test_name in payload.test_names:
        db.add(TestItem(
            visit_id=visit.id,
            queue_status=QueueStatus.NOT_QUEUED,  # <-- IMPORTANT!
            ...
        ))
    
    # 4. Run OR optimization (the magic!)
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    
    # 5. Notify all dashboards via WebSocket
    emit_nowait('visit.updated', response)
```

**Why `WAITING` State for Scheduling?**
- `WAITING`: Patient ready for queueing & scheduling → **OR solver picks these for assignment**
- `CURRENT`: Being tested right now → **OR solver ignores (in progress)**
- `PENDING`: Specialist locked patient → **OR solver ignores (specialist decision pending)**
- `BLOCKED`: Receptionist excluded → **OR solver ignores (completely excluded)**

When a test is in WAITING state with `assigned_lab_id=null`, the OR solver considers it. After assign­ment, it stays WAITING but `assigned_lab_id` is filled with the lab number. Test is now queued to that lab.

--- 

### 2. `Backend/app/services/or_scheduler.py` - The Brain

This is the mathematical optimizer. It decides where patients go.

**How it works:**

```python
def run_optimization(self):
    # 1. Get all unassigned tests
    tests = self.get_pending_tests()  # Only NOT_QUEUED tests
    labs = self.get_active_labs()
    
    # 2. Create the math problem
    model = cp_model.CpModel()
    
    # Decision variable: x[test_id][lab_id] = 1 if assigned, 0 if not
    x = {}
    for test in tests:
        for lab in labs:
            x[(test.id, lab.id)] = model.NewBoolVar(f'x_{test.id}_{lab.id}')
    
    # 3. Add constraints (rules that MUST be followed)
    
    # Rule 1: Each test goes to exactly one lab
    for test in tests:
        model.Add(sum(x[(test.id, lab.id)] for lab in labs) == 1)
    
    # Rule 2: Only compatible labs (ECG machine can't do Ultrasound)
    for test in tests:
        for lab in labs:
            if not self.check_lab_compatibility(test, lab, visit):
                model.Add(x[(test.id, lab.id)] == 0)  # Force to 0
    
    # Rule 3: Dependencies must be satisfied (ECG before TMT)
    for test in tests:
        if not self.check_dependency_satisfied(test):
            for lab in labs:
                model.Add(x[(test.id, lab.id)] == 0)
    
    # 4. Define objective (what we want to maximize)
    objective_terms = []
    for test in tests:
        priority_score = self.calculate_priority_score(visit, test)
        movement_penalty = self.calculate_movement_penalty(visit, current_lab, lab)
        
        # Maximize priority, minimize movement
        objective_terms.append(priority_score * x[(test.id, lab.id)])
        objective_terms.append(-movement_penalty * x[(test.id, lab.id)])
    
    model.Maximize(sum(objective_terms))
    
    # 5. Solve!
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # 6. Apply results to database
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for test in tests:
            for lab in labs:
                if solver.Value(x[(test.id, lab.id)]) == 1:
                    test.assigned_lab_id = lab.id
                    test.queue_status = QueueStatus.WAITING
```

**Priority Scoring:**
```python
def calculate_priority_score(self, visit, test):
    score = 0
    
    # Emergency patients get 1000 points
    if visit.priority_type == 'EMERGENCY':
        score += 1000
    
    # Fasting patients get 500 points (they're hungry!)
    if test.condition_category == 'Strict Fasting Blood':
        score += 500
    
    # Elderly patients (age >= 50) get 300 points
    if visit.patient_age >= 50:
        score += 300
    
    # Longer wait time = higher priority (10 points per minute)
    wait_minutes = (datetime.now() - visit.arrival_time).total_seconds() / 60
    score += int(wait_minutes * 10)
    
    return score
```

**Movement Penalty:**
```python
def calculate_movement_penalty(self, visit, current_lab, proposed_lab):
    if current_lab is None:
        return 0  # First test, no movement
    
    if current_lab.id == proposed_lab.id:
        return 0  # Same lab, no movement
    
    # Floor change = bad for elderly
    if current_lab.floor != proposed_lab.floor:
        if visit.patient_age >= 50:
            return 100  # High penalty for elderly
        else:
            return 20   # Low penalty for young
    
    return 0
```

---

### 3. `Backend/app/models.py` - Database Structure

This defines what tables exist and how they relate.

**The main tables:**

**Visit** = A patient arriving at the hospital
```python
class Visit:
    id = Column(Integer, primary_key=True)
    public_id = Column(String)  # Human-readable like "A0114001"
    patient_name = Column(String)
    patient_age = Column(Integer)
    patient_gender = Column(String)  # Male/Female/Other
    priority_type = Column(String)   # EMERGENCY/FASTING/ELDERLY/ROUTINE
    arrival_time = Column(DateTime)
    tests = relationship("TestItem")  # One visit has many tests
```

**TestItem** = A single test for a patient
```python
class TestItem:
    id = Column(Integer, primary_key=True)
    visit_id = Column(ForeignKey('visit.id'))  # Which visit
    test_code = Column(String)   # "ELECTROCARDIOGRAM_ECG"
    test_name = Column(String)   # "ECG"
    category = Column(String)    # "ECG" (for matching with labs)
    duration_minutes = Column(Integer)
    
    # Status tracking
    status = Column(Enum(TestStatus))      # SCHEDULED/IN_PROGRESS/COMPLETED
    queue_status = Column(Enum(QueueStatus))  # NOT_QUEUED/WAITING/CURRENT/PENDING/DONE
    
    assigned_lab_id = Column(ForeignKey('lab.id'))  # Which lab (NULL if not assigned)
    sequence_order = Column(Integer)  # Order in which to do tests
```

**Lab** = A room where tests happen
```python
class Lab:
    id = Column(Integer, primary_key=True)
    lab_code = Column(String)      # "ECG-01"
    category = Column(String)      # "ECG" (what tests can be done here)
    floor = Column(String)         # "1", "2", "3"
    specialist_id = Column(ForeignKey('specialist.id'))
    opening_time = Column(Time)
    closing_time = Column(Time)
    cleanup_duration_minutes = Column(Integer)  # Time between patients
```

**ExplicitDependencies** = Test prerequisites
```python
class ExplicitDependencies:
    test_code = Column(String)           # "TMT" (the test that needs something)
    depends_on_test_code = Column(String)  # "ECG" (the prerequisite)
    is_strict = Column(Boolean)          # True = must complete, False = recommended
```

Example entries:
- TMT depends on ECG (strict = True) → Can't do TMT until ECG done
- Ultrasound depends on Urine (strict = False) → Recommended order but not required

---

### 4. `Backend/app/services/queue.py` - Queue Management

This handles the real-time state of who's being seen where.

**Key concept: QueueEntry tracks state**

When a patient is assigned to a lab:
```python
# OR Scheduler creates this:
QueueEntry(
    lab_id=3,
    visit_id=5,
    test_item_id=12,
    queue_type=QueueEntryType.NEXT  # Waiting to be called
)
```

When specialist clicks "Accept":
```python
def accept_current(self, lab_id):
    # Find the NEXT entry
    next_entry = db.scalar(
        select(QueueEntry)
        .where(lab_id=lab_id, queue_type=NEXT)
    )
    
    # Change to CURRENT (patient is now being seen)
    next_entry.queue_type = QueueEntryType.CURRENT
    
    # Update test status
    test.status = TestStatus.IN_PROGRESS
    test.queue_status = QueueStatus.CURRENT
```

When specialist clicks "Complete":
```python
def complete_current(self, lab_id):
    # Find CURRENT entry
    current = db.scalar(
        select(QueueEntry)
        .where(lab_id=lab_id, queue_type=CURRENT)
    )
    
    # Mark test done
    test.status = TestStatus.COMPLETED
    test.queue_status = QueueStatus.DONE
    
    # Delete queue entry (they're done with this lab)
    db.delete(current)
    
    # Run OR optimization (maybe unblock dependent tests!)
    or_scheduler.run_optimization()
```

---

### 5. `Backend/app/services/bootstrap.py` - Frontend Data Transformation

This service converts internal database records into the format the frontend expects.

**Key function: `frontend_visit()`**
```python
def frontend_visit(visit: Visit) -> dict:
    # Determine frontend status from backend states
    if all(test.status == TestStatus.COMPLETED for test in visit.tests):
        status = 'Completed'
    elif any(test.is_blocked for test in visit.tests):
        status = 'Blocked'  # NEW: Receptionist blocked
    elif any(test.queue_status == QueueStatus.PENDING for test in visit.tests):
        status = 'Pending'  # Lab specialist locked patient to pending queue
    else:
        status = 'Waiting'   # Available for queueing/scheduling
    
    return {
        'id': visit.public_id,
        'status': status,
        'patient_name': visit.patient_name,
        ...
    }
```

**Status Meanings:**
- **Waiting**: Patient ready for queueing/scheduling. Can be assigned to labs
- **Pending**: Lab specialist clicked "pending" - locked to that lab, not for scheduling
- **Blocked**: Receptionist blocked - NOT locked to any lab, not for scheduling
- **Completed**: All tests done

---

### 6. `Backend/app/models.py` - Updated: is_blocked Field

Added new field to TestItem to distinguish between "Lab-Pending" and "Receptionist-Blocked":

```python
class TestItem:
    id = Column(Integer, primary_key=True)
    visit_id = Column(ForeignKey('visit.id'))
    test_code = Column(String)
    test_name = Column(String)
    category = Column(String)
    duration_minutes = Column(Integer)
    
    # Status tracking
    status = Column(Enum(TestStatus))      # SCHEDULED/IN_PROGRESS/COMPLETED
    queue_status = Column(Enum(QueueStatus))  # NOT_QUEUED/WAITING/CURRENT/PENDING/DONE
    
    # NEW: Receptionist blocking
    is_blocked = Column(Boolean, default=False, index=True)
    
    assigned_lab_id = Column(ForeignKey('lab.id'))
    sequence_order = Column(Integer)
```

---

### 7. Patient State Management - The Full Picture

**State Transitions Explained:**

The `queue_status` field goes through this lifecycle:

```
WAITING (New test, unassigned but ready for scheduling)
    ↓
    OR Scheduler picks it up and assigns to lab
    ↓
    Status stays WAITING (already assigned)
    ↓
    Specialist calls from queue (creates QueueEntry with NEXT)
    ↓
    Specialist clicks "Accept"
    ↓
CURRENT (Patient is NOW being tested)
    ↓
    Either:
    A) Specialist clicks "Complete" → DONE (test finished)
    B) Specialist clicks "Move to Pending" → PENDING (patient paused)
    C) From PENDING, specialist accepts → CURRENT (resume test)
```

**Key differences:**

- **WAITING** (with assigned_lab_id=null): Unassigned, eligible for OR optimization
- **WAITING** (with assigned_lab_id=5): Assigned to Lab 5, **Excluded from further OR optimization** (already has a lab)
- **PENDING**: Locked at specialist's queue. **Excluded from OR optimization** (waiting for specialist decision)
- **CURRENT**: Being tested right now
- **DONE**: Test finished

**BLOCKED state** (NEW):
- When receptionist clicks "Block": `is_blocked=true` is set, `queue_status` stays as is, but test is **completely excluded** from system
- **Prevents** the test from being considered by OR optimization
- When unblocked: `is_blocked=false` + `queue_status=WAITING` + `assigned_lab_id=null` → Back to start, can be assigned to any lab

**Three Patient States Explained:**

#### WAITING (Default/Ready)
```
Patient created with is_blocked=False, queue_status=NOT_QUEUED
│
├─ OR-Scheduler runs
│  └─ Assigns to lab, transitions to WAITING, creates QueueEntry
│
└─ Patient visible in "Waiting Candidates" for specialist
   └─ Must satisfy dependencies
   └─ Lab specialist can accept from waiting
```

#### PENDING (Lab Specialist Action)
```
Lab specialist clicks "Move Current to Pending" button
│
├─ queue_status = PENDING (stays locked to same lab)
├─ is_blocked = FALSE (not receptionist-blocked)
├─ assigned_lab_id = <current lab> (stays same lab)
│
└─ Patient locked to that lab
   └─ NOT reconsidered for other labs
   └─ Can be accepted from pending later
   └─ NOT eligible for OR optimization
```

#### BLOCKED (Receptionist Action)
```
Receptionist clicks "Block" button
│
├─ is_blocked = TRUE
├─ queue_status = whatever it was (NOT_QUEUED/WAITING/PENDING)
├─ assigned_lab_id = whatever it was
│
└─ Patient completely excluded from scheduling
   └─ NOT in any waiting candidates
   └─ NOT considered by OR optimizer
   └─ NOT eligible for anything until unblocked
   
Receptionist clicks "Unblock"
│
├─ is_blocked = FALSE
├─ queue_status = NOT_QUEUED (reset to start of scheduling cycle)
├─ assigned_lab_id = NULL (cleared, will be reassigned)
│
└─ Patient back in system as if newly arrived
   └─ OR Scheduler treats as fresh patient
   └─ Can be assigned to any compatible lab
```

**Key Difference:**
- **WAITING**: is_blocked=false, has a lab (assigned), ready to be called. **Will NOT be RE-assigned by OR.**
- **PENDING**: is_blocked=false, has a lab (locked), specialist decision pending. **Will NOT be considered by OR.**
- **BLOCKED**: is_blocked=true, no OR processing. **Completely excluded** until receptionist unblocks

---

### 8. Queue Population Logic - NEW in apply_schedule()

After OR optimization assigns tests, `apply_schedule()` automatically populates queues:

```python
def apply_schedule(self, assignments: dict) -> None:
    """
    Create QueueEntry records so tests enter the queue system.
    """
    for test_id, lab_id in assignments.items():
        test_item = self.db.get(TestItem, test_id)
        
        # 1. Assign to lab
        test_item.assigned_lab_id = lab_id
        
        # 2. Transition from NOT_QUEUED to WAITING
        test_item.queue_status = QueueStatus.WAITING
        
        # 3. Create queue entry (NEXT position)
        queue_entry = QueueEntry(
            lab_id=lab_id,
            visit_id=test_item.visit_id,
            test_item_id=test_id,
            queue_type=QueueEntryType.NEXT  # Waiting to be called
        )
        self.db.add(queue_entry)
    
    self.db.commit()
```

**Result**: Tests now visible in "waiting_candidates" for lab specialists

---

### 9. Receptionist Block/Unblock Endpoints - NEW

#### Block Endpoint
```python
@app.post('/api/visits/{visit_id}/block')
def receptionist_block_visit(visit_id: int, db: Session = Depends(get_db)):
    """Block all tests in a visit (not locked to any lab)."""
    tests = db.scalars(select(TestItem).where(TestItem.visit_id == visit_id)).all()
    
    for test in tests:
        if test.status not in {TestStatus.COMPLETED, TestStatus.IN_PROGRESS}:
            # Different from lab-pending!
            test.is_blocked = True  # Key difference
            test.caution_reason = 'Visit blocked by receptionist'
    
    db.commit()
    return {'message': 'Visit blocked', 'visit_id': visit_id}
```

#### Unblock Endpoint
```python
@app.post('/api/visits/{visit_id}/unblock')
def receptionist_unblock_visit(visit_id: int, db: Session = Depends(get_db)):
    """Unblock and re-consider for scheduling."""
    tests = db.scalars(select(TestItem).where(TestItem.visit_id == visit_id)).all()
    
    for test in tests:
        if test.is_blocked:
            test.is_blocked = False
            test.caution_reason = None
            
            # Reset to NOT_QUEUED so OR-Solver can reassign
            if test.queue_status != QueueStatus.CURRENT and test.status != TestStatus.IN_PROGRESS:
                test.queue_status = QueueStatus.NOT_QUEUED
    
    db.commit()
    
    # Re-run optimization!
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    
    return {'message': 'Visit unblocked', 'visit_id': visit_id}
```

**Key Behavior**:
- Block: `is_blocked=true` (patient excluded)
- Unblock: `is_blocked=false`, reset to `NOT_QUEUED` (available for new lab assignment!)

---

### 10. OR-Scheduler Triggers - EXPANDED

OR-Scheduler now runs automatically after:

1. **Patient Creation** ✅
   ```python
   @app.post('/api/frontend/patients')
   async def create_frontend_patient(...):
       db.add(visit)
       db.flush()
       # NEW: Trigger optimization
       or_scheduler = ORScheduler(db)
       or_scheduler.run_optimization()
   ```

2. **Patient Update** ✅ NEW
   ```python
   @app.patch('/api/frontend/patients/{visit_id}')
   async def update_frontend_patient(...):
       # After updating tests
       or_scheduler.run_optimization()
   ```

3. **Test Completion** ✅ NEW
   ```python
   @app.post('/api/queues/{lab_id}/complete-current')
   async def complete_current(...):
       snapshot = QueueService(...).complete_current(lab_id)
       # NEW: Re-optimize to schedule dependent tests
       or_scheduler = ORScheduler(db)
       or_scheduler.run_optimization()
   ```

4. **Receptionist Unblock** ✅ NEW
   ```python
   @app.post('/api/visits/{visit_id}/unblock')
   def receptionist_unblock_visit(...):
       # After unblocking
       or_scheduler.run_optimization()
   ```

5. **Lab Creation/Update** ✅ NEW
   ```python
   @app.post('/api/labs')
   async def create_lab(...):
       or_scheduler.run_optimization()
   ```

6. **Specialist Update** ✅ NEW
   ```python
   @app.patch('/api/specialists/{specialist_id}')
   async def update_specialist(...):
       or_scheduler.run_optimization()
   ```

7. **Explicit Scheduling API** ✅
   ```python
   @app.post('/api/scheduling/run')
   async def run_scheduling(...):
       or_scheduler.run_optimization()
   ```

---

### 11. Blocking Logic in OR-Scheduler

Tests with `is_blocked=true` are now excluded from scheduling:

```python
def get_pending_tests(self) -> list[TestItem]:
    """Get unassigned tests, excluding blocked ones."""
    return self.db.scalars(
        select(TestItem)
        .where(
            TestItem.status == TestStatus.SCHEDULED,
            TestItem.queue_status == QueueStatus.NOT_QUEUED,
            TestItem.is_blocked == False  # NEW: Ignore blocked tests
        )
    ).all()
```

**Result**: Blocked patients never get scheduled until unblocked

---

### 12. `Backend/app/services/planning_poker.py` - Estimation System

For when doctors want to collectively estimate how long a test takes.

**How Planning Poker works:**
1. Create a session for a test
2. Team members vote (1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
3. Reveal votes
4. Discuss outliers
5. Consensus = median rounded to Fibonacci

**Code flow:**
```python
# Create session
session = PlanningPokerSession(
    session_id="uuid-here",
    item_type="test",
    item_id="ELECTROCARDIOGRAM_ECG",
    item_name="ECG",
    status="voting"
)

# Cast vote (secret)
vote = PlanningPokerVote(
    session_id=session.id,
    user_id="dr_smith",
    value=8,  # 8 minutes
    is_revealed=False
)

# Reveal all votes
for vote in session.votes:
    vote.is_revealed = True

# Calculate consensus
values = [v.value for v in session.votes]  # [5, 8, 8, 13]
consensus = self._round_to_fibonacci(median(values))  # 8
```

---

## Understanding the Flow with an Example

**Scenario 1: Normal Patient Flow - John arrives for ECG and TMT**

### Step 1: Patient Registration
```
Frontend: POST /api/frontend/patients
{
  "patient_name": "John",
  "test_names": ["ECG", "TMT"]
}
```

Backend creates:
- Visit record (John, arrived at 10:00 AM)
- TestItem 1: ECG, status=SCHEDULED, queue_status=WAITING, is_blocked=false, assigned_lab_id=null
- TestItem 2: TMT, status=SCHEDULED, queue_status=WAITING, is_blocked=false, assigned_lab_id=null

### Step 2: OR Optimization Runs (NEW: Assigns Lab & Creates Queue Entries!)
```
OR Scheduler: "Let me check what needs scheduling..."

- ECG: WAITING status, no dependencies → Can assign
- TMT: WAITING status, depends on ECG → Not satisfied → Skip

OR Scheduler: "Assigning ECG to Lab 1 (ECG room on floor 1)"

Updates:
- TestItem 1: assigned_lab_id=1, queue_status=WAITING ← Now has a lab!
- Creates QueueEntry: lab_id=1, queue_type=NEXT
- TestItem 2: Still WAITING with assigned_lab_id=null (waiting for ECG)
```

### Step 3: Patient Appears on Dashboard
Receptionist sees: John assigned to Lab 1 (ECG) - Status: "Waiting"
John sees: Go to Room 1 for ECG

Lab Specialist sees in "Waiting Candidates": John for ECG

### Step 4: Specialist Accepts Patient
```
Specialist clicks "Accept"
→ POST /api/queues/{lab_id}/accept-current

Updates:
- QueueEntry: queue_type = NEXT → CURRENT
- TestItem 1: status=IN_PROGRESS, queue_status=CURRENT
```

### Step 5: Specialist Completes ECG
```
Specialist clicks "Complete"
→ POST /api/queues/{lab_id}/complete-current

Updates:
- TestItem 1: status=COMPLETED, queue_status=DONE
- QueueEntry: Deleted (patient done with Lab 1)

Triggers: OR Optimization runs again! (NEW)

OR Scheduler: "Now ECG is done, TMT dependency satisfied! Let me assign TMT..."

Updates:
- TestItem 2: assigned_lab_id=5, queue_status=WAITING ← Now has a lab!
- Creates QueueEntry: lab_id=5, queue_type=NEXT
```

### Step 6: Patient Goes to TMT Lab
Dashboard updates: John now assigned to Lab 5 (TMT room) - Status: "Waiting"
John walks to Room 5

---

**Scenario 2: Lab Specialist Makes Patient Pending - Jane for Blood Test**

### Step 1: Patient Jane Arrives
- TestItem: Blood Test, queue_status=WAITING, assigned_lab_id=2

### Step 2: Specialist Accepts Jane
- QueueEntry becomes CURRENT
- Blood Test status=IN_PROGRESS

### Step 3: Specialist Clicks "Move to Pending"
```
Specialist clicks "Move Current to Pending"
→ POST /api/queues/{lab_id}/move-current-to-pending

Updates:
- QueueEntry: queue_type = CURRENT → PENDING
- TestItem: queue_status=PENDING, is_blocked=FALSE
- Status now shows: "Pending"
```

### Step 4: Patient Waits in Reception (Pending Queue)
- Jane sits in waiting area
- Specialist can accept her from pending later
- She's locked to Lab 2 (NOT available for other labs)
- Status shows: "Pending"

### Step 5: Specialist Accepts from Pending
```
Specialist clicks "Accept from Pending" (can pick Jane)
→ POST /api/queues/{lab_id}/accept-from-pending

Updates:
- QueueEntry: queue_type = PENDING → CURRENT
- TestItem: status=IN_PROGRESS, queue_status=CURRENT
- Blood test resumes with Jane
```

---

**Scenario 3: Receptionist Blocks Patient - Mike for Multiple Tests**

### Step 1: Patient Mike Arrives
- TestItem 1: ECG, queue_status=WAITING, assigned_lab_id=1
- TestItem 2: TMT, queue_status=NOT_QUEUED

### Step 2: Receptionist Clicks "Block"
```
Receptionist clicks "Block" on Mike's record
→ POST /api/visits/{visit_id}/block

Updates:
- TestItem 1: is_blocked=TRUE
- TestItem 2: is_blocked=TRUE
- Status now shows: "Blocked"
```

### Step 3: Patient NOT Scheduled Anywhere
- Mike's records still exist but:
  - NOT in any waiting candidates
  - NOT scheduled to any labs
  - NOT eligible for OR optimization
- Status shows: "Blocked"

### Step 4: Receptionist Clicks "Unblock"
```
Receptionist clicks "Unblock"
→ POST /api/visits/{visit_id}/unblock

Updates:
- TestItem 1: is_blocked=FALSE, queue_status=NOT_QUEUED ← Reset!
- TestItem 2: is_blocked=FALSE, queue_status=NOT_QUEUED

Triggers: OR Optimization runs! (NEW)

OR Scheduler: "Mike is unblocked, let me find optimallabs..."
- Assigns TestItem 1 to Lab 1 or anywhere available
- Creates QueueEntry records
```

### Step 5: Patient Re-enters System
- Mike now appears in dashboards again
- Status: "Waiting"
- Can be assigned to same or different lab than before
- Treated like a fresh patient for scheduling

---

## Key Takeaways About Patient States

| Status | Meaning | OR Eligibility |
|--------|---------|---|
| **WAITING** | Test unassigned, patient ready for scheduling & queueing | ✅ **YES** - OR solver picks these |
| **PENDING** | Lab specialist locked patient to their queue | ❌ **NO** - Specialist decision pending, not for re-scheduling |
| **CURRENT** | Patient currently being tested | ❌ **NO** - Already in progress |
| **BLOCKED** | Receptionist excluded | ❌ **NO** - Completely excluded until unblocked |
| **DONE** | Test completed | ❌ **NO** - Already finished |

---

## Common Bugs and Their Causes

### 1. Patients Stay Stuck in "NOT_QUEUED"
**Cause:** OR-Scheduler not running or not triggering after patient creation
**Fix:** Check that `or_scheduler.run_optimization()` is called after patient/test creation

### 2. OR Solver Not Assigning Anyone
**Cause:** Constraints too strict (time window, dependency, compatibility)
**Fix:** Check `check_lab_compatibility()` and verify test categories match lab categories

### 3. Blocked Tests Still GetScheduled
**Cause:** `is_blocked` field not checked in `get_pending_tests()`
**Fix:** Ensure `is_blocked == False` filter is in the query

### 4. Pending Patients Disappear from Queues
**Cause:** Tests deleted or queue_status changed incorrectly
**Fix:** Check that PENDING tests are preserved and not modified during unblock

### 5. Dependencies Not Working
**Cause:** `ExplicitDependencies` table empty
**Fix:** Run seeding: `seed_database()` should populate dependencies

### 6. "No eligible lab" Error
**Cause:** Lab category doesn't match test category
**Fix:** Check `lab.category` matches `test.category`

### 7. QueueEntry Not Created After Assignment
**Cause:** `apply_schedule()` not being called or has errors
**Fix:** Verify OR-Scheduler creates queue entries in `apply_schedule()`

---

## How to Debug

### Check Database State
```bash
docker exec -it lab_scheduler_postgres psql -U postgres -d lab_scheduler

# See pending tests
SELECT id, test_name, queue_status, is_blocked, assigned_lab_id FROM test_items WHERE status='SCHEDULED';

# See queue entries
SELECT lab_id, queue_type, test_item_id FROM queue_entries;

# Check blocked tests
SELECT id, test_name, is_blocked FROM test_items WHERE is_blocked=true;

# See dependencies
SELECT * FROM explicit_dependencies LIMIT 10;
```

### Test With Sample Data
```bash
# Create test patient with blocking
curl -X POST http://localhost:8000/api/frontend/patients \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name":"Test Block",
    "patient_age":30,
    "patient_gender":"Male",
    "priority_type":"ROUTINE",
    "test_names":["CBC","ECG"]
  }'

# Get the visit_id from response

# Block the patient
curl -X POST http://localhost:8000/api/visits/{visit_id}/block

# Verify is_blocked=true in database

# Unblock the patient
curl -X POST http://localhost:8000/api/visits/{visit_id}/unblock

# Verify is_blocked=false and queue_status=NOT_QUEUED
```

### Check Backend Logs
```bash
docker-compose logs -f backend | grep -i "block\|pending\|schedule"
```

---

## Adding New Features

### Adding a New Test Type
1. Add to `Frontend/public/test_catalog.json`
2. Add to `Backend/seed_data/test_master.json`
3. Restart containers

### Adding a New Lab
1. Insert into `lab` table with correct `category`
2. Ensure `specialist_id` points to valid specialist
3. OR Scheduler will automatically use it

### Adding a New Constraint
1. Edit `or_scheduler.py` in `optimize_schedule()`
2. Add your constraint using `model.Add(...)`
3. Test with sample data

---

## Key Takeaways

1. **NOT_QUEUED is the trigger** - Only tests with this status are considered by OR solver for assignment
2. **WAITING means "ready but not for rescheduling"** - Already assigned to a lab, will NOT be reassigned by OR solver
3. **PENDING means "specialist locked"** - Not for OR optimization, waiting for specialist decision at their queue
4. **BLOCKED means "completely excluded"** - Receptionist-blocked tests are never considered until unblocked
5. **OR runs automatically** - After patient creation, test completion, unblock, lab change, specialist change
6. **QueueEntry tracks real-time state** - NEXT → CURRENT → PENDING or DONE
7. **WebSocket updates all dashboards** - Everyone sees changes in real-time
8. **Priority = Emergency > Fasting > Age > Wait time** - Scoring formula for optimization
9. **Movement penalty** - Elderly patients (age >= 50) heavily penalized for floor changes

---

*This document helps you understand the codebase. For technical API details, see README.md*
