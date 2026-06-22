import os
from datetime import date, timedelta
from streamlit_calendar import calendar
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
print("API_URL =", API_URL)

def api_get(path: str, token: str, params: dict | None = None):
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{API_URL}{path}", headers=headers, params=params or {})
        response.raise_for_status()
        return response.json()


def api_post(path: str, token: str, json_body: dict | None = None):
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30.0) as client:
        
        response = client.post(f"{API_URL}{path}", headers=headers, json=json_body or {})
        response.raise_for_status()
        return response.json()

def generate_task_calendar_pdf(
    work_map,
    report_date
):

    pdf_path = "task_calendar_report.pdf"

    doc = SimpleDocTemplate(
        pdf_path
    )

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            report_date,
            styles["Heading2"]
        )
    )

    for task in sorted(work_map.keys()):

        employees = ", ".join(
            sorted(work_map[task])
        )

        content.append(
            Paragraph(
                f"{task} - {employees}",
                styles["BodyText"]
            )
        )

    doc.build(content)

    return pdf_path


def login_page():
    st.title("WAP Manager Dashboard")
    st.subheader("Login")
    email = st.text_input(
        "Email",
        key="login_email"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="login_password"
    )
    if st.button("Login", type="primary"):
        try:
            with httpx.Client(timeout=30.0) as client:
                st.write("EMAIL =", repr(email))
                st.write("PASSWORD =", repr(password))
                print(
                    "LOGIN:",
                    repr(st.session_state.login_email),
                    repr(st.session_state.login_password)
                )
                response = client.post(
                    f"{API_URL}/login",
                    json={
                        "email": st.session_state.login_email.strip(),
                        "password": st.session_state.login_password.strip()
                    },
                )

                st.write("Status:", response.status_code)
                st.write("Response:", response.text)
                if response.status_code == 200:
                    st.session_state.token = response.json()["access_token"]
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        except Exception as exc:
            st.error(f"Login failed: {exc}")


def sidebar_nav():
    st.sidebar.title("Navigation")
    return st.sidebar.radio(
        "Go to",
        [
            "Today's Updates",
            "Task Calendar",
            "Work List",
            "Reports",
            "Holidays",
        ],
    )


def page_today(token):

    st.header(f"Today's Updates - {date.today().strftime('%d-%m-%Y')}")

    data = api_get(
        "/api/reports/daily-activity",
        token
    )

    work_map = {}

    for employee_data in data.get("data", []):

        employee = employee_data["employee"]

        for task in employee_data["completed"]:

            if task not in work_map:

                work_map[task] = []

            work_map[task].append(
                employee
            )

    for idx, task in enumerate(sorted(work_map.keys()), start=1):
        st.markdown(
            f"##### {idx}. {task}"
        )
        for employee in sorted(work_map[task]):
            st.write(
                f"• {employee}"
            )

def page_daily_activity(token):

    st.header("Task Calendar")

    col1, col2 = st.columns([4, 1])

    with col1:

        data = api_get(
            "/api/reports/daily-activity",
            token
        )
    

    events = []

    work_map = {}

    report_date = data["date"]

    for employee_data in data.get("data", []):

        employee = employee_data["employee"]

        for task in employee_data["completed"]:

            events.append(
                {
                    "title": task,
                    "start": report_date
                }
            )

            if task not in work_map:

                work_map[task] = []

            work_map[task].append(
                employee
            )

    with col1:

        calendar(
            events=events,
            options={
                "initialView": "dayGridMonth"
            }
        )
    
    with col2:

        completed = len(work_map)

        worklist = api_get(
            "/api/worklist",
            token
        )

        total_tasks = len(
            worklist.get(
                "data",
                []
            )
        )

        remaining = total_tasks - completed

        fig = px.pie(
            values=[
                completed,
                remaining
            ],
            names=[
                "Completed",
                "Remaining"
            ],
            hole=0.75,
            color=[
                "Completed",
                "Remaining"
            ],
            color_discrete_map={
                "Completed": "#00C853",
                "Remaining": "#F5F5F5"
            }
        )

        fig.update_layout(
            showlegend=False,
            margin=dict(
                t=10,
                b=10,
                l=10,
                r=10
            ),
            annotations=[
                dict(
                    text=f"{completed}/{total_tasks}",
                    x=0.5,
                    y=0.5,
                    font_size=22,
                    showarrow=False
                )
            ]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.divider()

    report_text = f"\n{report_date}\n"

    for task in sorted(work_map.keys()):

        employees = ", ".join(
            sorted(work_map[task])
        )

        report_text += (
            f"\n{task} - {employees}"
        )

    pdf_file = generate_task_calendar_pdf(
        work_map,
        report_date
    )

    with open(
        pdf_file,
        "rb"
    ) as f:

        st.download_button(
            "Download PDF",
            f,
            file_name="TaskCalendar.pdf",
            mime="application/pdf"
        )

    st.markdown(
        f"""
        <script>
        function printPage() {{
            window.print();
        }}
        </script>
        """,
        unsafe_allow_html=True
    )

    if st.button("Print"):

        st.info(
            "Use Ctrl+P in browser"
        )


def page_worklist(token):

    st.header("Work List")

    task_name = st.text_input(
        "Task Name"
    )

    description = st.text_area(
        "Description"
    )

    target_date = st.date_input(
        "Target Date"
    )

    if st.button("Add Task"):

        api_post(
            "/api/worklist/",
            token,
            {
                "task_name": task_name,
                "description": description,
                "target_date": str(
                    target_date
                )
            }
        )

        st.success(
            "Task Added"
        )

        st.rerun()

    st.divider()

    st.subheader(
        "Pending Work"
    )

    worklist = api_get(
        "/api/worklist/",
        token
    )

    pending = [
        item
        for item in worklist["data"]
        if item["status"] == "PENDING"
    ]

    if pending:

        st.dataframe(
            pending,
            use_container_width=True,
            hide_index=True
        )

def page_reports(token):

    st.header("Reports")

    report_types = st.multiselect(
        "Select Reports",
        [
            "Daily Summary",
            "Task Calendar",
            "Work List Status",
        ]
    )

    start_date = st.date_input(
        "Start Date"
    )

    end_date = st.date_input(
        "End Date"
    )

    if st.button("Generate Reports"):

        for report in report_types:

            st.divider()

            st.subheader(report)

            if report == "Daily Summary":

                data = api_get(
                    "/api/reports/daily-activity",
                    token,
                    {
                        "report_date": str(end_date)
                    }
                )

                st.json(data)

            elif report == "Task Calendar":

                data = api_get(
                    "/api/reports/daily-activity",
                    token,
                    {
                        "report_date": str(end_date)
                    }
                )

                work_map = {}

                for item in data["data"]:

                    for task in item["completed"]:

                        work_map.setdefault(
                            task,
                            []
                        ).append(
                            item["employee"]
                        )

                rows = []

                for task, employees in work_map.items():

                    rows.append(
                        {
                            "Task": task,
                            "Employees": ", ".join(
                                employees
                            )
                        }
                    )

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True
                )

            elif report == "Work List Status":

                data = api_get(
                    "/api/worklist/",
                    token
                )

                st.dataframe(
                    pd.DataFrame(
                        data["data"]
                    ),
                    use_container_width=True
                )


def page_holidays(token):

    st.header("Holiday Management")

    data = api_get("/api/holidays/", token)

    df = pd.DataFrame(data.get("data", []))

    if not df.empty:

        df = df.reset_index(drop=True)

        df["S.No"] = df.index + 1

        df["date"] = pd.to_datetime(
            df["date"]
        ).dt.strftime("%d-%m-%Y")

        st.dataframe(
            df[["S.No", "name", "date"]],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("Add Holiday")

    with st.form("add_holiday"):

        name = st.text_input("Holiday Name")

        hdate = st.date_input("Date")

        submitted = st.form_submit_button(
            "Add Holiday"
        )

        if submitted:

            api_post(
                "/api/holidays/",
                token,
                {
                    "name": name,
                    "date": str(hdate),
                    "location": "All",
                    "is_optional": False
                }
            )

            st.success("Holiday Added")

            st.rerun()

    st.divider()

    st.subheader("Edit / Delete Holiday")

    holiday_options = {
        f"{row['name']} ({row['date']})": row['id']
        for _, row in df.iterrows()
    }

    selected_holiday = st.selectbox(
        "Select Holiday",
        list(holiday_options.keys())
    )

    holiday_id = holiday_options[selected_holiday]

    selected_row = df[
        df["id"] == holiday_id
    ].iloc[0]

    edit_name = st.text_input(
        "Holiday Name",
        value=selected_row["name"],
        key="edit_name"
    )

    edit_date = st.date_input(
        "Holiday Date",
        value=pd.to_datetime(
            selected_row["date"],
            dayfirst=True
        ).date(),
        key="edit_date"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button("Update Holiday"):

            with httpx.Client(timeout=30.0) as client:

                response = client.put(
                    f"{API_URL}/api/holidays/{holiday_id}",
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                    json={
                        "name": edit_name,
                        "date": str(edit_date),
                        "location": "All",
                        "is_optional": False
                    }
                )

            if response.status_code == 200:

                st.success(
                    "Holiday Updated"
                )

                st.rerun()

    with col2:

        if st.button("Delete Holiday"):

            with httpx.Client(timeout=30.0) as client:

                response = client.delete(
                    f"{API_URL}/api/holidays/{holiday_id}",
                    headers={
                        "Authorization": f"Bearer {token}"
                    }
                )

            if response.status_code == 200:

                st.success(
                    "Holiday Deleted"
                )

                st.rerun()

def main():
    st.set_page_config(page_title="WAP Dashboard", page_icon="📊", layout="wide")

    if not st.session_state.get("logged_in"):
        login_page()
        return

    token = st.session_state.token
    page = sidebar_nav()

    pages = {
        "Today's Updates": page_today,
        "Task Calendar": page_daily_activity,
        "Work List": page_worklist,
        "Reports": page_reports,
        "Holidays": page_holidays,
    }
    pages[page](token)

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


if __name__ == "__main__":
    main()
