# WAP - WhatsApp Worklog Automation Platform

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis (optional, for future job state)

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Database

```bash
pip install -r requirements-wap.txt
alembic upgrade head
python -m app.seeds.seed
```

### 4. Start Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start WhatsApp Gateway

```bash
cd whatsapp-gateway
npm install
node index.js
```

Scan the QR code when prompted. The gateway forwards group messages to the backend.

### 6. Start Dashboard

```bash
streamlit run dashboard/app.py
```

## Architecture

```
WhatsApp Group → Gateway (Node.js) → FastAPI Backend → PostgreSQL
                                          ├── APScheduler (19:00 extraction, reminders, summaries)
                                          ├── Google Sheets Sync
                                          └── Streamlit Dashboard
```

## Scheduled Jobs (IST, working days only)

| Time  | Job                    |
|-------|------------------------|
| 19:00 | Information Extraction |
| 19:01 | Reminder (repeats 30 min until 21:00) |
| 20:00 | Daily Summary          |
| Fri 20:00 | Weekly Summary     |

## WhatsApp Commands

Mention `@WAP` in the worklog group:

- `@WAP` — show command menu
- `@WAP Generate Daily Summary`
- `@WAP 12-06-2026 pending work:` followed by numbered list

## Employee Worklog Format

```
Completed Tasks:
1. Task A
2. Task B

Pending Tasks:
1. Task C

Blockers:
1. Blocker A
```

Or simply: `On Leave`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /login` | Manager JWT login |
| `GET /api/employees` | List employees |
| `GET /api/reports/*` | Work reports |
| `GET /api/productivity` | Productivity metrics |
| `GET /api/summary/*` | Daily/weekly summaries |
| `POST /api/worklogs/ingest` | Message ingestion |
| `GET /api/holidays` | Holiday management |

## Docker

```bash
docker compose up -d
```

## Default Manager Login

Seed a manager via `app/seeds/managers.csv` then run `python -m app.seeds.seed`.
