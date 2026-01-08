from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

# ---------- Config ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
CORS(app)

# ---------- Database Setup ----------
import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            joining_date TEXT,
            salary REAL,
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

# Add employee
@app.route("/add_employee", methods=["POST"])
def add_employee():
    data = request.json or {}
    required_fields = ["name", "position", "department", "basic_salary", "status"]

    # Validation
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"'{field}' is required"}), 400

    try:
        basic_salary = int(data["basic_salary"])
    except ValueError:
        return jsonify({"error": "basic_salary must be a number"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (name, position, department, basic_salary, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["position"],
            data["department"],
            basic_salary,
            data["status"]
        ))
        employee_id = cursor.lastrowid

    return jsonify({"message": "Employee added successfully", "id": employee_id})



@app.route("/attendance")
def get_all_attendance():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            a.id,
            e.name AS employee_name,
            a.date,
            a.status
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        ORDER BY a.date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    attendance_list = []
    for row in rows:
        attendance_list.append({
            "id": row["id"],
            "employee_name": row["employee_name"],
            "date": row["date"],
            "status": row["status"]
        })

    return attendance_list



@app.route("/update_employee/<int:id>", methods=["PUT"])
def update_employee(id):
    data = request.json

    conn = get_db()
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

    conn.commit()
    conn.close()

    return jsonify({"message": "Employee updated successfully"})

# Get all employees
@app.route("/employees", methods=["GET"])
def get_employees():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees")
        rows = cursor.fetchall()
        employees = [dict(row) for row in rows]

    return jsonify(employees)

@app.route("/add-attendance", methods=["POST"])
def add_attendance():
    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance (employee_id, date, status)
        VALUES (?, ?, ?)
    """, (
        data["employee_id"],
        data["date"],
        data["status"]
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Attendance added"})


@app.route("/attendance", methods=["GET"])
def get_attendance():
    """
    Returns a list of attendance records
    Each record should have: employee_name, check_in, check_out, date, status
    """
    # Example: replace this with your actual DB query
    sample_data = [
        {"employee_name": "John Doe", "check_in": "09:00", "check_out": "17:00", "date": "2026-01-06", "status": "On time"},
        {"employee_name": "Jane Smith", "check_in": "09:30", "check_out": "17:00", "date": "2026-01-06", "status": "Late"},
        {"employee_name": "Bob Lee", "check_in": "08:50", "check_out": "18:00", "date": "2026-01-06", "status": "Overtime"}
    ]
    return jsonify(sample_data)


@app.route("/delete_employee/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Employee deleted successfully"})


# Calculate salary
@app.route("/calculate-salary", methods=["POST"])
def calculate_salary():
    data = request.json or {}

    try:
        basic = int(data.get("basic", 0))
        allowance = int(data.get("allowance", 0))
        tax = int(data.get("tax", 0))
        leaves = int(data.get("leaves", 0))
    except ValueError:
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
