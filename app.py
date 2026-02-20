from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from flask import Flask, abort, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db.sqlite3"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def query(sql: str, params: Iterable[Any] = (), one: bool = False):
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql: str, params: Iterable[Any] = ()):
    with get_conn() as conn:
        conn.execute(sql, tuple(params))
        conn.commit()


def init_db():
    """
    Initialize DB without wiping existing data.
    - Ensures base tables exist (schema.sql)
    - Applies lightweight migrations (adds missing columns)
    """
    # 1) Ensure file exists
    if not DB_PATH.exists():
        DB_PATH.touch()

    # 2) Ensure core tables exist
    schema_path = BASE_DIR / "schema.sql"
    if schema_path.exists():
        with get_conn() as conn, open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            conn.commit()

    # 3) Migrations: add columns if missing
    def has_column(table: str, col: str) -> bool:
        cols = query(f"PRAGMA table_info({table});")
        return any(r["name"] == col for r in cols)

    # user
    if not has_column("user", "CreatedAt"):
        execute("ALTER TABLE user ADD COLUMN CreatedAt TEXT;")
        execute("UPDATE user SET CreatedAt = COALESCE(CreatedAt, datetime('now'))")

    # menu
    if not has_column("menu", "Category"):
        execute("ALTER TABLE menu ADD COLUMN Category TEXT DEFAULT 'عمومی';")
    if not has_column("menu", "IsAvailable"):
        execute("ALTER TABLE menu ADD COLUMN IsAvailable INTEGER DEFAULT 1;")

    # checkout
    if not has_column("checkout", "CreatedAt"):
        execute("ALTER TABLE checkout ADD COLUMN CreatedAt TEXT;")
        execute("UPDATE checkout SET CreatedAt = COALESCE(CreatedAt, datetime('now'))")
    if not has_column("checkout", "Status"):
        execute("ALTER TABLE checkout ADD COLUMN Status TEXT DEFAULT 'در انتظار';")
    if not has_column("checkout", "Notes"):
        execute("ALTER TABLE checkout ADD COLUMN Notes TEXT;")

    # legacy table clean-up is intentionally avoided (keep existing data)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Ensure DB is ready even when using `flask run`
init_db()


@app.template_filter("money")
def money(v):
    try:
        return f"{int(v):,}"
    except Exception:
        return v


def fetch_dashboard_data():
    items = query(
        """
        SELECT ID, Name, Price, Category, IsAvailable
        FROM menu
        ORDER BY ID DESC
        """
    )
    customers = query(
        """
        SELECT ID, FirstName, LastName, Phone, CreatedAt
        FROM user
        ORDER BY ID DESC
        """
    )
    orders = query(
        """
        SELECT
            c.ID            AS OrderID,
            c.quantity      AS Quantity,
            c.ItemPrice     AS ItemPrice,
            c.TotalPrice    AS TotalPrice,
            c.Status        AS Status,
            c.Notes         AS Notes,
            c.CreatedAt     AS CreatedAt,
            u.ID            AS UserID,
            u.FirstName     AS FirstName,
            u.LastName      AS LastName,
            u.Phone         AS Phone,
            m.ID            AS ItemID,
            m.Name          AS ItemName,
            m.Category      AS Category
        FROM checkout c
        JOIN user u ON u.ID = c.UserID
        JOIN menu m ON m.ID = c.ItemID
        ORDER BY c.ID DESC
        """
    )

    total_customers = query("SELECT COUNT(*) AS C FROM user", one=True)["C"]
    total_items = query("SELECT COUNT(*) AS C FROM menu", one=True)["C"]
    total_orders = query("SELECT COUNT(*) AS C FROM checkout", one=True)["C"]
    total_revenue = query("SELECT COALESCE(SUM(TotalPrice), 0) AS S FROM checkout", one=True)["S"]

    stats = {
        "customers": total_customers,
        "items": total_items,
        "orders": total_orders,
        "revenue": total_revenue,
    }
    return items, customers, orders, stats


@app.get("/")
def welcome():
    return render_template("welcome.html")


@app.get("/dashboard")
def dashboard():
    items, customers, orders, stats = fetch_dashboard_data()
    return render_template("dashboard.html", items=items, customers=customers, orders=orders, stats=stats)


# -------------------------
# Menu CRUD
# -------------------------
@app.post("/menu")
def menu_create():
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "عمومی").strip()
    price_raw = (request.form.get("price") or "0").strip()
    is_available = 1 if request.form.get("is_available") == "on" else 0

    if not name:
        flash("نام آیتم نمی‌تواند خالی باشد.", "danger")
        return redirect(url_for("dashboard"))

    try:
        price = int(price_raw)
        if price < 0:
            raise ValueError
    except ValueError:
        flash("قیمت نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    execute(
        "INSERT INTO menu(Name, Price, Category, IsAvailable) VALUES (?, ?, ?, ?)",
        (name, price, category, is_available),
    )
    flash("آیتم منو با موفقیت اضافه شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/menu/<int:item_id>/update")
def menu_update(item_id: int):
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "عمومی").strip()
    price_raw = (request.form.get("price") or "0").strip()
    is_available = 1 if request.form.get("is_available") == "on" else 0

    exists = query("SELECT ID FROM menu WHERE ID = ?", (item_id,), one=True)
    if not exists:
        abort(404)

    if not name:
        flash("نام آیتم نمی‌تواند خالی باشد.", "danger")
        return redirect(url_for("dashboard"))

    try:
        price = int(price_raw)
        if price < 0:
            raise ValueError
    except ValueError:
        flash("قیمت نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    execute(
        "UPDATE menu SET Name = ?, Price = ?, Category = ?, IsAvailable = ? WHERE ID = ?",
        (name, price, category, is_available, item_id),
    )
    flash("آیتم منو بروزرسانی شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/menu/<int:item_id>/delete")
def menu_delete(item_id: int):
    # First delete related orders to prevent FK issues
    execute("DELETE FROM checkout WHERE ItemID = ?", (item_id,))
    execute("DELETE FROM menu WHERE ID = ?", (item_id,))
    flash("آیتم منو حذف شد.", "success")
    return redirect(url_for("dashboard"))


# -------------------------
# Customer CRUD
# -------------------------
@app.post("/customers")
def customer_create():
    first = (request.form.get("first_name") or "").strip()
    last = (request.form.get("last_name") or "").strip()
    phone_raw = (request.form.get("phone") or "").strip()

    if not first or not last:
        flash("نام و نام خانوادگی الزامی است.", "danger")
        return redirect(url_for("dashboard"))

    try:
        phone = int(phone_raw)
        if phone <= 0:
            raise ValueError
    except ValueError:
        flash("شماره تماس نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    execute(
        "INSERT INTO user(FirstName, LastName, Phone, CreatedAt) VALUES (?, ?, ?, datetime('now'))",
        (first, last, phone),
    )
    flash("مشتری با موفقیت اضافه شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/customers/<int:user_id>/update")
def customer_update(user_id: int):
    first = (request.form.get("first_name") or "").strip()
    last = (request.form.get("last_name") or "").strip()
    phone_raw = (request.form.get("phone") or "").strip()

    exists = query("SELECT ID FROM user WHERE ID = ?", (user_id,), one=True)
    if not exists:
        abort(404)

    if not first or not last:
        flash("نام و نام خانوادگی الزامی است.", "danger")
        return redirect(url_for("dashboard"))

    try:
        phone = int(phone_raw)
        if phone <= 0:
            raise ValueError
    except ValueError:
        flash("شماره تماس نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    execute(
        "UPDATE user SET FirstName = ?, LastName = ?, Phone = ? WHERE ID = ?",
        (first, last, phone, user_id),
    )
    flash("اطلاعات مشتری بروزرسانی شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/customers/<int:user_id>/delete")
def customer_delete(user_id: int):
    execute("DELETE FROM checkout WHERE UserID = ?", (user_id,))
    execute("DELETE FROM user WHERE ID = ?", (user_id,))
    flash("مشتری حذف شد.", "success")
    return redirect(url_for("dashboard"))


# -------------------------
# Order CRUD
# -------------------------
@app.post("/orders")
def order_create():
    user_id = (request.form.get("user_id") or "").strip()
    item_id = (request.form.get("item_id") or "").strip()
    qty_raw = (request.form.get("quantity") or "1").strip()
    status = (request.form.get("status") or "در انتظار").strip()
    notes = (request.form.get("notes") or "").strip() or None

    try:
        user_id_i = int(user_id)
        item_id_i = int(item_id)
        qty = int(qty_raw)
        if qty <= 0:
            raise ValueError
    except ValueError:
        flash("اطلاعات سفارش نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    item = query("SELECT Price FROM menu WHERE ID = ?", (item_id_i,), one=True)
    if not item:
        flash("آیتم انتخاب‌شده وجود ندارد.", "danger")
        return redirect(url_for("dashboard"))

    item_price = int(item["Price"] or 0)
    total = item_price * qty

    execute(
        """
        INSERT INTO checkout(UserID, quantity, ItemID, ItemPrice, TotalPrice, Status, Notes, CreatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (user_id_i, qty, item_id_i, item_price, total, status, notes),
    )
    flash("سفارش ثبت شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/orders/<int:order_id>/update")
def order_update(order_id: int):
    user_id = (request.form.get("user_id") or "").strip()
    item_id = (request.form.get("item_id") or "").strip()
    qty_raw = (request.form.get("quantity") or "1").strip()
    status = (request.form.get("status") or "در انتظار").strip()
    notes = (request.form.get("notes") or "").strip() or None

    exists = query("SELECT ID FROM checkout WHERE ID = ?", (order_id,), one=True)
    if not exists:
        abort(404)

    try:
        user_id_i = int(user_id)
        item_id_i = int(item_id)
        qty = int(qty_raw)
        if qty <= 0:
            raise ValueError
    except ValueError:
        flash("اطلاعات سفارش نامعتبر است.", "danger")
        return redirect(url_for("dashboard"))

    item = query("SELECT Price FROM menu WHERE ID = ?", (item_id_i,), one=True)
    if not item:
        flash("آیتم انتخاب‌شده وجود ندارد.", "danger")
        return redirect(url_for("dashboard"))

    item_price = int(item["Price"] or 0)
    total = item_price * qty

    execute(
        """
        UPDATE checkout
        SET UserID = ?, quantity = ?, ItemID = ?, ItemPrice = ?, TotalPrice = ?, Status = ?, Notes = ?
        WHERE ID = ?
        """,
        (user_id_i, qty, item_id_i, item_price, total, status, notes, order_id),
    )
    flash("سفارش بروزرسانی شد.", "success")
    return redirect(url_for("dashboard"))


@app.post("/orders/<int:order_id>/delete")
def order_delete(order_id: int):
    execute("DELETE FROM checkout WHERE ID = ?", (order_id,))
    flash("سفارش حذف شد.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(404)
def not_found(_):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
