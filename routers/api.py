"""
REST API Router — JSON endpoints for Flutter / mobile clients
All responses follow: {"status": "success", "data": ..., "meta": {...}}
Web routes in app.py are untouched.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from database import (
    get_db, Setting, Purchase, Sale, Expense, Employee, Payroll,
    Item, Supplier, Customer, Hakiya, Warshfana,
    Note, Todo, ExpenseCategory, PriceBoard, Custody,
)

router = APIRouter(prefix="/api", tags=["API"])

CATS = {
    1: 'نقل', 2: 'ديزل/وقود', 3: 'عمالة', 4: 'صيانة', 5: 'كهرباء',
    6: 'مياه', 7: 'إيجار', 8: 'اتصالات', 9: 'مصاريف إدارية', 10: 'أخرى',
    11: 'مقدم بضاعة', 12: 'شوالات', 13: 'مطبخ',
}


# ── Shared helpers ───────────────────────────────────────────

def to_dict(obj, exclude=None):
    """Convert a SQLAlchemy row to a JSON-serialisable dict."""
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


def ok(data):
    return {"status": "success", "data": data}


def paginated(data, total, page, pages, **extra_meta):
    return {
        "status": "success",
        "data": data,
        "meta": {"total": total, "page": page, "pages": pages, **extra_meta},
    }


def _paginate(query, page: int, per_page: int):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, (total + per_page - 1) // per_page)
    return items, total, pages


def _next_ref(db: Session, model, prefix: str) -> str:
    last = db.query(model).order_by(model.id.desc()).first()
    num = 1
    if last and getattr(last, "ref_no", None):
        try:
            num = int(last.ref_no.replace(prefix, "").lstrip("0") or "0") + 1
        except Exception:
            pass
    return f"{prefix}{num:06d}"


def _parse_date(s: Optional[str]) -> Optional[date]:
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def _apply_month(query, model, month: str):
    if month:
        y, m = month.split("-")
        query = query.filter(
            extract("year", model.date) == int(y),
            extract("month", model.date) == int(m),
        )
    return query


# ── Pydantic request schemas ─────────────────────────────────

class ItemIn(BaseModel):
    code: str
    name: str
    category: str = ""
    notes: str = ""
    active: bool = True


class SupplierIn(BaseModel):
    code: str
    name: str
    phone: str = ""
    city: str = ""
    notes: str = ""
    active: bool = True


class CustomerIn(BaseModel):
    code: str
    name: str
    phone: str = ""
    city: str = ""
    notes: str = ""
    active: bool = True


class EmployeeIn(BaseModel):
    code: str
    name: str
    department: str = ""
    hire_date: Optional[str] = None
    basic_salary: float = 0
    shift_salary: float = 0
    fixed_deductions: float = 0
    payment_method: str = ""
    active: bool = True


class PurchaseIn(BaseModel):
    ref_no: Optional[str] = None
    date: str
    supplier_name: str
    item_name: str
    item_code: str = ""
    gross_weight: float = 0
    tare_weight: float = 0
    net_weight: float = 0
    unit_price: float = 0
    amount_lyd: float = 0
    payment_method: str = ""
    paid: float = 0
    notes: str = ""


class SaleIn(BaseModel):
    ref_no: Optional[str] = None
    date: str
    customer_name: str
    item_name: str
    item_code: str = ""
    quantity: float = 0
    unit_price: float = 0
    amount_lyd: float = 0
    cogs: float = 0
    payment_method: str = ""
    paid: float = 0
    notes: str = ""


class ExpenseIn(BaseModel):
    date: str
    category_id: int
    description: str
    amount_lyd: float = 0
    payment_method: str = ""
    notes: str = ""


class PayrollIn(BaseModel):
    pay_date: str
    month: str
    employee_name: str
    basic_salary: float = 0
    allowances: float = 0
    overtime: float = 0
    deductions: float = 0
    payment_method: str = ""


class HakiyaIn(BaseModel):
    date: str
    type: str
    quantity: float = 0
    buy_price: float = 0
    sell_price: float = 0
    notes: str = ""


class WarshfanaIn(BaseModel):
    date: Optional[str] = None
    item_type: str
    weight: float = 0
    price_per_kg: float = 0
    total: float = 0
    driver_discount: float = 0
    paid: float = 0
    notes: str = ""


class PriceIn(BaseModel):
    date: str
    item_code: str
    item_name: str
    buy_price: float = 0
    sell_price: float = 0


class CustodyIn(BaseModel):
    date: str
    description: str
    amount: float = 0
    notes: str = ""


class NoteIn(BaseModel):
    title: str
    content: str = ""
    color: str = "yellow"


class TodoIn(BaseModel):
    task: str
    priority: str = "normal"
    due_date: Optional[str] = None


# ══════════════════════════════════════
#  DASHBOARD  GET /api/dashboard
# ══════════════════════════════════════

@router.get("/dashboard")
def api_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    m, y = today.month, today.year

    def ms(model, col):
        return db.query(func.sum(col)).filter(
            extract("month", model.date) == m,
            extract("year", model.date) == y,
        ).scalar() or 0

    purchases_m  = ms(Purchase, Purchase.amount_lyd)
    sales_m      = ms(Sale, Sale.amount_lyd)
    expenses_m   = ms(Expense, Expense.amount_lyd)
    cogs_m       = ms(Sale, Sale.cogs)
    gross_profit = sales_m - cogs_m
    net_profit   = gross_profit - expenses_m

    trend = []
    for i in range(5, -1, -1):
        mo = (m - i - 1) % 12 + 1
        yr = y if m - i > 0 else y - 1
        s = db.query(func.sum(Sale.amount_lyd)).filter(
            extract("month", Sale.date) == mo, extract("year", Sale.date) == yr
        ).scalar() or 0
        p = db.query(func.sum(Purchase.amount_lyd)).filter(
            extract("month", Purchase.date) == mo, extract("year", Purchase.date) == yr
        ).scalar() or 0
        trend.append({"month": f"{mo}/{yr}", "sales": round(s, 2), "purchases": round(p, 2)})

    exp_cats = [
        {"category": row[0], "total": round(row[1] or 0, 2)}
        for row in db.query(Expense.category_name, func.sum(Expense.amount_lyd)).filter(
            extract("month", Expense.date) == m, extract("year", Expense.date) == y
        ).group_by(Expense.category_name).all()
    ]

    return ok({
        "month": m, "year": y,
        "purchases_total":  round(purchases_m,  2),
        "sales_total":      round(sales_m,      2),
        "expenses_total":   round(expenses_m,   2),
        "gross_profit":     round(gross_profit, 2),
        "net_profit":       round(net_profit,   2),
        "trend":            trend,
        "expenses_by_category": exp_cats,
        "recent_purchases": [to_dict(r) for r in db.query(Purchase).order_by(Purchase.date.desc()).limit(5).all()],
        "recent_sales":     [to_dict(r) for r in db.query(Sale).order_by(Sale.date.desc()).limit(5).all()],
    })


# ══════════════════════════════════════
#  ITEMS  /api/items
# ══════════════════════════════════════

@router.get("/items")
def api_items_list(q: str = "", active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Item)
    if q:
        query = query.filter(Item.name.contains(q) | Item.code.contains(q))
    if active_only:
        query = query.filter(Item.active == True)
    return ok([to_dict(r) for r in query.order_by(Item.name).all()])


@router.get("/items/{item_id}")
def api_item_detail(item_id: int, db: Session = Depends(get_db)):
    r = db.query(Item).get(item_id)
    if not r:
        raise HTTPException(404, "الصنف غير موجود")
    return ok(to_dict(r))


@router.post("/items", status_code=201)
def api_item_create(body: ItemIn, db: Session = Depends(get_db)):
    r = Item(**body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/items/{item_id}")
def api_item_update(item_id: int, body: ItemIn, db: Session = Depends(get_db)):
    r = db.query(Item).get(item_id)
    if not r:
        raise HTTPException(404, "الصنف غير موجود")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/items/{item_id}")
def api_item_delete(item_id: int, db: Session = Depends(get_db)):
    r = db.query(Item).get(item_id)
    if not r:
        raise HTTPException(404, "الصنف غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": item_id})


# ══════════════════════════════════════
#  SUPPLIERS  /api/suppliers
# ══════════════════════════════════════

@router.get("/suppliers")
def api_suppliers_list(q: str = "", active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Supplier)
    if q:
        query = query.filter(Supplier.name.contains(q))
    if active_only:
        query = query.filter(Supplier.active == True)
    return ok([to_dict(r) for r in query.order_by(Supplier.name).all()])


@router.get("/suppliers/{sid}")
def api_supplier_detail(sid: int, db: Session = Depends(get_db)):
    r = db.query(Supplier).get(sid)
    if not r:
        raise HTTPException(404, "المورد غير موجود")
    return ok(to_dict(r))


@router.post("/suppliers", status_code=201)
def api_supplier_create(body: SupplierIn, db: Session = Depends(get_db)):
    r = Supplier(**body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/suppliers/{sid}")
def api_supplier_update(sid: int, body: SupplierIn, db: Session = Depends(get_db)):
    r = db.query(Supplier).get(sid)
    if not r:
        raise HTTPException(404, "المورد غير موجود")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/suppliers/{sid}")
def api_supplier_delete(sid: int, db: Session = Depends(get_db)):
    r = db.query(Supplier).get(sid)
    if not r:
        raise HTTPException(404, "المورد غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": sid})


# ══════════════════════════════════════
#  CUSTOMERS  /api/customers
# ══════════════════════════════════════

@router.get("/customers")
def api_customers_list(q: str = "", active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Customer)
    if q:
        query = query.filter(Customer.name.contains(q))
    if active_only:
        query = query.filter(Customer.active == True)
    return ok([to_dict(r) for r in query.order_by(Customer.name).all()])


@router.get("/customers/{cid}")
def api_customer_detail(cid: int, db: Session = Depends(get_db)):
    r = db.query(Customer).get(cid)
    if not r:
        raise HTTPException(404, "العميل غير موجود")
    return ok(to_dict(r))


@router.post("/customers", status_code=201)
def api_customer_create(body: CustomerIn, db: Session = Depends(get_db)):
    r = Customer(**body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/customers/{cid}")
def api_customer_update(cid: int, body: CustomerIn, db: Session = Depends(get_db)):
    r = db.query(Customer).get(cid)
    if not r:
        raise HTTPException(404, "العميل غير موجود")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/customers/{cid}")
def api_customer_delete(cid: int, db: Session = Depends(get_db)):
    r = db.query(Customer).get(cid)
    if not r:
        raise HTTPException(404, "العميل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": cid})


# ══════════════════════════════════════
#  EMPLOYEES  /api/employees
# ══════════════════════════════════════

@router.get("/employees")
def api_employees_list(q: str = "", active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Employee)
    if q:
        query = query.filter(Employee.name.contains(q) | Employee.department.contains(q))
    if active_only:
        query = query.filter(Employee.active == True)
    return ok([to_dict(r) for r in query.order_by(Employee.name).all()])


@router.get("/employees/{eid}")
def api_employee_detail(eid: int, db: Session = Depends(get_db)):
    r = db.query(Employee).get(eid)
    if not r:
        raise HTTPException(404, "الموظف غير موجود")
    return ok(to_dict(r))


@router.post("/employees", status_code=201)
def api_employee_create(body: EmployeeIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["hire_date"] = _parse_date(data.get("hire_date"))
    r = Employee(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/employees/{eid}")
def api_employee_update(eid: int, body: EmployeeIn, db: Session = Depends(get_db)):
    r = db.query(Employee).get(eid)
    if not r:
        raise HTTPException(404, "الموظف غير موجود")
    data = body.model_dump()
    data["hire_date"] = _parse_date(data.get("hire_date"))
    for k, v in data.items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/employees/{eid}")
def api_employee_delete(eid: int, db: Session = Depends(get_db)):
    r = db.query(Employee).get(eid)
    if not r:
        raise HTTPException(404, "الموظف غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": eid})


# ══════════════════════════════════════
#  PURCHASES  /api/purchases
# ══════════════════════════════════════

@router.get("/purchases")
def api_purchases_list(
    page: int = 1, per_page: int = 20,
    q: str = "", month: str = "", item_name: str = "", supplier: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Purchase).order_by(Purchase.date.desc())
    if q:
        query = query.filter(Purchase.supplier_name.contains(q) | Purchase.item_name.contains(q))
    query = _apply_month(query, Purchase, month)
    if item_name:
        query = query.filter(Purchase.item_name.contains(item_name))
    if supplier:
        query = query.filter(Purchase.supplier_name.contains(supplier))
    total_amount = query.with_entities(func.sum(Purchase.amount_lyd)).scalar() or 0
    items, total, pages = _paginate(query, page, per_page)
    return paginated(
        [to_dict(r) for r in items], total, page, pages,
        total_amount=round(total_amount, 2),
    )


@router.get("/purchases/{pid}")
def api_purchase_detail(pid: int, db: Session = Depends(get_db)):
    r = db.query(Purchase).get(pid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    return ok(to_dict(r))


@router.post("/purchases", status_code=201)
def api_purchase_create(body: PurchaseIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"]      = _parse_date(data["date"])
    data["ref_no"]    = data["ref_no"] or _next_ref(db, Purchase, "ش")
    data["amount"]    = data["amount_lyd"]
    data["remaining"] = data["amount_lyd"] - data["paid"]
    r = Purchase(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/purchases/{pid}")
def api_purchase_update(pid: int, body: PurchaseIn, db: Session = Depends(get_db)):
    r = db.query(Purchase).get(pid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    data = body.model_dump()
    data["date"]      = _parse_date(data["date"])
    data["amount"]    = data["amount_lyd"]
    data["remaining"] = data["amount_lyd"] - data["paid"]
    for k, v in data.items():
        if k == "ref_no" and not v:
            continue
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/purchases/{pid}")
def api_purchase_delete(pid: int, db: Session = Depends(get_db)):
    r = db.query(Purchase).get(pid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": pid})


# ══════════════════════════════════════
#  SALES  /api/sales
# ══════════════════════════════════════

@router.get("/sales")
def api_sales_list(
    page: int = 1, per_page: int = 20,
    q: str = "", month: str = "", item_name: str = "", customer: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Sale).order_by(Sale.date.desc())
    if q:
        query = query.filter(Sale.customer_name.contains(q) | Sale.item_name.contains(q))
    query = _apply_month(query, Sale, month)
    if item_name:
        query = query.filter(Sale.item_name.contains(item_name))
    if customer:
        query = query.filter(Sale.customer_name.contains(customer))
    total_amount = query.with_entities(func.sum(Sale.amount_lyd)).scalar() or 0
    total_profit = query.with_entities(func.sum(Sale.gross_profit)).scalar() or 0
    items, total, pages = _paginate(query, page, per_page)
    return paginated(
        [to_dict(r) for r in items], total, page, pages,
        total_amount=round(total_amount, 2),
        total_profit=round(total_profit, 2),
    )


@router.get("/sales/{sid}")
def api_sale_detail(sid: int, db: Session = Depends(get_db)):
    r = db.query(Sale).get(sid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    return ok(to_dict(r))


@router.post("/sales", status_code=201)
def api_sale_create(body: SaleIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"]         = _parse_date(data["date"])
    data["ref_no"]       = data["ref_no"] or _next_ref(db, Sale, "ب")
    data["amount"]       = data["amount_lyd"]
    data["gross_profit"] = data["amount_lyd"] - data["cogs"]
    data["remaining"]    = data["amount_lyd"] - data["paid"]
    r = Sale(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/sales/{sid}")
def api_sale_update(sid: int, body: SaleIn, db: Session = Depends(get_db)):
    r = db.query(Sale).get(sid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    data = body.model_dump()
    data["date"]         = _parse_date(data["date"])
    data["amount"]       = data["amount_lyd"]
    data["gross_profit"] = data["amount_lyd"] - data["cogs"]
    data["remaining"]    = data["amount_lyd"] - data["paid"]
    for k, v in data.items():
        if k == "ref_no" and not v:
            continue
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/sales/{sid}")
def api_sale_delete(sid: int, db: Session = Depends(get_db)):
    r = db.query(Sale).get(sid)
    if not r:
        raise HTTPException(404, "الفاتورة غير موجودة")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": sid})


# ══════════════════════════════════════
#  EXPENSES  /api/expenses
# ══════════════════════════════════════

@router.get("/expenses")
def api_expenses_list(
    page: int = 1, per_page: int = 20,
    q: str = "", month: str = "", category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Expense).order_by(Expense.date.desc())
    if q:
        query = query.filter(Expense.description.contains(q))
    query = _apply_month(query, Expense, month)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    total_amount = query.with_entities(func.sum(Expense.amount_lyd)).scalar() or 0
    items, total, pages = _paginate(query, page, per_page)
    return paginated(
        [to_dict(r) for r in items], total, page, pages,
        total_amount=round(total_amount, 2),
    )


@router.get("/expenses/{eid}")
def api_expense_detail(eid: int, db: Session = Depends(get_db)):
    r = db.query(Expense).get(eid)
    if not r:
        raise HTTPException(404, "المصروف غير موجود")
    return ok(to_dict(r))


@router.post("/expenses", status_code=201)
def api_expense_create(body: ExpenseIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"]          = _parse_date(data["date"])
    data["ref_no"]        = _next_ref(db, Expense, "م")
    data["category_name"] = CATS.get(data["category_id"], "أخرى")
    data["amount"]        = data["amount_lyd"]
    r = Expense(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/expenses/{eid}")
def api_expense_update(eid: int, body: ExpenseIn, db: Session = Depends(get_db)):
    r = db.query(Expense).get(eid)
    if not r:
        raise HTTPException(404, "المصروف غير موجود")
    data = body.model_dump()
    data["date"]          = _parse_date(data["date"])
    data["category_name"] = CATS.get(data["category_id"], "أخرى")
    data["amount"]        = data["amount_lyd"]
    for k, v in data.items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/expenses/{eid}")
def api_expense_delete(eid: int, db: Session = Depends(get_db)):
    r = db.query(Expense).get(eid)
    if not r:
        raise HTTPException(404, "المصروف غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": eid})


@router.get("/expense-categories")
def api_expense_categories():
    return ok([{"id": k, "name": v} for k, v in CATS.items()])


# ══════════════════════════════════════
#  PAYROLL  /api/payroll
# ══════════════════════════════════════

@router.get("/payroll")
def api_payroll_list(
    page: int = 1, per_page: int = 20,
    month: str = "", employee_name: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Payroll).order_by(Payroll.id.desc())
    if month:
        query = query.filter(Payroll.month.contains(month))
    if employee_name:
        query = query.filter(Payroll.employee_name.contains(employee_name))
    total_net = db.query(func.sum(Payroll.net_salary)).scalar() or 0
    items, total, pages = _paginate(query, page, per_page)
    return paginated(
        [to_dict(r) for r in items], total, page, pages,
        total_net=round(total_net, 2),
    )


@router.post("/payroll", status_code=201)
def api_payroll_create(body: PayrollIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["pay_date"]   = _parse_date(data["pay_date"])
    data["net_salary"] = data["basic_salary"] + data["allowances"] + data["overtime"] - data["deductions"]
    data["ref_no"]     = _next_ref(db, Payroll, "ر")
    r = Payroll(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/payroll/{pid}")
def api_payroll_delete(pid: int, db: Session = Depends(get_db)):
    r = db.query(Payroll).get(pid)
    if not r:
        raise HTTPException(404, "السجل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": pid})


# ══════════════════════════════════════
#  INVENTORY  GET /api/inventory
# ══════════════════════════════════════

@router.get("/inventory")
def api_inventory(db: Session = Depends(get_db)):
    items = db.query(Item).filter_by(active=True).all()
    inventory_data = []
    for item in items:
        bought   = db.query(func.sum(Purchase.net_weight)).filter(Purchase.item_code == item.code).scalar() or 0
        sold     = db.query(func.sum(Sale.quantity)).filter(Sale.item_code == item.code).scalar() or 0
        stock    = bought - sold
        avg_cost = db.query(func.avg(Purchase.unit_price)).filter(Purchase.item_code == item.code).scalar() or 0
        if bought > 0 or sold > 0:
            inventory_data.append({
                "code":     item.code,
                "name":     item.name,
                "category": item.category,
                "bought":   round(bought,   2),
                "sold":     round(sold,     2),
                "stock":    round(stock,    2),
                "avg_cost": round(avg_cost, 2),
                "value":    round(stock * avg_cost, 2),
            })
    return ok({
        "items":       inventory_data,
        "total_value": round(sum(i["value"] for i in inventory_data), 2),
    })


# ══════════════════════════════════════
#  PRICE BOARD  /api/prices
# ══════════════════════════════════════

@router.get("/prices")
def api_prices_list(db: Session = Depends(get_db)):
    return ok([to_dict(r) for r in db.query(PriceBoard).order_by(PriceBoard.date.desc()).all()])


@router.post("/prices", status_code=201)
def api_price_create(body: PriceIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"] = _parse_date(data["date"])
    r = PriceBoard(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/prices/{pid}")
def api_price_delete(pid: int, db: Session = Depends(get_db)):
    r = db.query(PriceBoard).get(pid)
    if not r:
        raise HTTPException(404, "السجل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": pid})


# ══════════════════════════════════════
#  CUSTODY  /api/custody
# ══════════════════════════════════════

@router.get("/custody")
def api_custody_list(db: Session = Depends(get_db)):
    records = db.query(Custody).order_by(Custody.date.desc()).all()
    total   = db.query(func.sum(Custody.amount)).scalar() or 0
    return ok({"records": [to_dict(r) for r in records], "total": round(total, 2)})


@router.post("/custody", status_code=201)
def api_custody_create(body: CustodyIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"] = _parse_date(data["date"])
    r = Custody(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/custody/{cid}")
def api_custody_delete(cid: int, db: Session = Depends(get_db)):
    r = db.query(Custody).get(cid)
    if not r:
        raise HTTPException(404, "السجل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": cid})


# ══════════════════════════════════════
#  HAKIYA  /api/hakiya
# ══════════════════════════════════════

@router.get("/hakiya")
def api_hakiya_list(type: str = Query("", alias="type"), db: Session = Depends(get_db)):
    query = db.query(Hakiya).order_by(Hakiya.date.asc())
    if type:
        query = query.filter(Hakiya.type == type)
    items    = query.all()
    nadifa   = [r for r in items if r.type == "نضيفة"]
    mahrouqa = [r for r in items if r.type == "محروقة"]
    return ok({
        "records": [to_dict(r) for r in items],
        "summary": {
            "nadifa": {
                "total_buy":    round(sum(r.total_buy  for r in nadifa), 2),
                "total_sell":   round(sum(r.total_sell for r in nadifa), 2),
                "total_profit": round(sum(r.profit     for r in nadifa), 2),
            },
            "mahrouqa": {
                "total_buy": round(sum(r.total_buy for r in mahrouqa), 2),
            },
        },
    })


@router.post("/hakiya", status_code=201)
def api_hakiya_create(body: HakiyaIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"]       = _parse_date(data["date"])
    data["total_buy"]  = data["quantity"] * data["buy_price"]
    data["total_sell"] = data["quantity"] * data["sell_price"]
    data["profit"]     = data["total_sell"] - data["total_buy"]
    r = Hakiya(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/hakiya/{hid}")
def api_hakiya_delete(hid: int, db: Session = Depends(get_db)):
    r = db.query(Hakiya).get(hid)
    if not r:
        raise HTTPException(404, "السجل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": hid})


# ══════════════════════════════════════
#  WARSHFANA  /api/warshfana
# ══════════════════════════════════════

@router.get("/warshfana")
def api_warshfana_list(db: Session = Depends(get_db)):
    records = db.query(Warshfana).order_by(Warshfana.date.asc()).all()
    return ok({
        "records": [to_dict(r) for r in records],
        "summary": {
            "total_amount":    round(sum(r.total           for r in records), 2),
            "total_paid":      round(sum(r.paid            for r in records), 2),
            "total_discount":  round(sum(r.driver_discount for r in records), 2),
            "total_remaining": round(sum(r.remaining       for r in records), 2),
        },
    })


@router.post("/warshfana", status_code=201)
def api_warshfana_create(body: WarshfanaIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["date"]      = _parse_date(data.get("date"))
    data["remaining"] = data["total"] - data["driver_discount"] - data["paid"]
    r = Warshfana(**data)
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/warshfana/{wid}")
def api_warshfana_delete(wid: int, db: Session = Depends(get_db)):
    r = db.query(Warshfana).get(wid)
    if not r:
        raise HTTPException(404, "السجل غير موجود")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": wid})


# ══════════════════════════════════════
#  NOTES  /api/notes
# ══════════════════════════════════════

@router.get("/notes")
def api_notes_list(db: Session = Depends(get_db)):
    return ok([to_dict(r) for r in db.query(Note).order_by(Note.updated_at.desc()).all()])


@router.post("/notes", status_code=201)
def api_note_create(body: NoteIn, db: Session = Depends(get_db)):
    r = Note(**body.model_dump(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/notes/{nid}")
def api_note_update(nid: int, body: NoteIn, db: Session = Depends(get_db)):
    r = db.query(Note).get(nid)
    if not r:
        raise HTTPException(404, "الملاحظة غير موجودة")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    r.updated_at = datetime.utcnow()
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/notes/{nid}")
def api_note_delete(nid: int, db: Session = Depends(get_db)):
    r = db.query(Note).get(nid)
    if not r:
        raise HTTPException(404, "الملاحظة غير موجودة")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": nid})


# ══════════════════════════════════════
#  TODOS  /api/todos
# ══════════════════════════════════════

@router.get("/todos")
def api_todos_list(done: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(Todo)
    if done is not None:
        query = query.filter(Todo.done == done)
    return ok([to_dict(r) for r in query.order_by(Todo.priority.asc(), Todo.created_at.asc()).all()])


@router.post("/todos", status_code=201)
def api_todo_create(body: TodoIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["due_date"] = _parse_date(data.get("due_date"))
    r = Todo(**data, created_at=datetime.utcnow())
    db.add(r); db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.put("/todos/{tid}")
def api_todo_update(tid: int, body: TodoIn, db: Session = Depends(get_db)):
    r = db.query(Todo).get(tid)
    if not r:
        raise HTTPException(404, "المهمة غير موجودة")
    data = body.model_dump()
    data["due_date"] = _parse_date(data.get("due_date"))
    for k, v in data.items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.patch("/todos/{tid}/toggle")
def api_todo_toggle(tid: int, db: Session = Depends(get_db)):
    r = db.query(Todo).get(tid)
    if not r:
        raise HTTPException(404, "المهمة غير موجودة")
    r.done = not r.done
    db.commit(); db.refresh(r)
    return ok(to_dict(r))


@router.delete("/todos/{tid}")
def api_todo_delete(tid: int, db: Session = Depends(get_db)):
    r = db.query(Todo).get(tid)
    if not r:
        raise HTTPException(404, "المهمة غير موجودة")
    db.delete(r); db.commit()
    return ok({"deleted": True, "id": tid})


# ══════════════════════════════════════
#  REPORTS  GET /api/reports/monthly
# ══════════════════════════════════════

@router.get("/reports/monthly")
def api_reports_monthly(db: Session = Depends(get_db)):
    all_months = sorted(set(
        [r[0] for r in db.query(func.strftime("%Y-%m", Purchase.date)).distinct() if r[0]]
        + [r[0] for r in db.query(func.strftime("%Y-%m", Sale.date)).distinct() if r[0]]
    ))
    months_data = []
    for m in all_months:
        p    = db.query(func.sum(Purchase.amount_lyd)).filter(func.strftime("%Y-%m", Purchase.date) == m).scalar() or 0
        s    = db.query(func.sum(Sale.amount_lyd)).filter(func.strftime("%Y-%m", Sale.date) == m).scalar() or 0
        cogs = db.query(func.sum(Sale.cogs)).filter(func.strftime("%Y-%m", Sale.date) == m).scalar() or 0
        exp  = db.query(func.sum(Expense.amount_lyd)).filter(func.strftime("%Y-%m", Expense.date) == m).scalar() or 0
        gp   = s - cogs
        months_data.append({
            "month":        m,
            "purchases":    round(p,    2),
            "sales":        round(s,    2),
            "cogs":         round(cogs, 2),
            "gross_profit": round(gp,   2),
            "expenses":     round(exp,  2),
            "net_profit":   round(gp - exp, 2),
        })
    return ok(months_data)
