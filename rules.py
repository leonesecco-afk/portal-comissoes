from __future__ import annotations
from typing import List, Optional
from models import Rule, Invoice
def pick_rule(rules: List[Rule], invoice: Invoice) -> Optional[Rule]:
    def score(rule: Rule) -> int:
        s=0
        if rule.consultant_id is not None: s+=1
        if rule.client: s+=1
        if rule.service_type: s+=1
        return s
    applicable = []
    for r in rules:
        if not r.active: continue
        if r.consultant_id is not None and r.consultant_id != invoice.consultant_id: continue
        if r.client and r.client.strip().lower() != invoice.client.strip().lower(): continue
        if r.service_type and r.service_type.strip().lower() != invoice.service_type.strip().lower(): continue
        applicable.append(r)
    if not applicable: return None
    applicable.sort(key=lambda x: (-score(x), x.id))
    return applicable[0]
def apply_commission_for_invoice(db, invoice: Invoice):
    rules = db.query(Rule).filter(Rule.active==True).all()
    r = pick_rule(rules, invoice)
    if r:
        invoice.commission_rate = r.rate
        invoice.commission_value = round(invoice.amount * r.rate, 2)
    else:
        invoice.commission_rate = 0.0
        invoice.commission_value = 0.0
    db.add(invoice)
def recompute_all(db):
    for inv in db.query(Invoice).all():
        apply_commission_for_invoice(db, inv)
    db.commit()
