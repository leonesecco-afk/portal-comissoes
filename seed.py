from __future__ import annotations
from models import init_db, SessionLocal, User, Rule, Invoice
from werkzeug.security import generate_password_hash
from datetime import date
from rules import apply_commission_for_invoice

def run():
    init_db()
    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@pinho.com").one_or_none()
        if not admin:
            admin = User(name="Admin", email="admin@pinho.com", password_hash=generate_password_hash("admin123"), role="admin")
            db.add(admin)
        joao = db.query(User).filter_by(email="joao@pinho.com").one_or_none()
        if not joao:
            joao = User(name="João", email="joao@pinho.com", password_hash=generate_password_hash("123456"), role="consultant")
            db.add(joao)
        maria = db.query(User).filter_by(email="maria@pinho.com").one_or_none()
        if not maria:
            maria = User(name="Maria", email="maria@pinho.com", password_hash=generate_password_hash("123456"), role="consultant")
            db.add(maria)
        db.commit()
        if db.query(Rule).count()==0:
            db.add_all([
                Rule(consultant_id=None, client=None, service_type=None, rate=0.01, notes="Geral 1%"),
                Rule(consultant_id=joao.id, client=None, service_type="Importação", rate=0.02, notes="João Importação 2%"),
                Rule(consultant_id=None, client="Klabin", service_type=None, rate=0.015, notes="Klabin 1.5%"),
                Rule(consultant_id=maria.id, client="SSAB", service_type="Exportação", rate=0.03, notes="Maria+SSAB+Export 3%")
            ]); db.commit()
        if db.query(Invoice).count()==0:
            demo=[
                Invoice(invoice_number="N-1001", date=date(2025,9,1), client="Klabin", service_type="Importação", amount=100000.0, paid=True, consultant_id=joao.id),
                Invoice(invoice_number="N-1002", date=date(2025,9,2), client="SSAB", service_type="Exportação", amount=80000.0, paid=False, consultant_id=maria.id),
                Invoice(invoice_number="N-1003", date=date(2025,9,5), client="Bosch", service_type="Importação", amount=120000.0, paid=True, consultant_id=joao.id),
            ]
            db.add_all(demo); db.commit()
            for inv in db.query(Invoice).all():
                apply_commission_for_invoice(db, inv)
            db.commit()

if __name__ == "__main__":
    run()
