from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import sqlite3
import os

# ---------- Config ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
CORS(app)

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Employees table
    # NOTE: using basic_salary consistently (was 'salary' before — this caused a bug)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            joining_date TEXT,
            basic_salary REAL,
            payroll_status TEXT DEFAULT 'Pending',
            status TEXT
        )
    """)

    # Attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Routes ----------
@app.route("/")
def home():
    return "Payroll Backend is running."

# ── Payroll ────────────────────────────────────────────────

# Get payroll data for all employees (with calculated net salary)
@app.route("/payroll", methods=["GET"])
def get_payroll():
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all employees
        cursor.execute("SELECT * FROM employees")
        employees = cursor.fetchall()

        payroll_list = []
        for emp in employees:
            emp = dict(emp)

            # Calculate overtime from attendance (count of 'Overtime' records)
            cursor.execute("""
                SELECT COUNT(*) FROM attendance
                WHERE employee_id = ? AND status = 'Overtime'
            """, (emp["id"],))
            overtime_days = cursor.fetchone()[0]

            # Calculate deductions from attendance (count of 'Absent' records)
            cursor.execute("""
                SELECT COUNT(*) FROM attendance
                WHERE employee_id = ? AND status = 'Absent'
            """, (emp["id"],))
            absent_days = cursor.fetchone()[0]

            # Simple calculation — adjust rates as needed
            overtime_pay = overtime_days * 500   # Rs 500 per overtime day
            deductions = absent_days * 500        # Rs 500 per absent day

            net_salary = (emp["basic_salary"] or 0) + overtime_pay - deductions

            payroll_list.append({
                "id": emp["id"],
                "name": emp["name"],
                "position": emp["position"],
                "department": emp["department"],
                "basic_salary": emp["basic_salary"] or 0,
                "overtime": overtime_pay,
                "deductions": deductions,
                "net_salary": net_salary,
                "payroll_status": emp.get("payroll_status") or "Pending"
            })

    return jsonify(payroll_list)


# Mark employee payroll as paid
@app.route("/mark_paid/<int:emp_id>", methods=["PUT"])
def mark_paid(emp_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE employees SET payroll_status = 'Paid' WHERE id = ?
        """, (emp_id,))

    return jsonify({"message": "Payroll marked as paid"})


# ── Employees ──────────────────────────────────────────────

# Get all employees
@app.route("/employees", methods=["GET"])
def get_employees():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees")
        rows = cursor.fetchall()
        employees = [dict(row) for row in rows]
    return jsonify(employees)


# Add employee
@app.route("/add_employee", methods=["POST"])
def add_employee():
    data = request.json or {}
    required_fields = ["name", "position", "department", "basic_salary", "status"]

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"'{field}' is required"}), 400

    try:
        basic_salary = int(data["basic_salary"])
    except (ValueError, TypeError):
        return jsonify({"error": "basic_salary must be a number"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (name, position, department, basic_salary, status,joining_date)
            VALUES (?, ?, ?, ?, ?,?)
        """, (
            data["name"],
            data["position"],
            data["department"],
            basic_salary,
            data["status"],
            data["joining_date"]
        ))
        employee_id = cursor.lastrowid

    return jsonify({"message": "Employee added successfully", "id": employee_id})


# Update employee
@app.route("/update_employee/<int:id>", methods=["PUT"])
def update_employee(id):
    data = request.json or {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE employees
            SET name = ?, position = ?, department = ?, basic_salary = ?, status = ?
            WHERE id = ?
        """, (
            data["name"],
            data["position"],
            data["department"],
            data["basic_salary"],
            data["status"],
            id
        ))

    return jsonify({"message": "Employee updated successfully"})


# Delete employee
@app.route("/delete_employee/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (emp_id,))

    return jsonify({"message": "Employee deleted successfully"})


# ── Attendance ─────────────────────────────────────────────

# Get all attendance (joined with employee details)
# FIX: removed duplicate route and fake sample data; now returns real DB data
# FIX: query now includes position, department, basic_salary, joining_date
@app.route("/attendance", methods=["GET"])
def get_attendance():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                a.id,
                e.name AS employee_name,
                e.position,
                e.department,
                e.basic_salary,
                e.joining_date,
                a.date,
                a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.date DESC
        """)
        rows = cursor.fetchall()

    attendance_list = [dict(row) for row in rows]
    return jsonify(attendance_list)


# Add attendance record
@app.route("/add-attendance", methods=["POST"])
def add_attendance():
    data = request.json or {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attendance (employee_id, date, status)
            VALUES (?, ?, ?)
        """, (
            data["employee_id"],
            data["date"],
            data["status"]
        ))

    return jsonify({"message": "Attendance added"})
#Employee stats
@app.route("/employee_stats", methods=["GET"])
def employee_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM employees WHERE status = 'Active'")
        active = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM employees WHERE status = 'Inactive'")
        inactive = cursor.fetchone()[0]
    return jsonify({"total": total, "active": active, "inactive": inactive})

# ── Payroll ────────────────────────────────────────────────

@app.route("/attendance_stats", methods=["GET"])
def attendance_stats():
    today = datetime.date.today().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'On time'", (today,))
        presence = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Absent'", (today,))
        absence = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Overtime'", (today,))
        overtime = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (today,))
        late = cursor.fetchone()[0]
    return jsonify({"presence": presence, "absence": absence, "overtime": overtime, "late": late})


# Calculate salary
@app.route("/calculate-salary", methods=["POST"])
def calculate_salary():
    data = request.json or {}

    try:
        basic = int(data.get("basic", 0))
        allowance = int(data.get("allowance", 0))
        tax = int(data.get("tax", 0))
        leaves = int(data.get("leaves", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "All salary fields must be numbers"}), 400

    leave_deduction = leaves * 500
    net_salary = basic + allowance - tax - leave_deduction

    return jsonify({
        "net_salary": net_salary,
        "leave_deduction": leave_deduction
    })


# ---------- Run ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)