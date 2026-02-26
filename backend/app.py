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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            joining_date TEXT,
            basic_salary REAL,
            payroll_status TEXT DEFAULT 'Pending',
            status TEXT,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin (name, password) VALUES ('Admin', 'admin123')")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            employee_name TEXT,
            leave_type TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# FIX: always open and close connection per query to prevent database locked error
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchone() if one else cursor.fetchall()
    conn.close()
    return rv

def execute_db(query, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, args)
    lastrowid = cursor.lastrowid
    conn.commit()
    conn.close()
    return lastrowid

# ---------- Routes ----------

@app.route("/")
def home():
    return "Payroll Backend is running."

# ── Login ──────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    row = query_db(
        "SELECT id, name, role FROM employees WHERE name=? AND password=?",
        (data.get("name"), data.get("password")),
        one=True
    )
    if row:
        return jsonify({"success": True, "name": row["name"], "role": row["role"]})
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

# ── Employees ──────────────────────────────────────────────
@app.route("/employees", methods=["GET"])
def get_employees():
    rows = query_db("SELECT * FROM employees")
    return jsonify([dict(row) for row in rows])

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

    emp_id = execute_db(
        "INSERT INTO employees (name, position, department, basic_salary, status, joining_date) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data["position"], data["department"], basic_salary, data["status"], data.get("joining_date", ""))
    )
    return jsonify({"message": "Employee added successfully", "id": emp_id})

@app.route("/update_employee/<int:id>", methods=["PUT"])
def update_employee(id):
    data = request.json or {}
    execute_db(
        "UPDATE employees SET name=?, position=?, department=?, basic_salary=?, status=?, joining_date=? WHERE id=?",
        (data["name"], data["position"], data["department"], data["basic_salary"], data["status"], data.get("joining_date", ""), id)
    )
    return jsonify({"message": "Employee updated successfully"})

@app.route("/delete_employee/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    execute_db("DELETE FROM employees WHERE id=?", (emp_id,))
    return jsonify({"message": "Employee deleted successfully"})

@app.route("/employee_stats", methods=["GET"])
def employee_stats():
    total = query_db("SELECT COUNT(*) FROM employees", one=True)[0]
    active = query_db("SELECT COUNT(*) FROM employees WHERE status='Active'", one=True)[0]
    inactive = query_db("SELECT COUNT(*) FROM employees WHERE status='Inactive'", one=True)[0]
    return jsonify({"total": total, "active": active, "inactive": inactive})

# ── Attendance ─────────────────────────────────────────────
@app.route("/attendance", methods=["GET"])
def get_attendance():
    rows = query_db("""
        SELECT a.id, e.name AS employee_name, e.position, e.department,
               e.basic_salary, e.joining_date, a.date, a.status
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        ORDER BY a.date DESC
    """)
    return jsonify([dict(row) for row in rows])

@app.route("/add-attendance", methods=["POST"])
def add_attendance():
    data = request.json or {}
    execute_db(
        "INSERT INTO attendance (employee_id, date, status) VALUES (?, ?, ?)",
        (data["employee_id"], data["date"], data["status"])
    )
    return jsonify({"message": "Attendance added"})

@app.route("/attendance_stats", methods=["GET"])
def attendance_stats():
    today = datetime.date.today().isoformat()
    presence = query_db("SELECT COUNT(*) FROM attendance WHERE date=? AND status='On time'", (today,), one=True)[0]
    absence = query_db("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'", (today,), one=True)[0]
    overtime = query_db("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Overtime'", (today,), one=True)[0]
    late = query_db("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Late'", (today,), one=True)[0]
    return jsonify({"presence": presence, "absence": absence, "overtime": overtime, "late": late})

# ── Payroll ────────────────────────────────────────────────
@app.route("/payroll", methods=["GET"])
def get_payroll():
    employees = query_db("SELECT * FROM employees")
    payroll_list = []
    for emp in employees:
        emp = dict(emp)
        overtime_days = query_db("SELECT COUNT(*) FROM attendance WHERE employee_id=? AND status='Overtime'", (emp["id"],), one=True)[0]
        absent_days = query_db("SELECT COUNT(*) FROM attendance WHERE employee_id=? AND status='Absent'", (emp["id"],), one=True)[0]
        overtime_pay = overtime_days * 500
        deductions = absent_days * 500
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

@app.route("/mark_paid/<int:emp_id>", methods=["PUT"])
def mark_paid(emp_id):
    execute_db("UPDATE employees SET payroll_status='Paid' WHERE id=?", (emp_id,))
    return jsonify({"message": "Payroll marked as paid"})

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
    return jsonify({"net_salary": net_salary, "leave_deduction": leave_deduction})

# ── Announcements ──────────────────────────────────────────
@app.route("/announcements", methods=["GET"])
def get_announcements():
    rows = query_db("SELECT * FROM announcements ORDER BY created_at DESC")
    return jsonify([dict(row) for row in rows])

@app.route("/announcements", methods=["POST"])
def add_announcement():
    data = request.json
    execute_db("INSERT INTO announcements (text, created_at) VALUES (?, ?)", (data["text"], data["created_at"]))
    return jsonify({"message": "Announcement posted"})

@app.route("/announcements/<int:id>", methods=["DELETE"])
def delete_announcement(id):
    execute_db("DELETE FROM announcements WHERE id=?", (id,))
    return jsonify({"message": "Announcement deleted"})

@app.route("/announcements/<int:id>", methods=["PUT"])
def edit_announcement(id):
    data = request.json
    execute_db("UPDATE announcements SET text=? WHERE id=?", (data["text"], id))
    return jsonify({"message": "Announcement updated"})

# ── Admin ──────────────────────────────────────────────────
@app.route("/admin", methods=["GET"])
def get_admin():
    row = query_db("SELECT id, name FROM admin LIMIT 1", one=True)
    return jsonify(dict(row)) if row else jsonify({"name": "Admin"})

@app.route("/update_admin", methods=["PUT"])
def update_admin():
    data = request.json
    if data.get("password"):
        execute_db("UPDATE admin SET name=?, password=? WHERE id=1", (data["name"], data["password"]))
    else:
        execute_db("UPDATE admin SET name=? WHERE id=1", (data["name"],))
    return jsonify({"message": "Profile updated successfully"})

# ── Leave Requests ─────────────────────────────────────────
@app.route("/leave_requests", methods=["GET"])
def get_leave_requests():
    rows = query_db("SELECT * FROM leave_requests ORDER BY id DESC")
    return jsonify([dict(row) for row in rows])

@app.route("/leave_requests/<int:id>", methods=["PUT"])
def update_leave_request(id):
    data = request.json
    execute_db("UPDATE leave_requests SET status=? WHERE id=?", (data["status"], id))
    return jsonify({"message": f"Leave request {data['status']}"})

# ---------- Run ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)


# ── User Side Routes ───────────────────────────────────────

# Get single employee profile
@app.route("/user/<int:emp_id>", methods=["GET"])
def get_user(emp_id):
    row = query_db("SELECT id, name, position, department, joining_date, basic_salary, status FROM employees WHERE id=?", (emp_id,), one=True)
    return jsonify(dict(row)) if row else jsonify({"error": "User not found"}), 404

# Get employee attendance for current month
@app.route("/user/<int:emp_id>/attendance", methods=["GET"])
def get_user_attendance(emp_id):
    import datetime
    today = datetime.date.today()
    month_start = today.replace(day=1).isoformat()
    rows = query_db("""
        SELECT date, status FROM attendance
        WHERE employee_id=? AND date >= ?
        ORDER BY date DESC
    """, (emp_id, month_start))
    return jsonify([dict(row) for row in rows])

# Get employee leave requests
@app.route("/user/<int:emp_id>/leave_requests", methods=["GET"])
def get_user_leave_requests(emp_id):
    rows = query_db("SELECT * FROM leave_requests WHERE employee_id=? ORDER BY id DESC", (emp_id,))
    return jsonify([dict(row) for row in rows])

# Submit leave request
@app.route("/leave_requests", methods=["POST"])
def submit_leave_request():
    data = request.json or {}
    execute_db("""
        INSERT INTO leave_requests (employee_id, employee_name, leave_type, start_date, end_date, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    """, (data["employee_id"], data["employee_name"], data["leave_type"], data["start_date"], data["end_date"], data.get("reason", "")))
    return jsonify({"message": "Leave request submitted"})

# Get employee payroll/payslip
@app.route("/user/<int:emp_id>/payroll", methods=["GET"])
def get_user_payroll(emp_id):
    emp = query_db("SELECT * FROM employees WHERE id=?", (emp_id,), one=True)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    emp = dict(emp)
    overtime_days = query_db("SELECT COUNT(*) FROM attendance WHERE employee_id=? AND status='Overtime'", (emp_id,), one=True)[0]
    absent_days = query_db("SELECT COUNT(*) FROM attendance WHERE employee_id=? AND status='Absent'", (emp_id,), one=True)[0]
    overtime_pay = overtime_days * 500
    deductions = absent_days * 500
    net_salary = (emp["basic_salary"] or 0) + overtime_pay - deductions
    return jsonify({
        "name": emp["name"],
        "position": emp["position"],
        "department": emp["department"],
        "joining_date": emp["joining_date"],
        "basic_salary": emp["basic_salary"] or 0,
        "overtime": overtime_pay,
        "deductions": deductions,
        "net_salary": net_salary,
        "payroll_status": emp.get("payroll_status") or "Pending"
    })