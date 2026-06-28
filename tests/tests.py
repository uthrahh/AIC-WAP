from app.database.session import SessionLocal
from app.models.employee import Employee

db = SessionLocal()

employee = Employee(
    name="Uthrah",
    phone_number="9999999999"
)

db.add(employee)
db.commit()

print("Inserted")