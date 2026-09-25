from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
DB = "garuda.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT, email TEXT);
    CREATE TABLE IF NOT EXISTS vehicles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE, number TEXT NOT NULL,
        model TEXT, year INTEGER);
    CREATE TABLE IF NOT EXISTS services(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE, service_date TEXT NOT NULL,
        next_service TEXT NOT NULL, service_type TEXT,
        amount REAL DEFAULT 0, notes TEXT);
    """)
    if con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        con.execute("INSERT INTO customers(name,phone,email) VALUES(?,?,?)",
                    ("Rahul Sharma","9876543210","rahul@example.com"))
        con.execute("INSERT INTO customers(name,phone,email) VALUES(?,?,?)",
                    ("Priya Patel","9876501234","priya@example.com"))
        c1 = con.execute("SELECT id FROM customers WHERE name='Rahul Sharma'").fetchone()[0]
        c2 = con.execute("SELECT id FROM customers WHERE name='Priya Patel'").fetchone()[0]
        con.execute("INSERT INTO vehicles(customer_id,number,model,year) VALUES(?,?,?,?)",
                    (c1,"GJ01AB1234","Honda City",2022))
        con.execute("INSERT INTO vehicles(customer_id,number,model,year) VALUES(?,?,?,?)",
                    (c2,"GJ05CD5678","Hyundai i20",2021))
        v1 = con.execute("SELECT id FROM vehicles WHERE number='GJ01AB1234'").fetchone()[0]
        v2 = con.execute("SELECT id FROM vehicles WHERE number='GJ05CD5678'").fetchone()[0]
        con.execute("""INSERT INTO services
            (vehicle_id,service_date,next_service,service_type,amount,notes)
            VALUES(?,?,?,?,?,?)""",
            (v1,"2026-09-10","2026-10-10","Regular Service",2500,"Oil and filter check"))
        con.execute("""INSERT INTO services
            (vehicle_id,service_date,next_service,service_type,amount,notes)
            VALUES(?,?,?,?,?,?)""",
            (v2,"2026-08-20","2026-09-28","General Service",1800,"Brake inspection"))
    con.commit()
    con.close()

@app.route("/")
def dashboard():
    con = db()
    customers = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    vehicles = con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    services = con.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    revenue = con.execute("SELECT COALESCE(SUM(amount),0) FROM services").fetchone()[0]
    upcoming = con.execute("""
        SELECT s.*,v.number,v.model,c.name FROM services s
        JOIN vehicles v ON s.vehicle_id=v.id JOIN customers c ON v.customer_id=c.id
        WHERE date(s.next_service)<=date('now','+15 day')
        ORDER BY date(s.next_service)""").fetchall()
    con.close()
    return render_template("dashboard.html", customers=customers, vehicles=vehicles,
                           services=services, revenue=revenue, upcoming=upcoming)

@app.route("/customers", methods=["GET","POST"])
def customers():
    con = db()
    if request.method == "POST":
        con.execute("INSERT INTO customers(name,phone,email) VALUES(?,?,?)",
                    (request.form["name"],request.form["phone"],request.form["email"]))
        con.commit(); con.close()
        return redirect(url_for("customers"))
    rows = con.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    con.close()
    return render_template("customers.html", customers=rows)

@app.route("/vehicles", methods=["GET","POST"])
def vehicles():
    con = db()
    if request.method == "POST":
        con.execute("""INSERT INTO vehicles(customer_id,number,model,year)
                       VALUES(?,?,?,?)""",
                    (request.form["customer_id"],request.form["number"],
                     request.form["model"],request.form["year"] or None))
        con.commit(); con.close()
        return redirect(url_for("vehicles"))
    rows = con.execute("""SELECT v.*,c.name customer FROM vehicles v
                          JOIN customers c ON v.customer_id=c.id
                          ORDER BY v.id DESC""").fetchall()
    cust = con.execute("SELECT * FROM customers ORDER BY name").fetchall()
    con.close()
    return render_template("vehicles.html", vehicles=rows, customers=cust)

@app.route("/services", methods=["GET","POST"])
def services():
    con = db()
    if request.method == "POST":
        con.execute("""INSERT INTO services
            (vehicle_id,service_date,next_service,service_type,amount,notes)
            VALUES(?,?,?,?,?,?)""",
            (request.form["vehicle_id"],request.form["service_date"],
             request.form["next_service"],request.form["service_type"],
             request.form["amount"] or 0,request.form["notes"]))
        con.commit(); con.close()
        return redirect(url_for("services"))
    rows = con.execute("""SELECT s.*,v.number,c.name customer FROM services s
                          JOIN vehicles v ON s.vehicle_id=v.id
                          JOIN customers c ON v.customer_id=c.id
                          ORDER BY date(s.service_date) DESC""").fetchall()
    veh = con.execute("""SELECT v.id,v.number,c.name customer FROM vehicles v
                         JOIN customers c ON v.customer_id=c.id
                         ORDER BY v.number""").fetchall()
    con.close()
    return render_template("services.html", services=rows, vehicles=veh)

@app.post("/customers/delete/<int:customer_id>")
def delete_customer(customer_id):
    con = db()
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    con.commit()
    con.close()
    return redirect(url_for("customers"))

@app.post("/vehicles/delete/<int:vehicle_id>")
def delete_vehicle(vehicle_id):
    con = db()
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
    con.commit()
    con.close()
    return redirect(url_for("vehicles"))

@app.post("/services/delete/<int:service_id>")
def delete_service(service_id):
    con = db()
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("DELETE FROM services WHERE id = ?", (service_id,))
    con.commit()
    con.close()
    return redirect(url_for("services"))

@app.route("/analytics")
def analytics():
    con = db()
    monthly = con.execute("""SELECT substr(service_date,1,7) month,
        COUNT(*) count,COALESCE(SUM(amount),0) revenue
        FROM services GROUP BY month ORDER BY month""").fetchall()
    types = con.execute("""SELECT service_type,COUNT(*) count
        FROM services GROUP BY service_type ORDER BY count DESC""").fetchall()
    con.close()
    return render_template("analytics.html", monthly=monthly, types=types)

@app.route("/retention")
def retention():
    con = db()
    rows = con.execute("""SELECT c.id,c.name,c.phone,c.email,
        COUNT(s.id) service_count,MAX(s.service_date) last_service
        FROM customers c LEFT JOIN vehicles v ON c.id=v.customer_id
        LEFT JOIN services s ON v.id=s.vehicle_id GROUP BY c.id
        ORDER BY last_service""").fetchall()
    con.close()
    result=[]
    for r in rows:
        last=r["last_service"]
        status="At Risk" if not last or (date.today()-datetime.strptime(last,"%Y-%m-%d").date()).days>45 else "Active"
        result.append({**dict(r),"status":status})
    return render_template("retention.html", customers=result)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
