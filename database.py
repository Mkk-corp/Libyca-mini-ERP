from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# على Railway يُخزن الملف في /data (volume دائم)، وإلا يُستخدم المجلد الحالي
_db_dir = os.environ.get("DB_DIR", ".")
os.makedirs(_db_dir, exist_ok=True)
DATABASE_URL = f"sqlite:///{_db_dir}/libyca.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── الإعدادات ──────────────────────────────────────────────
class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)


# ── الأصناف ────────────────────────────────────────────────
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    category = Column(String)
    active = Column(Boolean, default=True)
    notes = Column(Text)
    avg_cost = Column(Float, default=0)


# ── الموردون ───────────────────────────────────────────────
class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    city = Column(String)
    active = Column(Boolean, default=True)
    notes = Column(Text)


# ── العملاء ────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    city = Column(String)
    active = Column(Boolean, default=True)
    notes = Column(Text)


# ── الموظفون ───────────────────────────────────────────────
class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    department = Column(String)
    hire_date = Column(Date)
    basic_salary = Column(Float, default=0)
    shift_count = Column(Integer, default=0)
    shift_salary = Column(Float, default=0)
    fixed_deductions = Column(Float, default=0)
    payment_method = Column(String)
    active = Column(Boolean, default=True)


# ── الرواتب ────────────────────────────────────────────────
class Payroll(Base):
    __tablename__ = "payroll"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_no = Column(String)
    month = Column(String)
    pay_date = Column(Date)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    employee_name = Column(String)
    basic_salary = Column(Float, default=0)
    allowances = Column(Float, default=0)
    overtime = Column(Float, default=0)
    deductions = Column(Float, default=0)
    net_salary = Column(Float, default=0)
    payment_method = Column(String)
    employee = relationship("Employee")


# ── المشتريات ──────────────────────────────────────────────
class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_no = Column(String)
    date = Column(Date)
    supplier_name = Column(String)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    item_code = Column(String)
    item_name = Column(String)
    gross_weight = Column(Float, default=0)
    tare_weight = Column(Float, default=0)
    net_weight = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    amount = Column(Float, default=0)
    currency = Column(String, default="د.ل")
    exchange_rate = Column(Float, default=1)
    amount_lyd = Column(Float, default=0)
    payment_method = Column(String)
    paid = Column(Float, default=0)
    remaining = Column(Float, default=0)
    notes = Column(Text)


# ── المبيعات ───────────────────────────────────────────────
class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_no = Column(String)
    date = Column(Date)
    customer_name = Column(String)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    item_code = Column(String)
    item_name = Column(String)
    quantity = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    amount = Column(Float, default=0)
    currency = Column(String, default="د.ل")
    exchange_rate = Column(Float, default=1)
    amount_lyd = Column(Float, default=0)
    cogs = Column(Float, default=0)
    gross_profit = Column(Float, default=0)
    payment_method = Column(String)
    paid = Column(Float, default=0)
    remaining = Column(Float, default=0)
    notes = Column(Text)


# ── المصروفات ──────────────────────────────────────────────
class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_no = Column(String)
    date = Column(Date)
    category_id = Column(Integer)
    category_name = Column(String)
    description = Column(String)
    amount = Column(Float, default=0)
    currency = Column(String, default="د.ل")
    exchange_rate = Column(Float, default=1)
    amount_lyd = Column(Float, default=0)
    payment_method = Column(String)
    notes = Column(Text)


# ── المكب ──────────────────────────────────────────────────
class Collection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)
    item_code = Column(String)
    item_name = Column(String)
    gross_weight = Column(Float, default=0)
    tare_weight = Column(Float, default=0)
    net_weight = Column(Float, default=0)
    price_per_kg = Column(Float, default=0)
    amount = Column(Float, default=0)
    supervisor = Column(String)
    notes = Column(Text)


# ── بورصة الأسعار ──────────────────────────────────────────
class PriceBoard(Base):
    __tablename__ = "price_board"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)
    item_code = Column(String)
    item_name = Column(String)
    buy_price = Column(Float, default=0)
    sell_price = Column(Float, default=0)
    currency = Column(String, default="د.ل")
    exchange_rate = Column(Float, default=1)


# ── الذمم ──────────────────────────────────────────────────
class Receivable(Base):
    __tablename__ = "receivables"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String)  # 'supplier' or 'customer'
    party_name = Column(String)
    date = Column(Date)
    description = Column(String)
    amount = Column(Float, default=0)
    paid = Column(Float, default=0)
    remaining = Column(Float, default=0)
    notes = Column(Text)


# ── العهدة ─────────────────────────────────────────────────
class Custody(Base):
    __tablename__ = "custody"
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    date = Column(Date)
    amount = Column(Float, default=0)
    notes = Column(Text)


# ── تصنيفات المصروفات ──────────────────────────────────────
class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


# ── حكية أبو احمد ──────────────────────────────────────────
class Hakiya(Base):
    __tablename__ = "hakiya"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)
    type = Column(String)  # 'نضيفة' or 'محروقة'
    quantity = Column(Float, default=0)
    buy_price = Column(Float, default=0)
    total_buy = Column(Float, default=0)
    sell_price = Column(Float, default=0)
    total_sell = Column(Float, default=0)
    profit = Column(Float, default=0)
    notes = Column(Text)


# ── ورشفانة ────────────────────────────────────────────────
class Warshfana(Base):
    __tablename__ = "warshfana"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=True)
    item_type = Column(String)
    weight = Column(Float, default=0)
    price_per_kg = Column(Float, default=0)
    total = Column(Float, default=0)
    driver_discount = Column(Float, default=0)
    paid = Column(Float, default=0)
    remaining = Column(Float, default=0)
    notes = Column(Text)


# ── الملاحظات ───────────────────────────────────────────────
class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    color = Column(String, default="yellow")  # yellow, blue, green, red, purple
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ── المهام (Todo) ───────────────────────────────────────────
class Todo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task = Column(String, nullable=False)
    done = Column(Boolean, default=False)
    priority = Column(String, default="normal")  # high, normal, low
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── المستخدمون ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String, nullable=False)
    email        = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role         = Column(String, default="user")   # "admin" | "user"
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


# ── القائمة السوداء للتوكنات (لـ logout) ────────────────────
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    jti        = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)
