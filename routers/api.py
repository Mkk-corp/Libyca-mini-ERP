"""
API Router — JSON endpoints للتطبيق Flutter
كل endpoint يرجع JSON بدلاً من HTML
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, datetime
from typing import Optional

from database import (get_db, Purchase, Sale, Expense, Employee, Payroll,
                      Item, Supplier, Customer, Hakiya, Warshfana,
                      Note, Todo, ExpenseCategory, PriceBoard, Custody)

router = APIRouter(prefix="/api", tags=["API"])


def to_dict(obj, exclude=None):
    """تحويل SQLAlchemy object لـ dict"""
    exclude = exclude or []
    result = {}
    for c in obj.__table__.columns:
        if c.name in exclude:
            continue
        val = getattr(obj, c.name)
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        result[c.name] = val
    return result


# ══════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════
@router.get("/dashboard")
def api_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    m, y = today.month, today.year

    def month_sum(model, col):
        return db.query(func.sum(col)).filter(
            extract('month', model.date) == m,
            extract('year', model.date) == y
        ).scalar() or 0

    purchases_m  = month_sum(Purchase, Purchase.amount_lyd)
    sales_m      = month_sum(Sale, Sale.amount_lyd)
    expenses_m   = month_sum(Expense, Expense.amount_lyd)
    cogs_m       = month_sum(Sale, Sale.cogs)
    gross_profit = sales_m - cogs_m
    net_profit   = gross_profit - expenses_m

    recent_purchases = db.query(Purchase).order_by(Purchase.date.desc()).limit(5).all()
    recent_sales     = db.query(Sale).order_by(Sale.date.desc()).limit(5).all()
    recent_expenses  = db.query(Expense).order_by(Expense.date.desc()).limit(5).all()

    return {
        "month": m, "year": y,
        "purchases_total": round(purchases_m, 2),
        "sales_total": round(sales_m, 2),
        "expenses_total": round(expenses_m, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "recent_purchases": [to_dict(r) for r in recent_purchases],
        "recent_sales": [to_dict(r) for r in recent_sales],
        "recent_expenses": [to_dict(r) for r in recent_expenses],
    }


# ══════════════════════════════════════
#  PURCHASES
# ══════════════════════════════════════
@router.get("/purchases")
def api_purchases(
    page: int = 1,
    per_page: int = 20,
    item_name: Optional[str] = None,
    supplier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Purchase).order_by(Purchase.date.desc())
    if item_name:
        q = q.filter(Purchase.item_name.contains(item_name))
    if supplier:
        q = q.filter(Purchase.supplier_name.contains(supplier))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [to_dict(r) for r in items]
    }

@router.get("/purchases/{pid}")
def api_purchase_detail(pid: int, db: Session = Depends(get_db)):
    r = db.query(Purchase).filter(Purchase.id == pid).first()
    if not r:
        raise HTTPException(404, "غير موجود")
    return to_dict(r)

@router.post("/purchases")
def api_purchase_create(data: dict, db: Session = Depends(get_db)):
    r = Purchase(**{k: v for k, v in data.items() if k != 'id'})
    db.add(r); db.commit(); db.refresh(r)
    return to_dict(r)

@router.delete("/purchases/{pid}")
def api_purchase_delete(pid: int, db: Session = Depends(get_db)):
    r = db.query(Purchase).filter(Purchase.id == pid).first()
    if not r:
        raise HTTPException(404, "غير موجود")
    db.delete(r); db.commit()
    return {"success": True}


# ══════════════════════════════════════
#  SALES
# ══════════════════════════════════════
@router.get("/sales")
def api_sales(
    page: int = 1, per_page: int = 20,
    item_name: Optional[str] = None,
    customer: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Sale).order_by(Sale.date.desc())
    if item_name:
        q = q.filter(Sale.item_name.contains(item_name))
    if customer:
        q = q.filter(Sale.customer_name.contains(customer))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [to_dict(r) for r in items]
    }

@router.get("/sales/{sid}")
def api_sale_detail(sid: int, db: Session = Depends(get_db)):
    r = db.query(Sale).filter(Sale.id == sid).first()
    if not r: raise HTTPException(404, "غير موجود")
    return to_dict(r)

@router.post("/sales")
def api_sale_create(data: dict, db: Session = Depends(get_db)):
    r = Sale(**{k: v for k, v in data.items() if k != 'id'})
    db.add(r); db.commit(); db.refresh(r)
    return to_dict(r)

@router.delete("/sales/{sid}")
def api_sale_delete(sid: int, db: Session = Depends(get_db)):
    r = db.query(Sale).filter(Sale.id == sid).first()
    if not r: raise HTTPException(404, "غير موجود")
    db.delete(r); db.commit()
    return {"success": True}


# ══════════════════════════════════════
#  EXPENSES
# ══════════════════════════════════════
@router.get("/expenses")
def api_expenses(
    page: int = 1, per_page: int = 20,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Expense).order_by(Expense.date.desc())
    if category_id:
        q = q.filter(Expense.category_id == category_id)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [to_dict(r) for r in items]
    }

@router.post("/expenses")
def api_expense_create(data: dict, db: Session = Depends(get_db)):
    r = Expense(**{k: v for k, v in data.items() if k != 'id'})
    db.add(r); db.commit(); db.refresh(r)
    return to_dict(r)

@router.delete("/expenses/{eid}")
def api_expense_delete(eid: int, db: Session = Depends(get_db)):
    r = db.query(Expense).filter(Expense.id == eid).first()
    if not r: raise HTTPException(404, "غير موجود")
    db.delete(r); db.commit()
    return {"success": True}

@router.get("/expense-categories")
def api_expense_categories(db: Session = Depends(get_db)):
    cats = db.query(ExpenseCategory).all()
    return [to_dict(c) for c in cats]


# ══════════════════════════════════════
#  EMPLOYEES & PAYROLL
# ══════════════════════════════════════
@router.get("/employees")
def api_employees(db: Session = Depends(get_db)):
    items = db.query(Employee).order_by(Employee.name).all()
    return [to_dict(r) for r in items]

@router.get("/payroll")
def api_payroll(page: int = 1, per_page: int = 20, db: Session = Depends(get_db)):
    q = db.query(Payroll).order_by(Payroll.date.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [to_dict(r) for r in items]
    }


# ══════════════════════════════════════
#  ITEMS / SUPPLIERS / CUSTOMERS
# ══════════════════════════════════════
@router.get("/items")
def api_items(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(Item).order_by(Item.name).all()]

@router.get("/suppliers")
def api_suppliers(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(Supplier).order_by(Supplier.name).all()]

@router.get("/customers")
def api_customers(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(Customer).order_by(Customer.name).all()]


# ══════════════════════════════════════
#  HAKIYA
# ══════════════════════════════════════
@router.get("/hakiya")
def api_hakiya(db: Session = Depends(get_db)):
    items = db.query(Hakiya).order_by(Hakiya.date.asc()).all()
    data = [to_dict(r) for r in items]
    total_profit = sum(r.profit or 0 for r in items)
    return {"total_profit": round(total_profit, 2), "data": data}


# ══════════════════════════════════════
#  WARSHFANA
# ══════════════════════════════════════
@router.get("/warshfana")
def api_warshfana(db: Session = Depends(get_db)):
    items = db.query(Warshfana).order_by(Warshfana.date.asc()).all()
    total_remaining = sum(r.remaining or 0 for r in items)
    return {"total_remaining": round(total_remaining, 2), "data": [to_dict(r) for r in items]}


# ══════════════════════════════════════
#  NOTES & TODOS
# ══════════════════════════════════════
@router.get("/notes")
def api_notes(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(Note).order_by(Note.created_at.desc()).all()]

@router.post("/notes")
def api_note_create(data: dict, db: Session = Depends(get_db)):
    r = Note(**{k: v for k, v in data.items() if k != 'id'})
    db.add(r); db.commit(); db.refresh(r)
    return to_dict(r)

@router.delete("/notes/{nid}")
def api_note_delete(nid: int, db: Session = Depends(get_db)):
    r = db.query(Note).filter(Note.id == nid).first()
    if not r: raise HTTPException(404, "غير موجود")
    db.delete(r); db.commit()
    return {"success": True}

@router.get("/todos")
def api_todos(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(Todo).order_by(Todo.created_at.desc()).all()]

@router.post("/todos")
def api_todo_create(data: dict, db: Session = Depends(get_db)):
    r = Todo(**{k: v for k, v in data.items() if k != 'id'})
    db.add(r); db.commit(); db.refresh(r)
    return to_dict(r)

@router.put("/todos/{tid}")
def api_todo_toggle(tid: int, db: Session = Depends(get_db)):
    r = db.query(Todo).filter(Todo.id == tid).first()
    if not r: raise HTTPException(404, "غير موجود")
    r.done = not r.done
    db.commit()
    return to_dict(r)

@router.delete("/todos/{tid}")
def api_todo_delete(tid: int, db: Session = Depends(get_db)):
    r = db.query(Todo).filter(Todo.id == tid).first()
    if not r: raise HTTPException(404, "غير موجود")
    db.delete(r); db.commit()
    return {"success": True}


# ══════════════════════════════════════
#  PRICE BOARD & CUSTODY
# ══════════════════════════════════════
@router.get("/prices")
def api_prices(db: Session = Depends(get_db)):
    return [to_dict(r) for r in db.query(PriceBoard).order_by(PriceBoard.date.desc()).all()]

@router.get("/custody")
def api_custody(db: Session = Depends(get_db)):
    items = db.query(Custody).order_by(Custody.date.desc()).all()
    total = sum((r.amount or 0) for r in items)
    return {"total": round(total, 2), "data": [to_dict(r) for r in items]}
