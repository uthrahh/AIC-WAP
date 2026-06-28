# Worklog Automation Platform for AIC

---

# Project Information

## Project Title

Worklog Automation Platform

## Repository

> https://github.com/uthrahh/AIC-WAP
> 

## Description

The Worklog Automation Platform is an AI-assisted worklog management system developed to automate the collection, extraction, tracking, reporting, and monitoring of employee daily updates shared through WhatsApp.

Instead of manually maintaining spreadsheets and reports, employees submit their daily work updates in a designated WhatsApp group. The system synchronizes these messages, extracts completed and pending tasks, updates the task database, generates reports, tracks productivity, and provides an administrative dashboard.

The platform supports AI-powered worklog extraction using OpenAI or Google Gemini while also providing a rule-based parser as a fallback.

## Framework

FastAPI

## Developed By

Pavithra Uthrah R. K. - uthrahrk@gmail.com

---

# Technology Stack

## Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- Uvicorn

## Frontend

- HTML5
- Bootstrap 5
- Jinja2 Templates
- JavaScript

## Database

- PostgreSQL

## AI Integration

- OpenAI API (Optional)
- Google Gemini API (Optional)

## WhatsApp Integration

- whatsapp-web.js
- Puppeteer
- Node.js

## Reporting

- Pandas
- OpenPyXL
- ReportLab

---

# Features

## WhatsApp Integration

- Sync today's WhatsApp messages
- Automatic employee identification
- QR-based WhatsApp login
- WhatsApp logout
- Session persistence

## Worklog Extraction

- AI-assisted task extraction
- Rule-based parser fallback
- Detect completed tasks
- Detect pending tasks
- Leave detection
- Employee collaboration detection
- Deadline extraction

## Task Management

- Add pending tasks
- Complete tasks automatically
- Track task ownership
- Pending task dashboard
- Completed task dashboard

## Employee Management

- Add employees
- Edit employee details
- Delete employees
- Holiday management

## Dashboard

- Today's updates
- Submission statistics
- Pending tasks
- Completed tasks
- Employee productivity
- Missing submissions

## Reports

- Daily activity report
- Completed task report
- Excel export
- PDF export

---

# Project Structure

```
AIC-WAP
│
├── app
│   ├── api
│   ├── core
│   ├── database
│   ├── models
│   ├── routers
│   ├── schemas
│   ├── services
│   ├── templates
│   ├── static
│   ├── utils
│   └── main.py
│
├── reports
├── uploads
├── whatsapp
│   ├── whatsapp_listener.js
│   ├── package.json
│   └── node_modules
│
├── requirements.txt
├── .env
└── README.md
```

---

# Installation Guide

## 1. Clone Repository

```bash
git clone https://github.com/uthrahh/AIC-WAP
cd AIC-WAP
```

## 2. Create Virtual Environment

Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Node.js

Install Node.js (v18 or above)

Verify installation:

```bash
node -v
npm -v
```

## 5. Install WhatsApp Dependencies

Navigate to the WhatsApp folder.

```bash
cd whatsapp
```

Install packages.

```bash
npm install
```

This installs:

- whatsapp-web.js
- puppeteer
- axios

Return to the project root.

```bash
cd ..
```

## 6. Configure PostgreSQL

Create a PostgreSQL database.

Example

```
Database : worklog

User     : postgres

Password : ********

Host     : localhost

Port     : 5432
```

Update the database URL inside

```
app/core/config.py

or

.env
```

Example

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/worklog
```

## 7. Configure AI APIs (Optional)

### OpenAI

```
OPENAI_API_KEY=your_api_key
AI_PROVIDER=openai
```

### Gemini

```
GEMINI_API_KEY=your_api_key
AI_PROVIDER=gemini
```

If no API key is configured, the application automatically uses the built-in parser.

## 8. Create Database Tables

Run

```bash
alembic upgrade head
```

or

```bash
python create_tables.py
```

depending on your setup.

## 9. Run the Application

Start FastAPI

```bash
uvicorn app.main:app --reload
```

Application

```
http://127.0.0.1:8000
```

---

# First-Time WhatsApp Setup

1. Open the application.
2. Navigate to

```
Settings
```

1. Click

```
Sync WhatsApp
```

1. Scan the QR Code.
2. Wait until

```
READY
```

appears in the terminal.

1. The application will automatically synchronize today's messages from the configured WhatsApp group.

---

# WhatsApp Message Format

Employees should submit updates in the following format.

```
1. Completed Task 1

2. Completed Task 2 - Employee A, Employee B

Pending:

1. Pending Task 1

2. Pending Task 2; 30-06-26; Employee A
```

Supported formats include natural-language work updates such as

```
Work Update

1. Discussion with vendors
2. Completed PPT preparation
3. Followed up with startups

Pending:

1. ERP Documentation
2. Website Testing
```

and

```
Overall Outcome for the Day

1. Infrastructure planning - Aravind
2. Vendor discussion - Hiran
3. Startup onboarding - Vignesh, Dhena
```

---

# Running the System

Start FastAPI

```bash
uvicorn app.main:app --reload
```

Open

```
http://127.0.0.1:8000
```

To synchronize WhatsApp:

```
Home

↓

Sync WhatsApp
```

The listener automatically reads today's messages and updates the database.

---

# Frequently Used Commands

Start server

```bash
uvicorn app.main:app --reload
```

Install Python packages

```bash
pip install -r requirements.txt
```

Install WhatsApp packages

```bash
cd whatsapp
npm install
```

Run Alembic migrations

```bash
alembic upgrade head
```

Reset database

```sql
TRUNCATE TABLE daily_updates RESTART IDENTITY CASCADE;
TRUNCATE TABLE work_items RESTART IDENTITY CASCADE;
```

---

# License

This project was developed for the Crescent Innovation & Incubation Council (CIIC) as an internal worklog automation platform for employee work tracking and reporting.
