import pandas as pd

from app.database.session import SessionLocal

from app.models.employee import Employee
from app.models.manager import Manager
from app.models.holiday import Holiday

from app.core.security import hash_password


def seed_managers(db):

    manager_df = pd.read_csv(
        "app/seeds/managers.csv"
    )

    print(manager_df)
    print(manager_df.columns)
    print(manager_df.to_dict("records"))

    for row in manager_df.to_dict("records"):

        print(row)
        print(row["password"])

        existing_manager = (
            db.query(Manager)
            .filter(
                Manager.email == row["email"]
            )
            .first()
        )

        if existing_manager:
            continue

        manager = Manager(
            name=row["name"],
            email=row["email"],
            password_hash=hash_password(
                row["password"]
            ),
            role=row["role"]
        )

        db.add(manager)

    db.commit()

    print("Managers Seeded")


def seed_employees(db):

    employee_df = pd.read_csv(
        "app/seeds/employees.csv"
    )

    print(employee_df)
    print(employee_df.columns)
    print(employee_df.to_dict("records"))

    employee_df = pd.read_csv(
        "app/seeds/employees.csv"
    )

    for row in employee_df.to_dict("records"):

        existing_employee = (
            db.query(Employee)
            .filter(
                Employee.phone_number ==
                str(row["phone_number"])
            )
            .first()
        )

        if existing_employee:
            continue

        employee = Employee(
            name=row["name"],
            phone_number=str(row["phone_number"]),
            whatsapp_name=row["whatsapp_name"],
            designation=row["designation"],
            is_active=row["is_active"]
        )

        db.add(employee)

    db.commit()

    print("Employees Seeded")


def seed_holidays(db):

    holiday_df = pd.read_csv(
        "app/seeds/holidays.csv"
    )

    for row in holiday_df.to_dict("records"):

        existing_holiday = (
            db.query(Holiday)
            .filter(
                Holiday.date == row["date"]
            )
            .first()
        )

        if existing_holiday:
            continue

        holiday = Holiday(
            name=row["name"],
            date=row["date"],
            location=row["location"],
            is_optional=row["is_optional"],
            created_by="SYSTEM"
        )

        db.add(holiday)

    db.commit()

    print("Holidays Seeded")


def main():

    db = SessionLocal()

    try:

        seed_managers(db)

        seed_employees(db)

        seed_holidays(db)

        print("Database Seeding Completed")

    except Exception as e:

        db.rollback()

        print(f"Seeding Failed: {e}")

    finally:

        db.close()


if __name__ == "__main__":
    main()