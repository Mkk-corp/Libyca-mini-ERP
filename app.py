from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, datetime
from typing import Optional
import math

from database import (get_db, create_tables, Setting, Item, Supplier, Customer,
                      Employee, Payroll, Purchase, Sale, Expense, Collection,
                      PriceBoard, Receivable, Custody, ExpenseCategory, Hakiya, Warshfana,
                      Note, Todo)

from fastapi.middleware.cors import CORSMiddleware
from routers.api import router as api_router

app = FastAPI(title="ليبيكا ERP")

# CORS — للسماح لتطبيق Flutter بالاتصال
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.include_router(api_router)

create_tables()

CATS = {1:'نقل',2:'ديزل/وقود',3:'عمالة',4:'صيانة',5:'كهرباء',
        6:'مياه',7:'إيجار',8:'اتصالات',9:'مصاريف إدارية',10:'أخرى',
        11:'مقدم بضاعة',12:'شوالات',13:'مطبخ'}

def paginate(query, page: int, per_page: int = 20):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = math.ceil(total / per_page) if total else 1
    return items, total, pages

# ═══════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    m, y = today.month, today.year

    def month_sum(model, col):
        return db.query(func.sum(col)).filter(
            extract('month', model.date) == m,
            extract('year', model.date) == y
        ).scalar() or 0

    purchases_m   = month_sum(Purchase, Purchase.amount_lyd)
    sales_m       = month_sum(Sale, Sale.amount_lyd)
    expenses_m    = month_sum(Expense, Expense.amount_lyd)
    cogs_m        = month_sum(Sale, Sale.cogs)
    gross_profit  = sales_m - cogs_m
    net_profit    = gross_profit - expenses_m

    recent_purchases = db.query(Purchase).order_by(Purchase.date.desc()).limit(5).all()
    recent_sales     = db.query(Sale).order_by(Sale.date.desc()).limit(5).all()

    # monthly trend (last 6 months)
    trend = []
    for i in range(5, -1, -1):
        import calendar
        mo = (m - i - 1) % 12 + 1
        yr = y if m - i > 0 else y - 1
        s = db.query(func.sum(Sale.amount_lyd)).filter(
            extract('month', Sale.date) == mo, extract('year', Sale.date) == yr
        ).scalar() or 0
        p = db.query(func.sum(Purchase.amount_lyd)).filter(
            extract('month', Purchase.date) == mo, extract('year', Purchase.date) == yr
        ).scalar() or 0
        trend.append({"month": f"{mo}/{yr}", "sales": round(s,2), "purchases": round(p,2)})

    # expense by category
    exp_cats = [[row[0], row[1]] for row in db.query(Expense.category_name, func.sum(Expense.amount_lyd)).filter(
        extract('month', Expense.date) == m, extract('year', Expense.date) == y
    ).group_by(Expense.category_name).all()]

    return templates.TemplateResponse(request, "dashboard.html", {
        "purchases_m": purchases_m, "sales_m": sales_m,
        "expenses_m": expenses_m, "net_profit": net_profit,
        "gross_profit": gross_profit,
        "recent_purchases": recent_purchases, "recent_sales": recent_sales,
        "trend": trend, "exp_cats": exp_cats,
        "month": today.strftime("%B %Y"),
    })

# ═══════════════════════════════════════════
#  الأصناف
# ═══════════════════════════════════════════
@app.get("/items", response_class=HTMLResponse)
async def items_list(request: Request, page: int = 1, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Item)
    if q:
        query = query.filter(Item.name.contains(q) | Item.code.contains(q))
    items, total, pages = paginate(query.order_by(Item.id), page)
    return templates.TemplateResponse(request, "items.html", {
        "items": items, "total": total,
        "page": page, "pages": pages, "q": q
    })

@app.get("/items/new", response_class=HTMLResponse)
async def item_new(request: Request):
    return templates.TemplateResponse(request, "item_form.html", {"item": None})

@app.post("/items/new")
async def item_create(request: Request, db: Session = Depends(get_db),
                      code: str = Form(...), name: str = Form(...),
                      category: str = Form(""), notes: str = Form(""),
                      active: Optional[str] = Form(None)):
    db.add(Item(code=code, name=name, category=category, notes=notes, active=bool(active)))
    db.commit()
    return RedirectResponse("/items", status_code=303)

@app.get("/items/{item_id}/edit", response_class=HTMLResponse)
async def item_edit(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(Item).get(item_id)
    return templates.TemplateResponse(request, "item_form.html", {"item": item})

@app.post("/items/{item_id}/edit")
async def item_update(item_id: int, db: Session = Depends(get_db),
                      code: str = Form(...), name: str = Form(...),
                      category: str = Form(""), notes: str = Form(""),
                      active: Optional[str] = Form(None)):
    item = db.query(Item).get(item_id)
    item.code = code; item.name = name; item.category = category
    item.notes = notes; item.active = bool(active)
    db.commit()
    return RedirectResponse("/items", status_code=303)

@app.post("/items/{item_id}/delete")
async def item_delete(item_id: int, db: Session = Depends(get_db)):
    db.query(Item).filter_by(id=item_id).delete()
    db.commit()
    return RedirectResponse("/items", status_code=303)

# ═══════════════════════════════════════════
#  الموردون
# ═══════════════════════════════════════════
@app.get("/suppliers", response_class=HTMLResponse)
async def suppliers_list(request: Request, page: int = 1, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Supplier)
    if q:
        query = query.filter(Supplier.name.contains(q))
    suppliers, total, pages = paginate(query.order_by(Supplier.id), page)
    return templates.TemplateResponse(request, "suppliers.html", {
        "suppliers": suppliers,
        "total": total, "page": page, "pages": pages, "q": q
    })

@app.get("/suppliers/new", response_class=HTMLResponse)
async def supplier_new(request: Request):
    return templates.TemplateResponse(request, "supplier_form.html", {"supplier": None})

@app.post("/suppliers/new")
async def supplier_create(db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          phone: str = Form(""), city: str = Form(""),
                          notes: str = Form(""), active: Optional[str] = Form(None)):
    db.add(Supplier(code=code, name=name, phone=phone, city=city, notes=notes, active=bool(active)))
    db.commit()
    return RedirectResponse("/suppliers", status_code=303)

@app.get("/suppliers/{sid}/edit", response_class=HTMLResponse)
async def supplier_edit(sid: int, request: Request, db: Session = Depends(get_db)):
    s = db.query(Supplier).get(sid)
    return templates.TemplateResponse(request, "supplier_form.html", {"supplier": s})

@app.post("/suppliers/{sid}/edit")
async def supplier_update(sid: int, db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          phone: str = Form(""), city: str = Form(""),
                          notes: str = Form(""), active: Optional[str] = Form(None)):
    s = db.query(Supplier).get(sid)
    s.code = code; s.name = name; s.phone = phone; s.city = city
    s.notes = notes; s.active = bool(active)
    db.commit()
    return RedirectResponse("/suppliers", status_code=303)

@app.post("/suppliers/{sid}/delete")
async def supplier_delete(sid: int, db: Session = Depends(get_db)):
    db.query(Supplier).filter_by(id=sid).delete()
    db.commit()
    return RedirectResponse("/suppliers", status_code=303)

# ═══════════════════════════════════════════
#  العملاء
# ═══════════════════════════════════════════
@app.get("/customers", response_class=HTMLResponse)
async def customers_list(request: Request, page: int = 1, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Customer)
    if q:
        query = query.filter(Customer.name.contains(q))
    customers, total, pages = paginate(query.order_by(Customer.id), page)
    return templates.TemplateResponse(request, "customers.html", {
        "customers": customers,
        "total": total, "page": page, "pages": pages, "q": q
    })

@app.get("/customers/new", response_class=HTMLResponse)
async def customer_new(request: Request):
    return templates.TemplateResponse(request, "customer_form.html", {"customer": None})

@app.post("/customers/new")
async def customer_create(db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          phone: str = Form(""), city: str = Form(""),
                          notes: str = Form(""), active: Optional[str] = Form(None)):
    db.add(Customer(code=code, name=name, phone=phone, city=city, notes=notes, active=bool(active)))
    db.commit()
    return RedirectResponse("/customers", status_code=303)

@app.get("/customers/{cid}/edit", response_class=HTMLResponse)
async def customer_edit(cid: int, request: Request, db: Session = Depends(get_db)):
    c = db.query(Customer).get(cid)
    return templates.TemplateResponse(request, "customer_form.html", {"customer": c})

@app.post("/customers/{cid}/edit")
async def customer_update(cid: int, db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          phone: str = Form(""), city: str = Form(""),
                          notes: str = Form(""), active: Optional[str] = Form(None)):
    c = db.query(Customer).get(cid)
    c.code = code; c.name = name; c.phone = phone; c.city = city
    c.notes = notes; c.active = bool(active)
    db.commit()
    return RedirectResponse("/customers", status_code=303)

@app.post("/customers/{cid}/delete")
async def customer_delete(cid: int, db: Session = Depends(get_db)):
    db.query(Customer).filter_by(id=cid).delete()
    db.commit()
    return RedirectResponse("/customers", status_code=303)

# ═══════════════════════════════════════════
#  الموظفون
# ═══════════════════════════════════════════
@app.get("/employees", response_class=HTMLResponse)
async def employees_list(request: Request, page: int = 1, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Employee)
    if q:
        query = query.filter(Employee.name.contains(q) | Employee.department.contains(q))
    employees, total, pages = paginate(query.order_by(Employee.id), page)
    return templates.TemplateResponse(request, "employees.html", {
        "employees": employees,
        "total": total, "page": page, "pages": pages, "q": q
    })

@app.get("/employees/new", response_class=HTMLResponse)
async def employee_new(request: Request):
    return templates.TemplateResponse(request, "employee_form.html", {"emp": None})

@app.post("/employees/new")
async def employee_create(db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          department: str = Form(""), hire_date: Optional[str] = Form(None),
                          basic_salary: float = Form(0), shift_salary: float = Form(0),
                          fixed_deductions: float = Form(0), payment_method: str = Form(""),
                          active: Optional[str] = Form(None)):
    hd = datetime.strptime(hire_date, "%Y-%m-%d").date() if hire_date else None
    db.add(Employee(code=code, name=name, department=department, hire_date=hd,
                    basic_salary=basic_salary, shift_salary=shift_salary,
                    fixed_deductions=fixed_deductions, payment_method=payment_method,
                    active=bool(active)))
    db.commit()
    return RedirectResponse("/employees", status_code=303)

@app.get("/employees/{eid}/edit", response_class=HTMLResponse)
async def employee_edit(eid: int, request: Request, db: Session = Depends(get_db)):
    emp = db.query(Employee).get(eid)
    return templates.TemplateResponse(request, "employee_form.html", {"emp": emp})

@app.post("/employees/{eid}/edit")
async def employee_update(eid: int, db: Session = Depends(get_db),
                          code: str = Form(...), name: str = Form(...),
                          department: str = Form(""), hire_date: Optional[str] = Form(None),
                          basic_salary: float = Form(0), shift_salary: float = Form(0),
                          fixed_deductions: float = Form(0), payment_method: str = Form(""),
                          active: Optional[str] = Form(None)):
    emp = db.query(Employee).get(eid)
    emp.code = code; emp.name = name; emp.department = department
    emp.hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date() if hire_date else None
    emp.basic_salary = basic_salary; emp.shift_salary = shift_salary
    emp.fixed_deductions = fixed_deductions; emp.payment_method = payment_method
    emp.active = bool(active)
    db.commit()
    return RedirectResponse("/employees", status_code=303)

@app.post("/employees/{eid}/delete")
async def employee_delete(eid: int, db: Session = Depends(get_db)):
    db.query(Employee).filter_by(id=eid).delete()
    db.commit()
    return RedirectResponse("/employees", status_code=303)

# ═══════════════════════════════════════════
#  المشتريات
# ═══════════════════════════════════════════
@app.get("/purchases", response_class=HTMLResponse)
async def purchases_list(request: Request, page: int = 1, q: str = "",
                         month: str = "", item_filter: str = "", db: Session = Depends(get_db)):
    query = db.query(Purchase)
    if q:
        query = query.filter(Purchase.supplier_name.contains(q) | Purchase.item_name.contains(q))
    if month:
        y, m = month.split("-")
        query = query.filter(extract('year', Purchase.date) == int(y),
                             extract('month', Purchase.date) == int(m))
    if item_filter:
        query = query.filter(Purchase.item_name == item_filter)
    purchases, total, pages = paginate(query.order_by(Purchase.date.desc()), page)
    total_amount = query.with_entities(func.sum(Purchase.amount_lyd)).scalar() or 0
    item_names = [r[0] for r in db.query(Purchase.item_name).distinct().order_by(Purchase.item_name).all() if r[0]]
    suppliers = db.query(Supplier).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    return templates.TemplateResponse(request, "purchases.html", {
        "purchases": purchases, "total": total,
        "page": page, "pages": pages, "q": q, "month": month,
        "item_filter": item_filter, "item_names": item_names,
        "total_amount": total_amount, "suppliers": suppliers, "items": items
    })

@app.get("/purchases/new", response_class=HTMLResponse)
async def purchase_new(request: Request, db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    last = db.query(Purchase).order_by(Purchase.id.desc()).first()
    next_num = 1
    if last and last.ref_no:
        try:
            next_num = int(last.ref_no.replace('ش', '').lstrip('0') or '0') + 1
        except:
            pass
    ref_no = f"ش{next_num:06d}"
    return templates.TemplateResponse(request, "purchase_form.html", {
        "purchase": None,
        "suppliers": suppliers, "items": items, "ref_no": ref_no
    })

@app.post("/purchases/new")
async def purchase_create(db: Session = Depends(get_db),
                          ref_no: str = Form(...), date_: str = Form(...),
                          supplier_name: str = Form(...), item_name: str = Form(...),
                          item_code: str = Form(""), gross_weight: float = Form(0),
                          tare_weight: float = Form(0), net_weight: float = Form(0),
                          unit_price: float = Form(0), amount_lyd: float = Form(0),
                          payment_method: str = Form(""), paid: float = Form(0),
                          notes: str = Form("")):
    remaining = amount_lyd - paid
    db.add(Purchase(ref_no=ref_no, date=datetime.strptime(date_, "%Y-%m-%d").date(),
                    supplier_name=supplier_name, item_name=item_name, item_code=item_code,
                    gross_weight=gross_weight, tare_weight=tare_weight, net_weight=net_weight,
                    unit_price=unit_price, amount=amount_lyd, amount_lyd=amount_lyd,
                    payment_method=payment_method, paid=paid, remaining=remaining, notes=notes))
    db.commit()
    return RedirectResponse("/purchases", status_code=303)

@app.get("/purchases/{pid}/edit", response_class=HTMLResponse)
async def purchase_edit(pid: int, request: Request, db: Session = Depends(get_db)):
    p = db.query(Purchase).get(pid)
    suppliers = db.query(Supplier).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    return templates.TemplateResponse(request, "purchase_form.html", {
        "purchase": p, "suppliers": suppliers, "items": items
    })

@app.post("/purchases/{pid}/edit")
async def purchase_update(pid: int, db: Session = Depends(get_db),
                          ref_no: str = Form(...), date_: str = Form(...),
                          supplier_name: str = Form(...), item_name: str = Form(...),
                          item_code: str = Form(""), gross_weight: float = Form(0),
                          tare_weight: float = Form(0), net_weight: float = Form(0),
                          unit_price: float = Form(0), amount_lyd: float = Form(0),
                          payment_method: str = Form(""), paid: float = Form(0),
                          notes: str = Form("")):
    p = db.query(Purchase).get(pid)
    p.ref_no = ref_no; p.date = datetime.strptime(date_, "%Y-%m-%d").date()
    p.supplier_name = supplier_name; p.item_name = item_name; p.item_code = item_code
    p.gross_weight = gross_weight; p.tare_weight = tare_weight; p.net_weight = net_weight
    p.unit_price = unit_price; p.amount = amount_lyd; p.amount_lyd = amount_lyd
    p.payment_method = payment_method; p.paid = paid; p.remaining = amount_lyd - paid
    p.notes = notes
    db.commit()
    return RedirectResponse("/purchases", status_code=303)

@app.post("/purchases/{pid}/delete")
async def purchase_delete(pid: int, db: Session = Depends(get_db)):
    db.query(Purchase).filter_by(id=pid).delete()
    db.commit()
    return RedirectResponse("/purchases", status_code=303)

@app.get("/purchases/{pid}/print", response_class=HTMLResponse)
async def purchase_print(pid: int, request: Request, db: Session = Depends(get_db)):
    p = db.query(Purchase).get(pid)
    company = db.query(Setting).filter_by(key="company_name").first()
    return templates.TemplateResponse(request, "print_purchase.html", {
        "p": p,
        "company": company.value if company else "ليبيكا"
    })

# ═══════════════════════════════════════════
#  المبيعات
# ═══════════════════════════════════════════
@app.get("/sales", response_class=HTMLResponse)
async def sales_list(request: Request, page: int = 1, q: str = "",
                     month: str = "", db: Session = Depends(get_db)):
    query = db.query(Sale)
    if q:
        query = query.filter(Sale.customer_name.contains(q) | Sale.item_name.contains(q))
    if month:
        y, m = month.split("-")
        query = query.filter(extract('year', Sale.date) == int(y),
                             extract('month', Sale.date) == int(m))
    sales, total, pages = paginate(query.order_by(Sale.date.desc()), page)
    total_sales = db.query(func.sum(Sale.amount_lyd)).scalar() or 0
    total_profit = db.query(func.sum(Sale.gross_profit)).scalar() or 0
    customers = db.query(Customer).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    return templates.TemplateResponse(request, "sales.html", {
        "sales": sales, "total": total,
        "page": page, "pages": pages, "q": q, "month": month,
        "total_sales": total_sales, "total_profit": total_profit,
        "customers": customers, "items": items
    })

@app.get("/sales/new", response_class=HTMLResponse)
async def sale_new(request: Request, db: Session = Depends(get_db)):
    customers = db.query(Customer).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    last = db.query(Sale).order_by(Sale.id.desc()).first()
    next_num = 1
    if last and last.ref_no:
        try:
            next_num = int(last.ref_no.replace('ب', '').lstrip('0') or '0') + 1
        except:
            pass
    ref_no = f"ب{next_num:06d}"
    return templates.TemplateResponse(request, "sale_form.html", {
        "sale": None,
        "customers": customers, "items": items, "ref_no": ref_no
    })

@app.post("/sales/new")
async def sale_create(db: Session = Depends(get_db),
                      ref_no: str = Form(...), date_: str = Form(...),
                      customer_name: str = Form(...), item_name: str = Form(...),
                      item_code: str = Form(""), quantity: float = Form(0),
                      unit_price: float = Form(0), amount_lyd: float = Form(0),
                      cogs: float = Form(0), payment_method: str = Form(""),
                      paid: float = Form(0), notes: str = Form("")):
    gross_profit = amount_lyd - cogs
    remaining = amount_lyd - paid
    db.add(Sale(ref_no=ref_no, date=datetime.strptime(date_, "%Y-%m-%d").date(),
                customer_name=customer_name, item_name=item_name, item_code=item_code,
                quantity=quantity, unit_price=unit_price, amount=amount_lyd, amount_lyd=amount_lyd,
                cogs=cogs, gross_profit=gross_profit,
                payment_method=payment_method, paid=paid, remaining=remaining, notes=notes))
    db.commit()
    return RedirectResponse("/sales", status_code=303)

@app.get("/sales/{sid}/edit", response_class=HTMLResponse)
async def sale_edit(sid: int, request: Request, db: Session = Depends(get_db)):
    s = db.query(Sale).get(sid)
    customers = db.query(Customer).filter_by(active=True).all()
    items = db.query(Item).filter_by(active=True).all()
    return templates.TemplateResponse(request, "sale_form.html", {
        "sale": s, "customers": customers, "items": items
    })

@app.post("/sales/{sid}/edit")
async def sale_update(sid: int, db: Session = Depends(get_db),
                      ref_no: str = Form(...), date_: str = Form(...),
                      customer_name: str = Form(...), item_name: str = Form(...),
                      item_code: str = Form(""), quantity: float = Form(0),
                      unit_price: float = Form(0), amount_lyd: float = Form(0),
                      cogs: float = Form(0), payment_method: str = Form(""),
                      paid: float = Form(0), notes: str = Form("")):
    s = db.query(Sale).get(sid)
    s.ref_no = ref_no; s.date = datetime.strptime(date_, "%Y-%m-%d").date()
    s.customer_name = customer_name; s.item_name = item_name; s.item_code = item_code
    s.quantity = quantity; s.unit_price = unit_price; s.amount = amount_lyd; s.amount_lyd = amount_lyd
    s.cogs = cogs; s.gross_profit = amount_lyd - cogs
    s.payment_method = payment_method; s.paid = paid; s.remaining = amount_lyd - paid
    s.notes = notes
    db.commit()
    return RedirectResponse("/sales", status_code=303)

@app.post("/sales/{sid}/delete")
async def sale_delete(sid: int, db: Session = Depends(get_db)):
    db.query(Sale).filter_by(id=sid).delete()
    db.commit()
    return RedirectResponse("/sales", status_code=303)

@app.get("/sales/{sid}/print", response_class=HTMLResponse)
async def sale_print(sid: int, request: Request, db: Session = Depends(get_db)):
    s = db.query(Sale).get(sid)
    company = db.query(Setting).filter_by(key="company_name").first()
    return templates.TemplateResponse(request, "print_sale.html", {
        "s": s,
        "company": company.value if company else "ليبيكا"
    })

# ═══════════════════════════════════════════
#  المصروفات
# ═══════════════════════════════════════════
@app.get("/expenses", response_class=HTMLResponse)
async def expenses_list(request: Request, page: int = 1, q: str = "",
                        month: str = "", cat: str = "", db: Session = Depends(get_db)):
    query = db.query(Expense)
    if q:
        query = query.filter(Expense.description.contains(q))
    if month:
        y, m = month.split("-")
        query = query.filter(extract('year', Expense.date) == int(y),
                             extract('month', Expense.date) == int(m))
    if cat:
        query = query.filter(Expense.category_name == cat)
    expenses, total, pages = paginate(query.order_by(Expense.date.desc()), page)
    total_amount = query.with_entities(func.sum(Expense.amount_lyd)).scalar() or 0
    return templates.TemplateResponse(request, "expenses.html", {
        "expenses": expenses, "total": total,
        "page": page, "pages": pages, "q": q, "month": month, "cat": cat,
        "total_amount": total_amount, "cats": CATS
    })

@app.get("/expenses/new", response_class=HTMLResponse)
async def expense_new(request: Request):
    return templates.TemplateResponse(request, "expense_form.html", {
        "expense": None, "cats": CATS
    })

@app.post("/expenses/new")
async def expense_create(db: Session = Depends(get_db),
                         date_: str = Form(...), category_id: int = Form(...),
                         description: str = Form(...), amount_lyd: float = Form(0),
                         payment_method: str = Form(""), notes: str = Form("")):
    last = db.query(Expense).order_by(Expense.id.desc()).first()
    next_num = 1
    if last and last.ref_no:
        try:
            next_num = int(last.ref_no.replace('م', '').lstrip('0') or '0') + 1
        except:
            pass
    ref_no = f"م{next_num:06d}"
    db.add(Expense(ref_no=ref_no, date=datetime.strptime(date_, "%Y-%m-%d").date(),
                   category_id=category_id, category_name=CATS.get(category_id, 'أخرى'),
                   description=description, amount=amount_lyd, amount_lyd=amount_lyd,
                   payment_method=payment_method, notes=notes))
    db.commit()
    return RedirectResponse("/expenses", status_code=303)

@app.get("/expenses/{eid}/edit", response_class=HTMLResponse)
async def expense_edit(eid: int, request: Request, db: Session = Depends(get_db)):
    e = db.query(Expense).get(eid)
    return templates.TemplateResponse(request, "expense_form.html", {
        "expense": e, "cats": CATS
    })

@app.post("/expenses/{eid}/edit")
async def expense_update(eid: int, db: Session = Depends(get_db),
                         date_: str = Form(...), category_id: int = Form(...),
                         description: str = Form(...), amount_lyd: float = Form(0),
                         payment_method: str = Form(""), notes: str = Form("")):
    e = db.query(Expense).get(eid)
    e.date = datetime.strptime(date_, "%Y-%m-%d").date()
    e.category_id = category_id; e.category_name = CATS.get(category_id, 'أخرى')
    e.description = description; e.amount = amount_lyd; e.amount_lyd = amount_lyd
    e.payment_method = payment_method; e.notes = notes
    db.commit()
    return RedirectResponse("/expenses", status_code=303)

@app.post("/expenses/{eid}/delete")
async def expense_delete(eid: int, db: Session = Depends(get_db)):
    db.query(Expense).filter_by(id=eid).delete()
    db.commit()
    return RedirectResponse("/expenses", status_code=303)

@app.get("/expenses/{eid}/print", response_class=HTMLResponse)
async def expense_print(eid: int, request: Request, db: Session = Depends(get_db)):
    e = db.query(Expense).get(eid)
    company = db.query(Setting).filter_by(key="company_name").first()
    return templates.TemplateResponse(request, "print_expense.html", {
        "e": e,
        "company": company.value if company else "ليبيكا"
    })

# ═══════════════════════════════════════════
#  المخزون
# ═══════════════════════════════════════════
@app.get("/inventory", response_class=HTMLResponse)
async def inventory(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).filter_by(active=True).all()
    inventory_data = []
    for item in items:
        bought = db.query(func.sum(Purchase.net_weight)).filter(
            Purchase.item_code == item.code).scalar() or 0
        sold = db.query(func.sum(Sale.quantity)).filter(
            Sale.item_code == item.code).scalar() or 0
        stock = bought - sold
        avg_cost = db.query(func.avg(Purchase.unit_price)).filter(
            Purchase.item_code == item.code).scalar() or 0
        if bought > 0 or sold > 0:
            inventory_data.append({
                "code": item.code, "name": item.name, "category": item.category,
                "bought": round(bought, 2), "sold": round(sold, 2),
                "stock": round(stock, 2), "avg_cost": round(avg_cost, 2),
                "value": round(stock * avg_cost, 2)
            })
    total_value = sum(i["value"] for i in inventory_data)
    return templates.TemplateResponse(request, "inventory.html", {
        "inventory_data": inventory_data, "total_value": total_value
    })

# ═══════════════════════════════════════════
#  بورصة الأسعار
# ═══════════════════════════════════════════
@app.get("/prices", response_class=HTMLResponse)
async def prices_list(request: Request, db: Session = Depends(get_db)):
    prices = db.query(PriceBoard).order_by(PriceBoard.date.desc()).all()
    items = db.query(Item).filter_by(active=True).all()
    return templates.TemplateResponse(request, "prices.html", {
        "prices": prices, "items": items
    })

@app.post("/prices/new")
async def price_create(db: Session = Depends(get_db),
                       date_: str = Form(...), item_code: str = Form(...),
                       item_name: str = Form(...), buy_price: float = Form(0),
                       sell_price: float = Form(0)):
    db.add(PriceBoard(date=datetime.strptime(date_, "%Y-%m-%d").date(),
                      item_code=item_code, item_name=item_name,
                      buy_price=buy_price, sell_price=sell_price))
    db.commit()
    return RedirectResponse("/prices", status_code=303)

@app.post("/prices/{pid}/delete")
async def price_delete(pid: int, db: Session = Depends(get_db)):
    db.query(PriceBoard).filter_by(id=pid).delete()
    db.commit()
    return RedirectResponse("/prices", status_code=303)

# ═══════════════════════════════════════════
#  العهدة
# ═══════════════════════════════════════════
@app.get("/custody", response_class=HTMLResponse)
async def custody_list(request: Request, db: Session = Depends(get_db)):
    records = db.query(Custody).order_by(Custody.date.desc()).all()
    total = db.query(func.sum(Custody.amount)).scalar() or 0
    return templates.TemplateResponse(request, "custody.html", {
        "records": records, "total": total
    })

@app.post("/custody/new")
async def custody_create(db: Session = Depends(get_db),
                         date_: str = Form(...), description: str = Form(...),
                         amount: float = Form(0), notes: str = Form("")):
    db.add(Custody(date=datetime.strptime(date_, "%Y-%m-%d").date(),
                   description=description, amount=amount, notes=notes))
    db.commit()
    return RedirectResponse("/custody", status_code=303)

@app.post("/custody/{cid}/delete")
async def custody_delete(cid: int, db: Session = Depends(get_db)):
    db.query(Custody).filter_by(id=cid).delete()
    db.commit()
    return RedirectResponse("/custody", status_code=303)

# ═══════════════════════════════════════════
#  الرواتب
# ═══════════════════════════════════════════
@app.get("/payroll", response_class=HTMLResponse)
async def payroll_list(request: Request, page: int = 1, month: str = "", db: Session = Depends(get_db)):
    query = db.query(Payroll)
    if month:
        query = query.filter(Payroll.month.contains(month))
    payrolls, total, pages = paginate(query.order_by(Payroll.id.desc()), page)
    total_net = db.query(func.sum(Payroll.net_salary)).scalar() or 0
    employees = db.query(Employee).filter_by(active=True).all()
    return templates.TemplateResponse(request, "payroll.html", {
        "payrolls": payrolls, "total": total,
        "page": page, "pages": pages, "month": month,
        "total_net": total_net, "employees": employees
    })

@app.post("/payroll/new")
async def payroll_create(db: Session = Depends(get_db),
                         pay_date: str = Form(...), month: str = Form(...),
                         employee_name: str = Form(...), basic_salary: float = Form(0),
                         allowances: float = Form(0), overtime: float = Form(0),
                         deductions: float = Form(0), payment_method: str = Form("")):
    net = basic_salary + allowances + overtime - deductions
    last = db.query(Payroll).order_by(Payroll.id.desc()).first()
    num = (last.id + 1) if last else 1
    db.add(Payroll(ref_no=f"ر{num:06d}", month=month,
                   pay_date=datetime.strptime(pay_date, "%Y-%m-%d").date(),
                   employee_name=employee_name, basic_salary=basic_salary,
                   allowances=allowances, overtime=overtime,
                   deductions=deductions, net_salary=net, payment_method=payment_method))
    db.commit()
    return RedirectResponse("/payroll", status_code=303)

# ═══════════════════════════════════════════
#  التقارير
# ═══════════════════════════════════════════
@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request, db: Session = Depends(get_db)):
    # Monthly summary
    monthly = db.query(
        func.strftime('%Y-%m', Purchase.date).label('month'),
        func.sum(Purchase.amount_lyd)
    ).group_by('month').all()

    months_data = []
    all_months = sorted(set(
        list(db.query(func.strftime('%Y-%m', Purchase.date)).distinct()) +
        list(db.query(func.strftime('%Y-%m', Sale.date)).distinct())
    ))
    for (m,) in all_months:
        if not m:
            continue
        y, mo = int(m.split('-')[0]), int(m.split('-')[1])
        p = db.query(func.sum(Purchase.amount_lyd)).filter(
            func.strftime('%Y-%m', Purchase.date) == m).scalar() or 0
        s = db.query(func.sum(Sale.amount_lyd)).filter(
            func.strftime('%Y-%m', Sale.date) == m).scalar() or 0
        cogs = db.query(func.sum(Sale.cogs)).filter(
            func.strftime('%Y-%m', Sale.date) == m).scalar() or 0
        exp = db.query(func.sum(Expense.amount_lyd)).filter(
            func.strftime('%Y-%m', Expense.date) == m).scalar() or 0
        gp = s - cogs
        np = gp - exp
        months_data.append({
            "month": m, "purchases": round(p,2), "sales": round(s,2),
            "cogs": round(cogs,2), "gross_profit": round(gp,2),
            "expenses": round(exp,2), "net_profit": round(np,2)
        })

    return templates.TemplateResponse(request, "reports.html", {
        "months_data": months_data
    })

# ═══════════════════════════════════════════
#  الحكية
# ═══════════════════════════════════════════
@app.get("/hakiya", response_class=HTMLResponse)
async def hakiya_list(request: Request, type_: str = "", db: Session = Depends(get_db)):
    query = db.query(Hakiya).order_by(Hakiya.date.asc(), Hakiya.id.asc())
    if type_:
        query = query.filter(Hakiya.type == type_)
    records = query.all()

    nadifa = [r for r in db.query(Hakiya).filter_by(type='نضيفة').all()]
    mahrouqa = [r for r in db.query(Hakiya).filter_by(type='محروقة').all()]

    total_buy_nadifa   = sum(r.total_buy  for r in nadifa)
    total_sell_nadifa  = sum(r.total_sell for r in nadifa)
    total_profit_nadifa = sum(r.profit    for r in nadifa)
    total_buy_mahrouqa  = sum(r.total_buy for r in mahrouqa)

    return templates.TemplateResponse(request, "hakiya.html", {
        "records": records,
        "type_": type_,
        "total_buy_nadifa": round(total_buy_nadifa, 2),
        "total_sell_nadifa": round(total_sell_nadifa, 2),
        "total_profit_nadifa": round(total_profit_nadifa, 2),
        "total_buy_mahrouqa": round(total_buy_mahrouqa, 2),
    })

@app.post("/hakiya/new")
async def hakiya_create(db: Session = Depends(get_db),
                        date_: str = Form(...), type_: str = Form(...),
                        quantity: float = Form(0), buy_price: float = Form(0),
                        sell_price: float = Form(0), notes: str = Form("")):
    total_buy = quantity * buy_price
    total_sell = quantity * sell_price
    profit = total_sell - total_buy
    db.add(Hakiya(date=datetime.strptime(date_, "%Y-%m-%d").date(),
                  type=type_, quantity=quantity, buy_price=buy_price,
                  total_buy=total_buy, sell_price=sell_price,
                  total_sell=total_sell, profit=profit, notes=notes))
    db.commit()
    return RedirectResponse("/hakiya", status_code=303)

@app.post("/hakiya/{hid}/delete")
async def hakiya_delete(hid: int, db: Session = Depends(get_db)):
    db.query(Hakiya).filter_by(id=hid).delete()
    db.commit()
    return RedirectResponse("/hakiya", status_code=303)

# ═══════════════════════════════════════════
#  الإعدادات
# ═══════════════════════════════════════════
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    settings = {s.key: s.value for s in db.query(Setting).all()}
    return templates.TemplateResponse(request, "settings.html", {
        "settings": settings
    })

# ═══════════════════════════════════════════
#  ورشفانة
# ═══════════════════════════════════════════
@app.get("/warshfana", response_class=HTMLResponse)
async def warshfana_list(request: Request, db: Session = Depends(get_db)):
    records = db.query(Warshfana).order_by(Warshfana.date.asc(), Warshfana.id.asc()).all()
    total_amount  = sum(r.total           for r in records)
    total_paid    = sum(r.paid            for r in records)
    total_disc    = sum(r.driver_discount for r in records)
    total_remain  = sum(r.remaining       for r in records)
    return templates.TemplateResponse(request, "warshfana.html", {
        "records": records,
        "total_amount": round(total_amount, 2),
        "total_paid": round(total_paid, 2),
        "total_disc": round(total_disc, 2),
        "total_remain": round(total_remain, 2),
    })

@app.post("/warshfana/new")
async def warshfana_create(db: Session = Depends(get_db),
                           date_: Optional[str] = Form(None),
                           item_type: str = Form(...),
                           weight: float = Form(0),
                           price_per_kg: float = Form(0),
                           total: float = Form(0),
                           driver_discount: float = Form(0),
                           paid: float = Form(0),
                           notes: str = Form("")):
    remaining = total - driver_discount - paid
    d = datetime.strptime(date_, "%Y-%m-%d").date() if date_ else None
    db.add(Warshfana(date=d, item_type=item_type, weight=weight,
                     price_per_kg=price_per_kg, total=total,
                     driver_discount=driver_discount, paid=paid,
                     remaining=remaining, notes=notes))
    db.commit()
    return RedirectResponse("/warshfana", status_code=303)

@app.post("/warshfana/{wid}/delete")
async def warshfana_delete(wid: int, db: Session = Depends(get_db)):
    db.query(Warshfana).filter_by(id=wid).delete()
    db.commit()
    return RedirectResponse("/warshfana", status_code=303)

# ═══════════════════════════════════════════
#  الملاحظات والمهام
# ═══════════════════════════════════════════
@app.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request, db: Session = Depends(get_db)):
    notes = db.query(Note).order_by(Note.updated_at.desc()).all()
    todos_pending = db.query(Todo).filter_by(done=False).order_by(Todo.priority.asc(), Todo.created_at.asc()).all()
    todos_done    = db.query(Todo).filter_by(done=True).order_by(Todo.created_at.desc()).limit(20).all()
    total_todos   = db.query(Todo).count()
    done_count    = db.query(Todo).filter_by(done=True).count()
    return templates.TemplateResponse(request, "notes.html", {
        "notes": notes,
        "todos_pending": todos_pending, "todos_done": todos_done,
        "total_todos": total_todos, "done_count": done_count,
    })

@app.post("/notes/new")
async def note_create(db: Session = Depends(get_db),
                      title: str = Form(...), content: str = Form(""),
                      color: str = Form("yellow")):
    db.add(Note(title=title, content=content, color=color,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/notes/{nid}/edit")
async def note_update(nid: int, db: Session = Depends(get_db),
                      title: str = Form(...), content: str = Form(""),
                      color: str = Form("yellow")):
    n = db.query(Note).get(nid)
    n.title = title; n.content = content; n.color = color
    n.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/notes/{nid}/delete")
async def note_delete(nid: int, db: Session = Depends(get_db)):
    db.query(Note).filter_by(id=nid).delete()
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/todos/new")
async def todo_create(db: Session = Depends(get_db),
                      task: str = Form(...), priority: str = Form("normal"),
                      due_date: Optional[str] = Form(None)):
    d = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None
    db.add(Todo(task=task, priority=priority, due_date=d, created_at=datetime.utcnow()))
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/todos/{tid}/toggle")
async def todo_toggle(tid: int, db: Session = Depends(get_db)):
    t = db.query(Todo).get(tid)
    t.done = not t.done
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/todos/{tid}/delete")
async def todo_delete(tid: int, db: Session = Depends(get_db)):
    db.query(Todo).filter_by(id=tid).delete()
    db.commit()
    return RedirectResponse("/notes", status_code=303)

@app.post("/settings")
async def settings_save(db: Session = Depends(get_db),
                        company_name: str = Form(""), currency: str = Form(""),
                        business_type: str = Form(""), whatsapp1: str = Form(""),
                        whatsapp2: str = Form("")):
    updates = {"company_name": company_name, "currency": currency,
               "business_type": business_type, "whatsapp1": whatsapp1, "whatsapp2": whatsapp2}
    for key, value in updates.items():
        s = db.query(Setting).filter_by(key=key).first()
        if s:
            s.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return RedirectResponse("/settings", status_code=303)
