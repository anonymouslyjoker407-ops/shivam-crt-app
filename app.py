import os
import io
import json
import uuid
import base64
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, Response

# Check optional dependencies for Excel and PDF exports
try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shivam_omega_secure_key_2026")

DATA_FILE = "omega_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "attendance" not in data:
                    data["attendance"] = []
                if "cash_expenses" not in data:
                    data["cash_expenses"] = []
                return data
        except Exception:
            pass
    return {"attendance": [], "cash_expenses": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Change default credentials as needed
        if username == "admin" and password == "shivam123":
            session["user"] = username
            return redirect(url_for("index"))
        else:
            error = "Invalid Username or Password"
    
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    data = load_data()
    action = request.args.get("action", "attendance")
    search_query = request.args.get("search", "").strip().lower()

    if request.method == "POST":
        form_type = request.form.get("form_type")
        
        if form_type == "add_attendance":
            new_record = {
                "id": str(uuid.uuid4())[:8],
                "name": request.form.get("name"),
                "card_number": request.form.get("card_number"),
                "role": request.form.get("role"),
                "in_time": request.form.get("in_time"),
                "out_time": request.form.get("out_time"),
                "signature": request.form.get("signature"),
                "amount": float(request.form.get("amount", 0) or 0),
                "conveyance": float(request.form.get("conveyance", 0) or 0)
            }
            data["attendance"].append(new_record)
            save_data(data)
            return redirect(url_for("index", action="attendance"))

        elif form_type == "edit_attendance":
            rec_id = request.form.get("id")
            for item in data["attendance"]:
                if item.get("id") == rec_id:
                    item["name"] = request.form.get("name")
                    item["card_number"] = request.form.get("card_number")
                    item["role"] = request.form.get("role")
                    item["in_time"] = request.form.get("in_time")
                    item["out_time"] = request.form.get("out_time")
                    item["signature"] = request.form.get("signature")
                    item["amount"] = float(request.form.get("amount", 0) or 0)
                    item["conveyance"] = float(request.form.get("conveyance", 0) or 0)
                    break
            save_data(data)
            return redirect(url_for("index", action="attendance"))

        elif form_type == "add_cash_expense":
            attachments = []
            files = request.files.getlist("attachments")
            for f in files:
                if f and f.filename:
                    file_bytes = f.read()
                    encoded = base64.b64encode(file_bytes).decode("utf-8")
                    attachments.append({
                        "file_name": f.filename,
                        "file_data": encoded
                    })

            new_cash = {
                "id": str(uuid.uuid4())[:8],
                "date": request.form.get("date"),
                "pay_to": request.form.get("pay_to"),
                "description": request.form.get("description"),
                "amount": float(request.form.get("amount", 0) or 0),
                "attachments": attachments
            }
            data["cash_expenses"].append(new_cash)
            save_data(data)
            return redirect(url_for("index", action="cash_expenses"))

        elif form_type == "edit_cash_expense":
            rec_id = request.form.get("id")
            for item in data["cash_expenses"]:
                if item.get("id") == rec_id:
                    item["date"] = request.form.get("date")
                    item["pay_to"] = request.form.get("pay_to")
                    item["description"] = request.form.get("description")
                    item["amount"] = float(request.form.get("amount", 0) or 0)
                    
                    # Append new files if uploaded
                    files = request.files.getlist("attachments")
                    for f in files:
                        if f and f.filename:
                            file_bytes = f.read()
                            encoded = base64.b64encode(file_bytes).decode("utf-8")
                            item.setdefault("attachments", []).append({
                                "file_name": f.filename,
                                "file_data": encoded
                            })
                    break
            save_data(data)
            return redirect(url_for("index", action="cash_expenses"))

    # Filtering data for search
    filtered_attendance = data["attendance"]
    if search_query:
        filtered_attendance = [
            a for a in data["attendance"] 
            if search_query in str(a.get("name", "")).lower() or
               search_query in str(a.get("card_number", "")).lower() or
               search_query in str(a.get("role", "")).lower() or
               search_query in str(a.get("in_time", "")).lower() or
               search_query in str(a.get("out_time", "")).lower() or
               search_query in str(a.get("signature", "")).lower() or
               search_query in str(a.get("amount", "")).lower() or
               search_query in str(a.get("conveyance", "")).lower() or
               search_query in str(a.get("amount", 0) + a.get("conveyance", 0)).lower()
        ]

    filtered_cash_expenses = data["cash_expenses"]
    if search_query:
        filtered_cash_expenses = [
            c for c in data["cash_expenses"]
            if search_query in str(c.get("date", "")).lower() or
               search_query in str(c.get("pay_to", "")).lower() or
               search_query in str(c.get("description", "")).lower() or
               search_query in str(c.get("amount", "")).lower()
        ]

    filtered_total_attendance = sum(a.get("amount", 0) + a.get("conveyance", 0) for a in filtered_attendance)
    filtered_total_cash_expenses = sum(c.get("amount", 0) for c in filtered_cash_expenses)

    return render_template_string(
        DASHBOARD_HTML,
        action=action,
        search_query=search_query,
        filtered_attendance=filtered_attendance,
        filtered_total_attendance=filtered_total_attendance,
        filtered_cash_expenses=filtered_cash_expenses,
        filtered_total_cash_expenses=filtered_total_cash_expenses
    )

@app.route("/delete/attendance/<rec_id>")
def delete_attendance(rec_id):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    data["attendance"] = [a for a in data["attendance"] if a.get("id") != rec_id]
    save_data(data)
    return redirect(url_for("index", action="attendance"))

@app.route("/delete/cash_expense/<rec_id>")
def delete_cash_expense(rec_id):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    data["cash_expenses"] = [c for c in data["cash_expenses"] if c.get("id") != rec_id]
    save_data(data)
    return redirect(url_for("index", action="cash_expenses"))

@app.route("/export/excel")
def export_excel():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    
    if not EXCEL_SUPPORT:
        return "openpyxl library not installed on server.", 400

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Ledger"

    headers = ["Sr #", "Name", "Card Number", "Role", "In Time", "Out Time", "Signature", "Amount (₹)", "Conveyance (₹)", "Total (₹)"]
    ws.append(headers)

    for idx, a in enumerate(data.get("attendance", []), 1):
        amt = a.get("amount", 0)
        conv = a.get("conveyance", 0)
        ws.append([
            idx,
            a.get("name", ""),
            a.get("card_number", ""),
            a.get("role", ""),
            a.get("in_time", ""),
            a.get("out_time", ""),
            a.get("signature", ""),
            amt,
            conv,
            amt + conv
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment;filename=Shivam_CRT_Attendance_Ledger.xlsx"}
    )

@app.route("/export/pdf")
def export_pdf():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()

    if not PDF_SUPPORT:
        return "reportlab library not installed on server.", 400

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#10b981'), spaceAfter=12)

    elements.append(Paragraph("Shivam CRT - Attendance & Stipend Master Ledger", title_style))
    elements.append(Spacer(1, 10))

    table_data = [["Sr", "Name", "Card", "Role", "In", "Out", "Amt", "Conv", "Total"]]
    for idx, a in enumerate(data.get("attendance", []), 1):
        amt = a.get("amount", 0)
        conv = a.get("conveyance", 0)
        table_data.append([
            str(idx),
            str(a.get("name", "")),
            str(a.get("card_number", "")),
            str(a.get("role", "")),
            str(a.get("in_time", "")),
            str(a.get("out_time", "")),
            f"Rs {amt}",
            f"Rs {conv}",
            f"Rs {amt + conv}"
        ])

    t = Table(table_data, colWidths=[30, 90, 60, 80, 50, 50, 60, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 7),
    ]))

    elements.append(t)
    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=Shivam_CRT_Attendance_Ledger.pdf"}
    )

@app.route("/export/cash_excel")
def export_cash_excel():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    
    if not EXCEL_SUPPORT:
        return "openpyxl library not installed on server.", 400

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cash Expenses Ledger"

    headers = ["Sr #", "Date", "Pay To", "Description", "Amount (₹)"]
    ws.append(headers)

    for idx, c in enumerate(data.get("cash_expenses", []), 1):
        ws.append([
            idx,
            c.get("date", ""),
            c.get("pay_to", ""),
            c.get("description", ""),
            c.get("amount", 0)
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment;filename=Shivam_CRT_Cash_Expenses_Ledger.xlsx"}
    )

@app.route("/export/cash_pdf")
def export_cash_pdf():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()

    if not PDF_SUPPORT:
        return "reportlab library not installed on server.", 400

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#10b981'), spaceAfter=12)

    elements.append(Paragraph("Shivam CRT - Cash Expenses Master Ledger", title_style))
    elements.append(Spacer(1, 10))

    table_data = [["Sr", "Date", "Pay To", "Description", "Amount"]]
    for idx, c in enumerate(data.get("cash_expenses", []), 1):
        table_data.append([
            str(idx),
            str(c.get("date", "")),
            str(c.get("pay_to", "")),
            str(c.get("description", "")),
            f"Rs {c.get('amount', 0)}"
        ])

    t = Table(table_data, colWidths=[40, 90, 130, 200, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#065f46')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
    ]))

    elements.append(t)
    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=Shivam_CRT_Cash_Expenses_Ledger.pdf"}
    )

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login - Shivam Omega Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-gray-100 flex items-center justify-center h-screen">
    <div class="bg-gray-900 p-8 rounded-2xl border border-gray-800 shadow-2xl w-full max-w-md">
        <h2 class="text-2xl font-bold text-emerald-400 mb-6 text-center">[ SHIVAM SINGH OMEGA ]</h2>
        {% if error %}
            <div class="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-xs rounded-xl text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" class="space-y-4">
            <div>
                <label class="text-xs text-gray-400">Username</label>
                <input type="text" name="username" required class="w-full mt-1 p-3 bg-gray-800 rounded-xl border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400">
            </div>
            <div>
                <label class="text-xs text-gray-400">Password</label>
                <input type="password" name="password" required class="w-full mt-1 p-3 bg-gray-800 rounded-xl border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400">
            </div>
            <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Secure Login</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Shivam Singh Omega Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex flex-col font-sans">
    <!-- Navbar -->
    <nav class="bg-gray-900 border-b border-gray-800 px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <span class="text-emerald-400 font-bold font-mono text-lg">[ SHIVAM SINGH OMEGA DASHBOARD ]</span>
        </div>
        <div class="flex items-center space-x-4">
            <a href="/logout" class="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl text-xs font-bold border border-red-500/30 transition">Logout</a>
        </div>
    </nav>

    <!-- Main Container -->
    <div class="flex flex-1 overflow-hidden">
        <!-- Sidebar Navigation -->
        <aside class="w-64 bg-gray-900/50 border-r border-gray-800 p-4 space-y-2 hidden md:block">
            <a href="/?action=attendance" class="flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-bold transition {% if action == 'attendance' %}bg-emerald-500/10 text-emerald-400 border border-emerald-500/30{% else %}text-gray-400 hover:bg-gray-800/50 hover:text-gray-200{% endif %}">
                <span>📋 Attendance Ledger</span>
            </a>
            <a href="/?action=cash_expenses" class="flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-bold transition {% if action == 'cash_expenses' %}bg-emerald-500/10 text-emerald-400 border border-emerald-500/30{% else %}text-gray-400 hover:bg-gray-800/50 hover:text-gray-200{% endif %}">
                <span>💵 Cash Expenses</span>
            </a>
        </aside>

        <!-- Content Area -->
        <main class="flex-1 overflow-y-auto p-6">
            <div class="md:hidden flex space-x-2 mb-6">
                <a href="/?action=attendance" class="flex-1 text-center py-2 rounded-xl text-xs font-bold {% if action == 'attendance' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %}">Attendance</a>
                <a href="/?action=cash_expenses" class="flex-1 text-center py-2 rounded-xl text-xs font-bold {% if action == 'cash_expenses' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %}">Cash Expenses</a>
            </div>

            {% if action == 'attendance' %}
            <div class="space-y-6">
                <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                    <h2 class="text-xl font-bold text-emerald-400 mb-4">📋 Add Attendance Entry</h2>
                    <form method="POST" class="grid grid-cols-1 sm:grid-cols-4 gap-4">
                        <input type="hidden" name="form_type" value="add_attendance">
                        <div>
                            <label class="text-xs text-gray-400">Name</label>
                            <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Card Number</label>
                            <input type="text" name="card_number" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Role</label>
                            <input type="text" name="role" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">In Time</label>
                            <input type="text" name="in_time" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="09:00 AM">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Out Time</label>
                            <input type="text" name="out_time" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="06:00 PM">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Signature / Status</label>
                            <input type="text" name="signature" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" value="Verified">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Amount (₹)</label>
                            <input type="number" name="amount" required value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Conveyance (₹)</label>
                            <input type="number" name="conveyance" required value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div class="sm:col-span-4">
                            <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Attendance Entry</button>
                        </div>
                    </form>
                </div>

                <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                    <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                        <h3 class="font-bold">📋 Master Attendance & Stipend Ledger</h3>
                        <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
                            <form method="GET" action="/" class="flex items-center gap-2 w-full sm:w-auto">
                                <input type="hidden" name="action" value="attendance">
                                <input type="text" name="search" value="{{ search_query }}" placeholder="Search name, card, role..." class="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 w-full sm:w-64">
                                <button type="submit" class="px-3 py-1.5 bg-emerald-500 text-gray-950 font-bold rounded-xl text-xs hover:bg-emerald-600 transition">Search</button>
                                {% if search_query %}
                                    <a href="/?action=attendance" class="px-2 py-1.5 bg-gray-700 text-gray-300 rounded-xl text-xs hover:bg-gray-600">Clear</a>
                                {% endif %}
                            </form>
                            <div class="flex items-center gap-1 border-l border-gray-700 pl-2">
                                <a href="/export/excel" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs transition flex items-center gap-1">📊 Excel</a>
                                <a href="/export/pdf" class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs transition flex items-center gap-1">📄 PDF</a>
                            </div>
                        </div>
                    </div>

                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-gray-800/80 text-gray-300 uppercase tracking-wider font-mono">
                                    <th class="p-3 border-r border-gray-700">Sr #</th>
                                    <th class="p-3 border-r border-gray-700">Name</th>
                                    <th class="p-3 border-r border-gray-700">Card #</th>
                                    <th class="p-3 border-r border-gray-700">Role</th>
                                    <th class="p-3 border-r border-gray-700">In / Out</th>
                                    <th class="p-3 border-r border-gray-700">Status</th>
                                    <th class="p-3 border-r border-gray-700">Amount</th>
                                    <th class="p-3 border-r border-gray-700">Conveyance</th>
                                    <th class="p-3 border-r border-gray-700">Total</th>
                                    <th class="p-3 text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-800 font-mono">
                                {% for a in filtered_attendance %}
                                <tr class="hover:bg-gray-800/35 transition">
                                    <td class="p-3 border-r border-gray-800">{{ loop.index }}</td>
                                    <td class="p-3 border-r border-gray-800 font-bold text-emerald-400">{{ a.name }}</td>
                                    <td class="p-3 border-r border-gray-800 text-gray-300">{{ a.card_number }}</td>
                                    <td class="p-3 border-r border-gray-800 text-gray-300">{{ a.role }}</td>
                                    <td class="p-3 border-r border-gray-800 text-gray-400">{{ a.in_time }} - {{ a.out_time }}</td>
                                    <td class="p-3 border-r border-gray-800 text-indigo-400">{{ a.signature }}</td>
                                    <td class="p-3 border-r border-gray-800">₹{{ a.amount }}</td>
                                    <td class="p-3 border-r border-gray-800">₹{{ a.conveyance }}</td>
                                    <td class="p-3 border-r border-gray-800 font-bold text-emerald-400">₹{{ a.amount + a.conveyance }}</td>
                                    <td class="p-3 text-center space-x-2 whitespace-nowrap">
                                        <button onclick='openEditAttendanceModal({{ a|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-[10px] font-bold cursor-pointer">Edit</button>
                                        <a href="/delete/attendance/{{ a.id }}" onclick="return confirm('Confirm delete attendance?');" class="text-red-400 bg-red-500/10 px-2 py-1 rounded text-[10px] font-bold inline-block">Delete</a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                            <tfoot>
                                <tr class="bg-gray-800/90 font-mono font-bold text-gray-200 border-t-2 border-gray-700">
                                    <td colspan="8" class="p-3 text-right uppercase tracking-wider text-emerald-400">Total Sum:</td>
                                    <td colspan="2" class="p-3 text-emerald-400">₹{{ filtered_total_attendance }}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>

            {% elif action == 'cash_expenses' %}
            <div class="space-y-6">
                <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                    <h2 class="text-xl font-bold text-emerald-400 mb-4">💵 Add Cash Expense & Files</h2>
                    <form method="POST" enctype="multipart/form-data" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <input type="hidden" name="form_type" value="add_cash_expense">
                        <div>
                            <label class="text-xs text-gray-400">Date</label>
                            <input type="date" name="date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Pay To</label>
                            <input type="text" name="pay_to" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Recipient Name">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Description</label>
                            <input type="text" name="description" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Expense purpose">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400">Amount (₹)</label>
                            <input type="number" name="amount" required value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                        </div>
                        <div class="sm:col-span-2">
                            <label class="text-xs text-gray-400">Upload Multiple Files (PDF/Images)</label>
                            <input type="file" name="attachments" multiple accept=".pdf,image/*" class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-gray-300">
                        </div>
                        <div class="sm:col-span-3">
                            <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Cash Expense</button>
                        </div>
                    </form>
                </div>

                <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                    <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                        <h3 class="font-bold">💵 Cash Expense Ledger</h3>
                        
                        <!-- Search & Export Controls -->
                        <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
                            <form method="GET" action="/" class="flex items-center gap-2 w-full sm:w-auto">
                                <input type="hidden" name="action" value="cash_expenses">
                                <input type="text" name="search" value="{{ search_query }}" placeholder="Search pay to, desc, amount..." class="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 w-full sm:w-64">
                                <button type="submit" class="px-3 py-1.5 bg-emerald-500 text-gray-950 font-bold rounded-xl text-xs hover:bg-emerald-600 transition">Search</button>
                                {% if search_query %}
                                    <a href="/?action=cash_expenses" class="px-2 py-1.5 bg-gray-700 text-gray-300 rounded-xl text-xs hover:bg-gray-600">Clear</a>
                                {% endif %}
                            </form>
                            <div class="flex items-center gap-1 border-l border-gray-700 pl-2">
                                <a href="/export/cash_excel" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs transition flex items-center gap-1">📊 Excel</a>
                                <a href="/export/cash_pdf" class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs transition flex items-center gap-1">📄 PDF</a>
                            </div>
                        </div>
                    </div>

                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-gray-800/80 text-gray-300 uppercase tracking-wider font-mono">
                                    <th class="p-3 border-r border-gray-700">Sr #</th>
                                    <th class="p-3 border-r border-gray-700">Date</th>
                                    <th class="p-3 border-r border-gray-700">Pay To</th>
                                    <th class="p-3 border-r border-gray-700">Description</th>
                                    <th class="p-3 border-r border-gray-700">Amount</th>
                                    <th class="p-3 border-r border-gray-700">Files Attach</th>
                                    <th class="p-3 text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-800 font-mono">
                                {% for c in filtered_cash_expenses %}
                                <tr class="hover:bg-gray-800/35 transition">
                                    <td class="p-3 border-r border-gray-800">{{ loop.index }}</td>
                                    <td class="p-3 border-r border-gray-800 text-gray-300">{{ c.date }}</td>
                                    <td class="p-3 border-r border-gray-800 font-bold text-indigo-400">{{ c.pay_to }}</td>
                                    <td class="p-3 border-r border-gray-800 text-gray-200">{{ c.description }}</td>
                                    <td class="p-3 border-r border-gray-800 font-bold text-emerald-400">₹{{ c.amount }}</td>
                                    <td class="p-3 border-r border-gray-800">
                                        {% if c.attachments %}
                                            <div class="flex flex-col space-y-1">
                                                {% for att in c.attachments %}
                                                <button onclick="openFileViewer('data:application/octet-stream;base64,{{ att.file_data }}', '{{ att.file_name }}')" class="text-indigo-400 underline hover:text-indigo-300 text-[10px] text-left">📎 {{ att.file_name[:15] }}...</button>
                                                {% endfor %}
                                            </div>
                                        {% else %}
                                            <span class="text-gray-500 text-[10px]">No Files</span>
                                        {% endif %}
                                    </td>
                                    <td class="p-3 text-center space-x-2 whitespace-nowrap">
                                        <button onclick='openEditCashModal({{ c|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-[10px] font-bold cursor-pointer">Edit</button>
                                        <a href="/delete/cash_expense/{{ c.id }}" onclick="return confirm('Confirm delete cash expense?');" class="text-red-400 bg-red-500/10 px-2 py-1 rounded text-[10px] font-bold inline-block">Delete</a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                            <tfoot>
                                <tr class="bg-gray-800/90 font-mono font-bold text-gray-200 border-t-2 border-gray-700">
                                    <td colspan="4" class="p-3 text-right uppercase tracking-wider text-emerald-400">Total Sum:</td>
                                    <td colspan="3" class="p-3 text-emerald-400">₹{{ filtered_total_cash_expenses }}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>
            {% endif %}
        </main>
    </div>

    <!-- Edit Attendance Modal -->
    <div id="editAttendanceModal" class="fixed inset-0 bg-black/70 hidden items-center justify-center z-50">
        <div class="bg-gray-900 border border-gray-800 p-6 rounded-2xl w-full max-w-lg">
            <h3 class="text-lg font-bold text-emerald-400 mb-4">Edit Attendance Record</h3>
            <form method="POST" class="grid grid-cols-2 gap-4">
                <input type="hidden" name="form_type" value="edit_attendance">
                <input type="hidden" name="id" id="edit_att_id">
                <div>
                    <label class="text-xs text-gray-400">Name</label>
                    <input type="text" name="name" id="edit_att_name" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Card Number</label>
                    <input type="text" name="card_number" id="edit_att_card" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Role</label>
                    <input type="text" name="role" id="edit_att_role" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">In Time</label>
                    <input type="text" name="in_time" id="edit_att_in" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Out Time</label>
                    <input type="text" name="out_time" id="edit_att_out" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Signature</label>
                    <input type="text" name="signature" id="edit_att_sig" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Amount</label>
                    <input type="number" name="amount" id="edit_att_amt" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Conveyance</label>
                    <input type="number" name="conveyance" id="edit_att_conv" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div class="col-span-2 flex justify-end space-x-2 mt-4">
                    <button type="button" onclick="closeModals()" class="px-4 py-2 bg-gray-800 text-gray-300 rounded-xl text-xs">Cancel</button>
                    <button type="submit" class="px-4 py-2 bg-emerald-500 text-gray-950 font-bold rounded-xl text-xs">Update</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Edit Cash Modal -->
    <div id="editCashModal" class="fixed inset-0 bg-black/70 hidden items-center justify-center z-50">
        <div class="bg-gray-900 border border-gray-800 p-6 rounded-2xl w-full max-w-lg">
            <h3 class="text-lg font-bold text-emerald-400 mb-4">Edit Cash Expense Record</h3>
            <form method="POST" enctype="multipart/form-data" class="grid grid-cols-2 gap-4">
                <input type="hidden" name="form_type" value="edit_cash_expense">
                <input type="hidden" name="id" id="edit_cash_id">
                <div>
                    <label class="text-xs text-gray-400">Date</label>
                    <input type="date" name="date" id="edit_cash_date" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Pay To</label>
                    <input type="text" name="pay_to" id="edit_cash_pay" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div class="col-span-2">
                    <label class="text-xs text-gray-400">Description</label>
                    <input type="text" name="description" id="edit_cash_desc" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Amount</label>
                    <input type="number" name="amount" id="edit_cash_amt" required class="w-full mt-1 p-2 bg-gray-800 rounded-xl border border-gray-700 text-xs text-white">
                </div>
                <div>
                    <label class="text-xs text-gray-400">Add More Files</label>
                    <input type="file" name="attachments" multiple accept=".pdf,image/*" class="w-full mt-1 p-1 bg-gray-800 rounded-xl border border-gray-700 text-[10px] text-gray-300">
                </div>
                <div class="col-span-2 flex justify-end space-x-2 mt-4">
                    <button type="button" onclick="closeModals()" class="px-4 py-2 bg-gray-800 text-gray-300 rounded-xl text-xs">Cancel</button>
                    <button type="submit" class="px-4 py-2 bg-emerald-500 text-gray-950 font-bold rounded-xl text-xs">Update</button>
                </div>
            </form>
        </div>
    </div>

    <!-- File Viewer Modal -->
    <div id="fileViewerModal" class="fixed inset-0 bg-black/70 hidden items-center justify-center z-50">
        <div class="bg-gray-900 border border-gray-800 p-4 rounded-2xl w-full max-w-2xl flex flex-col h-[80vh]">
            <div class="flex justify-between items-center mb-3">
                <h3 id="viewerFileName" class="text-sm font-bold text-emerald-400">Attachment Preview</h3>
                <button onclick="closeModals()" class="px-3 py-1 bg-gray-800 text-gray-300 rounded-lg text-xs font-bold">Close</button>
            </div>
            <div class="flex-1 bg-gray-950 rounded-xl overflow-hidden flex items-center justify-center border border-gray-800">
                <iframe id="viewerFrame" src="" class="w-full h-full border-0"></iframe>
            </div>
        </div>
    </div>

    <script>
        function openEditAttendanceModal(data) {
            document.getElementById('edit_att_id').value = data.id;
            document.getElementById('edit_att_name').value = data.name;
            document.getElementById('edit_att_card').value = data.card_number;
            document.getElementById('edit_att_role').value = data.role;
            document.getElementById('edit_att_in').value = data.in_time;
            document.getElementById('edit_att_out').value = data.out_time;
            document.getElementById('edit_att_sig').value = data.signature;
            document.getElementById('edit_att_amt').value = data.amount;
            document.getElementById('edit_att_conv').value = data.conveyance;
            document.getElementById('editAttendanceModal').classList.remove('hidden');
            document.getElementById('editAttendanceModal').classList.add('flex');
        }

        function openEditCashModal(data) {
            document.getElementById('edit_cash_id').value = data.id;
            document.getElementById('edit_cash_date').value = data.date;
            document.getElementById('edit_cash_pay').value = data.pay_to;
            document.getElementById('edit_cash_desc').value = data.description;
            document.getElementById('edit_cash_amt').value = data.amount;
            document.getElementById('editCashModal').classList.remove('hidden');
            document.getElementById('editCashModal').classList.add('flex');
        }

        function openFileViewer(dataUrl, fileName) {
            document.getElementById('viewerFileName').innerText = "Previewing: " + fileName;
            document.getElementById('viewerFrame').src = dataUrl;
            document.getElementById('fileViewerModal').classList.remove('hidden');
            document.getElementById('fileViewerModal').classList.add('flex');
        }

        function closeModals() {
            document.getElementById('editAttendanceModal').classList.add('hidden');
            document.getElementById('editCashModal').classList.add('hidden');
            document.getElementById('fileViewerModal').classList.add('hidden');
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True, port=5000)
