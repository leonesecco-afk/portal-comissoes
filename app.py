from __future__ import annotations
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select
from models import init_db, SessionLocal, User, Invoice, Rule
from rules import recompute_all, apply_commission_for_invoice
import pandas as pd
from io import BytesIO

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class LoginUser(UserMixin):
    def __init__(self, user: User):
        self.id = str(user.id)
        self.name = user.name
        self.email = user.email
        self.role = user.role

@login_manager.user_loader
def load_user(user_id):
    with SessionLocal() as db:
        u = db.get(User, int(user_id))
        return LoginUser(u) if u else None

@app.before_first_request
def setup():
    init_db()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with SessionLocal() as db:
            u = db.execute(select(User).where(User.email==email)).scalar_one_or_none()
            if u and check_password_hash(u.password_hash, password):
                login_user(LoginUser(u))
                session["user_id"] = u.id
                return redirect(url_for("dashboard"))
        flash("Credenciais inválidas.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); session.pop("user_id", None)
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with SessionLocal() as db:
        if current_user.role == "admin":
            total = db.query(Invoice).count()
            vals = db.query(Invoice.amount, Invoice.commission_value).all()
        else:
            total = db.query(Invoice).where(Invoice.consultant_id==int(current_user.id)).count()
            vals = db.query(Invoice.amount, Invoice.commission_value).where(Invoice.consultant_id==int(current_user.id)).all()
        total_valor = sum(x[0] for x in vals) if vals else 0.0
        total_comissao = sum(x[1] for x in vals) if vals else 0.0
    return render_template("dashboard.html", total=total, total_valor=total_valor, total_comissao=total_comissao)

@app.route("/invoices")
@login_required
def invoices():
    start = request.args.get("start")
    end = request.args.get("end")
    client = request.args.get("client","").strip()
    service = request.args.get("service","").strip()
    paid = request.args.get("paid")
    from models import Invoice
    with SessionLocal() as db:
        q = db.query(Invoice)
        if current_user.role != "admin":
            q = q.where(Invoice.consultant_id==int(current_user.id))
        if start:
            try: q = q.where(Invoice.date >= datetime.strptime(start,"%Y-%m-%d").date())
            except: pass
        if end:
            try: q = q.where(Invoice.date <= datetime.strptime(end,"%Y-%m-%d").date())
            except: pass
        if client: q = q.where(Invoice.client.ilike(f"%{client}%"))
        if service: q = q.where(Invoice.service_type.ilike(f"%{service}%"))
        if paid in ("0","1"): q = q.where(Invoice.paid==(paid=="1"))
        rows = q.order_by(Invoice.date.desc(), Invoice.invoice_number.desc()).all()
    return render_template("invoices.html", invoices=rows)

@app.route("/export")
@login_required
def export_csv():
    with SessionLocal() as db:
        q = db.query(Invoice)
        if current_user.role != "admin":
            q = q.where(Invoice.consultant_id==int(current_user.id))
        rows = q.order_by(Invoice.date.desc()).all()
        data = [{
            "Nota": r.invoice_number, "Data": r.date.isoformat(), "Cliente": r.client,
            "Serviço": r.service_type, "Valor": r.amount, "Pago": "Sim" if r.paid else "Não",
            "% Comissão": r.commission_rate, "Comissão": r.commission_value
        } for r in rows]
    df = pd.DataFrame(data); buf = BytesIO(); df.to_csv(buf, index=False, encoding="utf-8-sig"); buf.seek(0)
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="comissoes.csv")

@app.route("/admin/recompute")
@login_required
def admin_recompute():
    if current_user.role != "admin":
        flash("Acesso negado.", "danger"); return redirect(url_for("dashboard"))
    with SessionLocal() as db:
        recompute_all(db)
    flash("Recalculo concluído.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/import", methods=["GET","POST"])
@login_required
def admin_import():
    if current_user.role != "admin":
        flash("Acesso negado.", "danger"); return redirect(url_for("dashboard"))
    import pandas as pd
    if request.method == "POST":
        f = request.files.get("file")
        if not f: flash("Envie um CSV.", "danger"); return redirect(url_for("admin_import"))
        df = pd.read_csv(f)
        required = {"invoice_number","date","client","service_type","amount","paid","consultant_email"}
        if not required.issubset(set(c.lower() for c in df.columns)):
            flash("Cabeçalhos esperados: invoice_number,date,client,service_type,amount,paid,consultant_email", "danger")
            return redirect(url_for("admin_import"))
        from werkzeug.security import generate_password_hash
        with SessionLocal() as db:
            users = {u.email.lower(): u for u in db.query(User).all()}
            created, updated = 0, 0
            for _, row in df.iterrows():
                invn = str(row["invoice_number"]).strip()
                d = pd.to_datetime(row["date"]).date()
                client = str(row["client"]).strip()
                service = str(row["service_type"]).strip()
                amount = float(row["amount"])
                paid = str(row["paid"]).strip().lower() in ("1","true","sim","yes","y")
                email = str(row["consultant_email"]).strip().lower()
                user = users.get(email)
                if not user:
                    user = User(name=email.split("@")[0].title(), email=email, password_hash=generate_password_hash("123456"), role="consultant")
                    db.add(user); db.flush(); users[email]=user
                inv = db.query(Invoice).where(Invoice.invoice_number==invn).one_or_none()
                if not inv:
                    inv = Invoice(invoice_number=invn, date=d, client=client, service_type=service, amount=amount, paid=paid, consultant_id=user.id)
                    db.add(inv); created += 1
                else:
                    inv.date=d; inv.client=client; inv.service_type=service; inv.amount=amount; inv.paid=paid; inv.consultant_id=user.id; updated += 1
                apply_commission_for_invoice(db, inv)
            db.commit()
        flash(f"Importação: {created} criados, {updated} atualizados.", "success")
        return redirect(url_for("dashboard"))
    return render_template("admin_import.html")

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == "__main__":
    app.run(debug=True)
