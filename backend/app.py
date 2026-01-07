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
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT NOT NULL,
                basic_salary INTEGER NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.commit()

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

# Get all employees
@app.route("/employees", methods=["GET"])
def get_employees():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees")
        rows = cursor.fetchall()
        employees = [dict(row) for row in rows]

    return jsonify(employees)


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
    app.run(debug=True)
