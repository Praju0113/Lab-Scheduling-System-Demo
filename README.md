# Lab Scheduling System - Technical Documentation

## Overview

The Lab Scheduling System is a comprehensive healthcare queue management platform that uses **Operations Research (OR)** optimization and **Planning Poker** collaborative estimation to efficiently route patients through medical laboratory tests.

## Key Features

- **OR-Tools CP-SAT Solver**: Mathematical optimization for patient-to-lab assignments
- **Planning Poker**: Collaborative estimation for test duration forecasting
- **Real-time Queue Management**: Dynamic patient flow with live updates
- **Dependency Resolution**: Automatic handling of test prerequisites (e.g., ECG before TMT)
- **Multi-dashboard Support**: Receptionist, Specialist, and Admin views

---

## System Architecture

### Backend Stack
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Optimization Engine**: Google OR-Tools CP-SAT solver
- **Real-time**: WebSocket for live updates
- **Containerization**: Docker & Docker Compose

### Frontend Stack
- **Framework**: React + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **UI Components**: shadcn/ui
- **Icons**: Lucide React

---

## Core Components

### 1. OR Scheduler (`app/services/or_scheduler.py`)

The mathematical optimization engine that assigns patients to labs using constraint programming.

#### Key Constraints:
1. **Lab Compatibility**: Tests can only be assigned to compatible labs
2. **Dependency Satisfaction**: Prerequisites must be completed (e.g., ECG → TMT)
3. **Time Window Fitting**: Tests must fit within specialist shifts and lab hours
4. **One Place at a Time**: Patient cannot be in multiple labs simultaneously
5. **Lab Capacity**: One test at a time per lab

#### Objective Function:
- Maximize priority scores (emergency > fasting > elderly)
- Minimize patient movement between floors
- Balance lab workload

#### Usage:
```python
from app.services.or_scheduler import ORScheduler

or_scheduler = ORScheduler(db)
or_scheduler.run_optimization()  # Runs assignment algorithm
```

---

### 2. Planning Poker (`app/services/planning_poker.py`)

Collaborative estimation system for forecasting test durations using the Planning Poker methodology.

#### Features:
- **Session Management**: Create estimation sessions for tests
- **Voting**: Team members vote using Fibonacci sequence (1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
- **Consensus Calculation**: Median rounded to nearest Fibonacci number
- **Anonymous Voting**: Hidden votes until reveal

#### API Endpoints:
```
POST   /api/planning-poker/sessions           - Create new session
POST   /api/planning-poker/sessions/{id}/vote - Cast vote
POST   /api/planning-poker/sessions/{id}/reveal - Reveal votes
POST   /api/planning-poker/sessions/{id}/complete - Complete session
GET    /api/planning-poker/sessions/{id}/stats - Get statistics
```

---

### 3. Queue Service (`app/services/queue.py`)

Manages the real-time state of patient queues at each lab.

#### Key States:
- **NOT_QUEUED**: Test needs OR optimization assignment
- **WAITING**: Test assigned to lab, waiting to be called
- **CURRENT**: Patient currently being processed
- **PENDING**: Test paused (e.g., waiting for water intake)
- **DONE**: Test completed

#### Operations:
- `accept_current()`: Promote NEXT to CURRENT
- `move_current_to_pending()`: Pause current test
- `accept_from_pending()`: Resume pending test
- `complete_current()`: Mark test as done

---

### 4. Database Models (`app/models.py`)

#### Core Entities:

**Visit**: Patient visit record
- `public_id`: Human-readable ID (e.g., A0114001)
- `patient_name`, `patient_age`, `patient_gender`
- `priority_type`: EMERGENCY, FASTING, ELDERLY, ROUTINE
- `arrival_time`: When patient arrived

**TestItem**: Individual test within a visit
- `test_code`: Unique test identifier (e.g., "ELECTROCARDIOGRAM_ECG")
- `test_name`: Human-readable name
- `category`: Medical category (e.g., "ECG", "Ultrasound")
- `duration_minutes`: Estimated time required
- `status`: SCHEDULED, IN_PROGRESS, COMPLETED, UNSCHEDULABLE
- `queue_status`: NOT_QUEUED, WAITING, CURRENT, PENDING, DONE
- `assigned_lab_id`: Which lab is handling this test

**Lab**: Laboratory/Room where tests are performed
- `lab_code`: Unique identifier
- `category`: Type of tests supported
- `floor`: Physical location for movement optimization
- `specialist_id`: Assigned medical professional
- `opening_time`, `closing_time`: Operating hours
- `cleanup_duration_minutes`: Time between tests

**ExplicitDependencies**: Test prerequisites
- `test_code`: The test that has a dependency
- `depends_on_test_code`: The prerequisite test
- `is_strict`: If True, must complete before; if False, recommended order

**QueueEntry**: Queue state tracking
- `lab_id`, `visit_id`, `test_item_id`: Links to entities
- `queue_type`: NEXT, CURRENT, PENDING
- `pending_since`: When test was paused

---

### 5. API Endpoints (`app/main.py`)

#### Patient Management:
```
POST   /api/frontend/patients           - Create new patient visit
PATCH  /api/frontend/patients/{id}    - Update patient
GET    /api/frontend/visits           - List all visits for records table
POST   /api/lims/ingest               - Ingest from LIMS webhook
```

#### Test Operations:
```
POST   /api/tests/{id}/start           - Start test (IN_PROGRESS)
POST   /api/tests/{id}/complete        - Complete test
POST   /api/tests/{id}/unblock         - Resume from pending (NOT_QUEUED)
POST   /api/tests/{id}/pending         - Pause test
```

#### Visit Operations:
```
POST   /api/visits/{id}/block          - Block entire visit
POST   /api/visits/{id}/unblock        - Unblock entire visit
```

#### Queue/Lobby:
```
GET    /api/lobby/next                - Get waiting patients
GET    /api/lobby/pending              - Get pending patients
GET    /api/labs/{id}/current          - Get current patient in lab
GET    /api/lobby/feeds               - Combined feed for displays
GET    /api/queues/{lab_id}/snapshot   - Full queue state for lab
```

#### Catalog & Admin:
```
GET    /api/frontend/catalog           - Available tests
GET    /api/admin/dashboard           - Statistics and metrics
```

---

## Data Flow

### 1. New Patient Registration
1. Frontend calls `POST /api/frontend/patients` with patient details and selected tests
2. Backend creates `Visit` and `TestItem` records with `queue_status=NOT_QUEUED`
3. `ORScheduler.run_optimization()` assigns tests to optimal labs
4. Tests transition to `WAITING` state with `assigned_lab_id` set
5. WebSocket emits `visit.updated` event to all connected clients

### 2. Patient Called to Lab
1. Specialist clicks "Accept" in their dashboard
2. Frontend calls `POST /api/tests/{id}/start`
3. Test status changes to `IN_PROGRESS`, queue_status to `CURRENT`
4. WebSocket updates all dashboards

### 3. Test Completion
1. Specialist clicks "Complete"
2. Frontend calls `POST /api/tests/{id}/complete`
3. Test marked as `COMPLETED`, queue entry deleted
4. `ORScheduler.run_optimization()` recalculates for dependencies
5. If dependent tests (e.g., TMT after ECG) were blocked, they become assignable

### 4. Handling Dependencies
- TMT requires ECG to be completed first
- Ultrasound requires full bladder (Urine test should come after)
- OR solver checks `ExplicitDependencies` before assignment
- If dependency not met, test stays `NOT_QUEUED` until prerequisite completes

---

## Configuration

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/lab_scheduling

# Backend
BACKEND_PORT=8000
RESET_DB_ON_STARTUP=true
SEED_ON_STARTUP=true

# Frontend
FRONTEND_PORT=5173
VITE_BACKEND_URL=http://localhost:8000
```

### Docker Services
- **postgres**: PostgreSQL 16 Alpine
- **backend**: FastAPI application (port 8000)
- **frontend**: React Vite dev server (port 5173)

---

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Running with Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart backend after code changes
docker-compose restart backend
```

### Local Backend Development
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Local Frontend Development
```bash
cd Frontend
npm install
npm run dev
```

---

## OR Solver Algorithm Details

### Decision Variables
```python
x[(test_id, lab_id)] = 1 if test assigned to lab, 0 otherwise
```

### Constraints (Mathematical)
1. **Assignment**: `sum(x[(test_id, lab_id)] for all labs) == 1` (each test to exactly one lab)
2. **Compatibility**: `x[(test_id, lab_id)] == 0` if lab cannot perform test
3. **Dependencies**: `x[(test_id, lab_id)] == 0` if prerequisite not completed
4. **Time Window**: `x[(test_id, lab_id)] == 0` if test doesn't fit in shift hours
5. **One Place**: `x[(test_id, lab_id)] == 0` if patient already has active test
6. **Capacity**: `sum(x[(test_id, lab_id)] for all tests) <= 1` per lab

### Objective Function
```
Maximize: sum(priority_score * x[(test, lab)] - movement_penalty * x[(test, lab)])
```

---

## Testing

### Sample API Calls
```bash
# Create a patient
curl -X POST http://localhost:8000/api/frontend/patients \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "John Doe",
    "patient_age": 45,
    "patient_gender": "Male",
    "priority_type": "ROUTINE",
    "test_names": ["Complete Blood Count", "ECG"]
  }'

# Get lobby status
curl http://localhost:8000/api/lobby/next

# Start a test
curl -X POST http://localhost:8000/api/tests/1/start
```

---

## Troubleshooting

### Common Issues

**Backend won't start (NameError: Visit not defined)**
- Fix: Ensure `from app.models import ...` is outside TYPE_CHECKING block in or_scheduler.py

**Patients stuck in NOT_QUEUED**
- Check that `ORScheduler.get_pending_tests()` queries for NOT_QUEUED status
- Verify OR-Tools constraints aren't too restrictive

**Database connection errors**
- Verify postgres container is healthy: `docker ps`
- Check DATABASE_URL environment variable

**Tests not auto-assigning**
- Ensure `run_optimization()` is called after patient creation
- Check that tests are created with `queue_status=NOT_QUEUED`

---

## Contributing

### Code Structure
```
Backend/
├── app/
│   ├── main.py              # FastAPI endpoints
│   ├── models.py            # Database models
│   ├── db.py                # Database connection
│   ├── seed.py              # Database seeding
│   ├── catalog.py           # Test catalog
│   └── services/
│       ├── or_scheduler.py  # OR optimization engine
│       ├── planning_poker.py # Estimation service
│       ├── queue.py         # Queue management
│       └── scheduling.py    # Legacy wrapper (deprecated)
├── requirements.txt
└── Dockerfile

Frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── services/
├── package.json
└── Dockerfile
```

---

## License

MIT License - See LICENSE file for details

---

## Contact

For support or questions, please contact the development team.

---

*Last Updated: April 14, 2026*
*Version: 2.0 (OR-Integrated)*
