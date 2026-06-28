import json
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.employees import router as employees_router
from app.api.holidays import router as holidays_router
from app.api.reports import router as reports_router
from app.api.summary import router as summary_router
from app.api.worklist import router as worklist_router
from app.api.worklogs import router as worklogs_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.templates import templates
from app.database.session import SessionLocal
from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.work_item import WorkItem
from app.scheduler.scheduler import scheduler
from app.utils.text_parser import (
    parse_worklog_message,
    tasks_from_json,
    tasks_to_json,
    tasks_match
)
from sqlalchemy import text

setup_logging()

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# ----------------------------
# API ROUTERS
# ----------------------------

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(reports_router)
app.include_router(summary_router)
app.include_router(worklogs_router)
app.include_router(holidays_router)
app.include_router(audit_router)
app.include_router(worklist_router)


# ----------------------------
# HELPERS
# ----------------------------

def _find_employee(employees, sender_name: str, sender_phone: str, message: str):
    """
    Three-tier employee lookup:
      1. Exact phone number match (most reliable when stored correctly)
      2. Name-word intersection from sender_name
      3. Name mentioned inside the message body (handles Unknown sender)
    Returns the matched Employee or None.
    """

    clean_phone = sender_phone.strip()

    # --- Tier 1: phone ---
    if clean_phone:
        for emp in employees:
            if emp.phone_number and emp.phone_number.strip() == clean_phone:
                print(f"MATCHED by phone: {emp.name}")
                return emp

    # --- Tier 2: sender display name ---
    lower_sender = sender_name.strip().lower()
    if lower_sender and lower_sender != "unknown":
        sender_words = set(lower_sender.split())
        for emp in employees:
            words = set()
            if emp.name:
                words.update(emp.name.lower().split())
            if emp.whatsapp_name:
                words.update(emp.whatsapp_name.lower().split())
            if sender_words & words:
                print(f"MATCHED by display name: {emp.name}")
                return emp

    # --- Tier 3: employee name appears inside the message ---
    # Works when the worklog lists tasks with "- Name" attribution.
    # We pick the employee whose name appears most often (most tasks = the sender).
    message_lower = message.lower()
    best_emp = None
    best_count = 0
    for emp in employees:
        if not emp.name:
            continue
        # match each word of the employee's first name
        first_word = emp.name.split()[0].lower()
        count = message_lower.count(first_word)
        if count > best_count:
            best_count = count
            best_emp = emp
    if best_emp and best_count > 0:
        print(f"MATCHED by message content ({best_count} hits): {best_emp.name}")
        return best_emp

    return None


# ----------------------------
# WEB PAGES
# ----------------------------

@app.get("/")
def today_page(request: Request):

    db = SessionLocal()

    try:

        today = date.today()

        updates = (
            db.query(DailyUpdate, Employee)
            .join(Employee, DailyUpdate.employee_id == Employee.id)
            .filter(func.date(DailyUpdate.timestamp) == today)
            .all()
        )

        total_employees = (
            db.query(Employee)
            .filter(Employee.is_active == True)
            .count()
        )

        work_map = {}

        for update, employee in updates:

            completed = tasks_from_json(update.completed_tasks)

            if not completed:
                continue

            for item in completed:

                if isinstance(item, dict):

                    task = item.get("task", "").strip().lower()

                    if not task:
                        continue

                    work_map.setdefault(task, set())

                    emp_list = item.get("employees", [])

                    if emp_list:
                        for emp in emp_list:
                            if emp:
                                work_map[task].add(emp)
                    else:
                        work_map[task].add(employee.name)

                else:

                    task = str(item).strip().lower()

                    if not task:
                        continue

                    work_map.setdefault(task, set())
                    work_map[task].add(employee.name)

        work_map = {
            task: sorted(users)
            for task, users in work_map.items()
        }

        employees_sent_today = len(
            {
                emp.id
                for update, emp in updates
                if tasks_from_json(update.completed_tasks)
            }
        )

        print("WORK MAP")
        print(work_map)

        print("UPDATES")
        for update, emp in updates:
            completed = tasks_from_json(update.completed_tasks)
            for item in completed:
                if isinstance(item, dict):
                    print(emp.name, "->", item.get("task", ""))
                else:
                    print(emp.name, "->", item)

        return templates.TemplateResponse(
            request=request,
            name="pages/today.html",
            context={
                "today": today,
                "updates": updates,
                "work_map": work_map,
                "total_employees": total_employees,
                "employees_sent_today": employees_sent_today,
            }
        )

    finally:
        db.close()


@app.get("/worklogs/clear")
def clear_worklogs():

    db = SessionLocal()

    try:
        db.execute(text("""
            TRUNCATE TABLE
                daily_updates,
                work_items,
                employee_metrics,
                audit_logs,
                pending_work,
                weekly_reports,
                whatsapp_messages
            RESTART IDENTITY CASCADE;
        """))
        db.commit()
    finally:
        db.close()

    return RedirectResponse("/", status_code=303)


@app.get("/settings")
def settings_page(
    request: Request,
    employee_add: int = 0,
    employee_manage: int = 0,
    holiday_add: int = 0,
    holiday_manage: int = 0,
):

    db = SessionLocal()

    try:

        employees = db.query(Employee).order_by(Employee.id).all()
        holidays  = db.query(Holiday).order_by(Holiday.date).all()

        return templates.TemplateResponse(
            request=request,
            name="pages/settings.html",
            context={
                "employees": employees,
                "holidays": holidays,
                "employee_add": employee_add,
                "employee_manage": employee_manage,
                "holiday_add": holiday_add,
                "holiday_manage": holiday_manage,
            }
        )

    finally:
        db.close()


@app.get("/employees/add")
def add_employee_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/add_employee.html",
        context={}
    )


@app.post("/employees/add")
def save_employee(
    request: Request,
    name: str = Form(...),
    designation: str = Form(""),
    phone_number: str = Form(...),
    whatsapp_name: str = Form("")
):

    db = SessionLocal()

    try:

        existing = (
            db.query(Employee)
            .filter(Employee.phone_number == phone_number)
            .first()
        )

        if existing:
            return {"status": "already_exists", "employee": name}   # fixed: was `employee_name`

        employee = Employee(
            name=name,
            designation=designation,
            phone_number=phone_number,
            whatsapp_name=whatsapp_name
        )
        db.add(employee)
        db.commit()

    finally:
        db.close()

    return RedirectResponse("/settings", status_code=303)


@app.get("/employees/delete/{employee_id}")
def delete_employee_page(employee_id: int):

    db = SessionLocal()

    try:
        db.query(DailyUpdate).filter(
            DailyUpdate.employee_id == employee_id
        ).update({DailyUpdate.employee_id: None})

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            db.delete(employee)
        db.commit()

    finally:
        db.close()

    return RedirectResponse("/settings?employee_manage=1", status_code=303)


@app.get("/employees/edit/{employee_id}")
def edit_employee_page(request: Request, employee_id: int):

    db = SessionLocal()

    try:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()

        if not employee:
            return RedirectResponse("/settings?employee_manage=1", status_code=303)

        return templates.TemplateResponse(
            request=request,
            name="pages/edit_employee.html",
            context={"employee": employee}
        )

    finally:
        db.close()


@app.post("/employees/edit/{employee_id}")
def update_employee(
    employee_id: int,
    name: str = Form(...),
    designation: str = Form(""),
    phone_number: str = Form(...),
    whatsapp_name: str = Form("")
):

    db = SessionLocal()

    try:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()

        if employee:
            employee.name = name
            employee.designation = designation
            employee.phone_number = phone_number
            employee.whatsapp_name = whatsapp_name
            db.commit()

    finally:
        db.close()

    return RedirectResponse("/settings?employee_manage=1", status_code=303)


@app.get("/employees/download")
def download_employees():

    db = SessionLocal()

    try:

        employees = (
            db.query(Employee)
            .filter(Employee.is_active == True)
            .order_by(Employee.name)
            .all()
        )

        pdf_path = "employees_report.pdf"
        doc = SimpleDocTemplate(pdf_path)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Employee Directory", styles["Title"]))
        elements.append(Spacer(1, 20))

        data = [["ID", "Name", "Designation", "Number", "Username"]]
        for emp in employees:
            data.append([
                str(emp.id),
                emp.name or "",
                emp.designation or "",
                emp.phone_number or "",
                emp.whatsapp_name or ""
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID",       (0, 0), (-1, -1), 1, colors.black),
            ("FONTNAME",   (0, 0), (-1, 0),  "Helvetica-Bold"),
        ]))
        elements.append(table)
        doc.build(elements)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename="Employees.pdf"
        )

    finally:
        db.close()


@app.post("/api/worklogs/whatsapp")
def whatsapp_webhook(payload: dict):

    db = SessionLocal()

    try:

        sender_name  = payload.get("sender_name",  "").strip()
        sender_phone = payload.get("sender_phone", "").strip()
        message      = payload.get("message",      "")

        print(f"WEBHOOK  name={sender_name!r}  phone={sender_phone!r}")

        employees = (
            db.query(Employee)
            .filter(Employee.is_active == True)
            .all()
        )

        employee = _find_employee(employees, sender_name, sender_phone, message)

        if employee is None:
            print("NO EMPLOYEE MATCHED")
            return {
                "status": "employee_not_found",
                "sender": sender_name or sender_phone
            }

        parsed = parse_worklog_message(message)
        print("PARSED COMPLETED:", parsed.completed_tasks)
        print("PARSED PENDING:  ", parsed.pending_tasks)

        # -----------------------
        # SAVE PENDING TASKS
        # -----------------------

        for pending_task in parsed.pending_tasks:

            parts = [x.strip() for x in pending_task.split(";")]
            task_name = parts[0]
            employees_text = ""

            if " - " in task_name:
                task_name, employees_text = task_name.rsplit(" - ", 1)
            elif " – " in task_name:
                task_name, employees_text = task_name.rsplit(" – ", 1)

            target_date = None
            if len(parts) >= 2:
                try:
                    target_date = datetime.strptime(parts[1], "%d-%m-%y").date()
                except Exception:
                    pass

            if len(parts) >= 3:
                employees_text = parts[2]

            exists = (
                db.query(WorkItem)
                .filter(WorkItem.task_name.ilike(f"%{task_name}%"))
                .first()
            )

            if not exists:
                db.add(WorkItem(
                    task_name=task_name,
                    target_date=target_date,
                    employees=employees_text,
                    status="PENDING"
                ))

        # -----------------------
        # BUILD COMPLETED TASKS
        # -----------------------

        completed = []

        for task in parsed.completed_tasks:

            employee_names = []

            for short_name in task["employees"]:
                short_name = short_name.strip()
                matched = False

                for emp in employees:
                    if not emp.name:
                        continue
                    emp_words   = {x.lower() for x in emp.name.split()}
                    short_words = {x.lower() for x in short_name.split()}
                    if short_words & emp_words:
                        employee_names.append(emp.name)
                        matched = True
                        break

                if not matched:
                    employee_names.append(short_name)

            if not employee_names:
                employee_names.append(employee.name)

            completed.append({
                "task":      task["task"].strip(),
                "employees": sorted(set(employee_names))
            })

        # -----------------------
        # MARK TASKS COMPLETED
        # -----------------------

        for item in completed:
            work_items = (
                db.query(WorkItem)
                .filter(WorkItem.status == "PENDING")
                .all()
            )
            for work in work_items:
                if tasks_match(work.task_name, item["task"]):
                    work.status       = "COMPLETED"
                    work.completed_by = ", ".join(item["employees"])

        # -----------------------
        # SAVE DAILY UPDATE
        # -----------------------

        existing = (
            db.query(DailyUpdate)
            .filter(
                DailyUpdate.employee_id == employee.id,
                func.date(DailyUpdate.timestamp) == date.today()
            )
            .first()
        )

        if existing:
            existing.completed_tasks = tasks_to_json(completed)
            existing.pending_tasks   = tasks_to_json(parsed.pending_tasks)
            existing.raw_message     = message
        else:
            db.add(DailyUpdate(
                employee_id=employee.id,
                timestamp=datetime.now(),
                completed_tasks=tasks_to_json(completed),
                pending_tasks=tasks_to_json(parsed.pending_tasks),
                raw_message=message
            ))

        db.commit()

        return {"status": "saved", "employee": employee.name}

    finally:
        db.close()


# ----------------------------
# SYSTEM
# ----------------------------

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def startup():
    scheduler.start()


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()


@app.post("/tasks/add")
def add_task(
    task_name:   str = Form(...),
    description: str = Form(""),
    target_date: str = Form(...)
):

    db = SessionLocal()

    try:
        db.add(WorkItem(
            task_name=task_name,
            description=description,
            target_date=target_date
        ))
        db.commit()
    finally:
        db.close()

    return RedirectResponse("/tasks?task_manage=1", status_code=303)


@app.get("/tasks/delete/{task_id}")
def delete_task(task_id: int):

    db = SessionLocal()

    try:
        task = db.query(WorkItem).filter(WorkItem.id == task_id).first()
        if task:
            db.delete(task)
            db.commit()
    finally:
        db.close()

    return RedirectResponse("/tasks?task_manage=1", status_code=303)


@app.get("/tasks/edit/{task_id}")
def edit_task_page(request: Request, task_id: int):

    db = SessionLocal()

    try:
        task = db.query(WorkItem).filter(WorkItem.id == task_id).first()
        return templates.TemplateResponse(
            request=request,
            name="pages/edit_task.html",
            context={"task": task}
        )
    finally:
        db.close()


@app.post("/tasks/edit/{task_id}")
def update_task(
    task_id:     int,
    task_name:   str = Form(...),
    description: str = Form(""),
    target_date: str = Form(...)
):

    db = SessionLocal()

    try:
        task = db.query(WorkItem).filter(WorkItem.id == task_id).first()
        if task:
            task.task_name   = task_name
            task.description = description
            task.target_date = target_date
            db.commit()
    finally:
        db.close()

    return RedirectResponse("/tasks?task_manage=1", status_code=303)


@app.get("/sync-whatsapp")
def sync_whatsapp():

    BASE_DIR = Path(__file__).resolve().parent.parent
    listener = BASE_DIR / "whatsapp" / "whatsapp_listener.js"

    print(listener)
    print(listener.exists())

    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
    except Exception:
        pass

    subprocess.Popen(["node", str(listener)])

    return RedirectResponse("/", status_code=303)


@app.get("/api/whatsapp/groups")
def get_groups():
    file = Path("groups.json")
    if not file.exists():
        return []
    return json.loads(file.read_text())


@app.post("/api/whatsapp/logout")
def whatsapp_logout():

    shutil.rmtree(".wwebjs_auth", ignore_errors=True)

    config = Path("whatsapp/config.json")
    if config.exists():
        config.unlink()

    return RedirectResponse("/settings", status_code=303)


@app.get("/tasks")
def tasks_page(
    request: Request,
    task_add: int = 0,
    task_manage: int = 0
):

    db = SessionLocal()

    try:

        all_pending_tasks = (
            db.query(WorkItem)
            .filter(WorkItem.status == "PENDING")
            .order_by(WorkItem.target_date)
            .all()
        )

        updates = (
            db.query(DailyUpdate, Employee)
            .join(Employee, DailyUpdate.employee_id == Employee.id)
            .all()
        )

        completed_map = {}

        for update, emp in updates:

            tasks = tasks_from_json(update.completed_tasks)
            if not tasks:
                continue

            for item in tasks:

                if isinstance(item, dict):
                    task_key  = item.get("task", "").lower().strip()
                    emp_names = item.get("employees", [emp.name])
                else:
                    task_key  = str(item).lower().strip()
                    emp_names = [emp.name]

                if not task_key:
                    continue

                completed_map.setdefault(
                    task_key,
                    {"date": update.timestamp.date(), "employees": set()}
                )
                completed_map[task_key]["employees"].update(emp_names)

        completed_tasks = [
            {
                "task":      k.title(),
                "date":      v["date"],
                "employees": ", ".join(sorted(v["employees"]))
            }
            for k, v in completed_map.items()
        ]
        completed_tasks.sort(key=lambda x: x["date"], reverse=True)

        completed_names = set(completed_map.keys())

        pending_tasks = [
            t for t in all_pending_tasks
            if not any(tasks_match(t.task_name, c) for c in completed_names)
        ]

        return templates.TemplateResponse(
            request=request,
            name="pages/tasks.html",
            context={
                "tasks":           pending_tasks,
                "completed_tasks": completed_tasks,
                "task_add":        task_add,
                "task_manage":     task_manage,
            }
        )

    finally:
        db.close()