from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
from datetime import datetime
import csv
import io
import sqlite3

app = Flask(__name__)

DATABASE = "newcreatestudio.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    # =========================
    # 顧客管理
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT,
            phone TEXT,
            category TEXT NOT NULL DEFAULT '検討者',
            status TEXT NOT NULL DEFAULT '未対応',
            memo TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # =========================
    # お問い合わせ
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # =========================
    # 予約可能日時
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservation_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # =========================
    # 打ち合わせ予約
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            meeting_type TEXT NOT NULL,
            message TEXT,
            status TEXT NOT NULL DEFAULT '予約受付',
            created_at TEXT NOT NULL,
            FOREIGN KEY (slot_id) REFERENCES reservation_slots(id)
        )
    """)

    # =========================
    # 案件管理
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            project_type TEXT,
            amount INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT '問い合わせ',
            start_date TEXT,
            due_date TEXT,
            memo TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()

app.secret_key = "newcreatestudio-production-key"


# =========================
# 共通
# =========================

@app.context_processor
def inject_year():
    return {"current_year": datetime.now().year}


# =========================
# 通常ページ
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/company")
def company():
    return render_template("company.html")


@app.route("/service")
def service():
    return render_template("service.html")


@app.route("/works")
def works():
    return render_template("works.html")


@app.route("/sample")
def sample():
    return render_template("sample.html")


@app.route("/price")
def price():
    return render_template("price.html")


@app.route("/staff")
def staff():
    return render_template("staff.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("必須項目を入力してください。", "error")
            return redirect(url_for("contact"))

        conn = get_db()

        conn.execute(
            """
            INSERT INTO contacts
            (name, email, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        conn.commit()
        conn.close()

        flash(
            "お問い合わせありがとうございます。内容を確認のうえご連絡いたします。",
            "success"
        )

        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# =========================
# 管理画面ログイン
# =========================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "admin" and password == "studio123":

            session["admin_logged_in"] = True

            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            error="IDまたはパスワードが違います。"
        )

    return render_template("admin_login.html")


# =========================
# 管理画面
# =========================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("admin.html")

@app.route("/admin/contacts")
def admin_contacts():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    contacts = conn.execute(
        """
        SELECT *
        FROM contacts
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_contacts.html",
        contacts=contacts
    )

# =========================
# 顧客管理
# =========================

@app.route("/admin/customers")
def admin_customers():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    keyword = request.args.get("keyword", "").strip()

    conn = get_db()

    if keyword:
        customers = conn.execute(
            """
            SELECT *
            FROM customers
            WHERE
                name LIKE ?
                OR company LIKE ?
                OR email LIKE ?
                OR phone LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%"
            )
        ).fetchall()
    else:
        customers = conn.execute(
            """
            SELECT *
            FROM customers
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "admin_customers.html",
        customers=customers,
        keyword=keyword
    )
# =========================
# 顧客登録
# =========================

@app.route(
    "/admin/customers/new",
    methods=["GET", "POST"]
)
def admin_customer_new():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        company = request.form.get(
            "company",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        category = request.form.get(
            "category",
            "検討者"
        ).strip()

        status = request.form.get(
            "status",
            "未対応"
        ).strip()

        memo = request.form.get(
            "memo",
            ""
        ).strip()

        if not name:

            flash(
                "顧客名を入力してください。",
                "error"
            )

            return redirect(
                url_for("admin_customer_new")
            )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO customers
            (
                name,
                company,
                email,
                phone,
                category,
                status,
                memo,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                company,
                email,
                phone,
                category,
                status,
                memo,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()
        conn.close()

        flash(
            "顧客を登録しました。",
            "success"
        )

        return redirect(
            url_for("admin_customers")
        )

    return render_template(
        "admin_customer_form.html",
        customer=None
    )
# =========================
# 顧客編集
# =========================

@app.route("/admin/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def admin_customer_edit(customer_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    customer = conn.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()

    if not customer:
        conn.close()

        flash(
            "顧客情報が見つかりません。",
            "error"
        )

        return redirect(
            url_for("admin_customers")
        )

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        company = request.form.get("company", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        status = request.form.get("status", "").strip()
        memo = request.form.get("memo", "").strip()

        if not name:
            conn.close()

            flash(
                "名前を入力してください。",
                "error"
            )

            return redirect(
                url_for(
                    "admin_customer_edit",
                    customer_id=customer_id
                )
            )

        conn.execute(
            """
            UPDATE customers
            SET
                name = ?,
                company = ?,
                email = ?,
                phone = ?,
                category = ?,
                status = ?,
                memo = ?
            WHERE id = ?
            """,
            (
                name,
                company,
                email,
                phone,
                category,
                status,
                memo,
                customer_id
            )
        )

        conn.commit()
        conn.close()

        flash(
            "顧客情報を更新しました。",
            "success"
        )

        return redirect(
            url_for("admin_customers")
        )

    conn.close()

    return render_template(
        "admin_customer_edit.html",
        customer=customer
    )
# =========================
# 顧客削除
# =========================

@app.route("/admin/customers/delete/<int:customer_id>")
def admin_customer_delete(customer_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "顧客を削除しました。",
        "success"
    )

    return redirect(
        url_for("admin_customers")
    )

# =========================
# 予約可能日時管理
# =========================

@app.route("/admin/reservation-slots", methods=["GET", "POST"])
def admin_reservation_slots():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    # -------------------------
    # 予約可能日時を登録
    # -------------------------
    if request.method == "POST":

        reservation_date = request.form.get(
            "reservation_date",
            ""
        ).strip()

        reservation_time = request.form.get(
            "reservation_time",
            ""
        ).strip()

        if not reservation_date or not reservation_time:
            flash(
                "日付と時間を入力してください。",
                "error"
            )

            conn.close()

            return redirect(
                url_for("admin_reservation_slots")
            )

        # 同じ日時がすでに登録されているか確認
        existing = conn.execute(
            """
            SELECT *
            FROM reservation_slots
            WHERE reservation_date = ?
            AND reservation_time = ?
            """,
            (
                reservation_date,
                reservation_time
            )
        ).fetchone()

        if existing:
            flash(
                "その日時はすでに登録されています。",
                "error"
            )

            conn.close()

            return redirect(
                url_for("admin_reservation_slots")
            )

        # 登録
        conn.execute(
            """
            INSERT INTO reservation_slots
            (
                reservation_date,
                reservation_time,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                reservation_date,
                reservation_time,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()

        flash(
            "予約可能日時を登録しました。",
            "success"
        )

    # -------------------------
    # 予約可能日時一覧
    # -------------------------

    slots = conn.execute(
        """
        SELECT
            reservation_slots.*,

            (
                SELECT COUNT(*)
                FROM reservations
                WHERE reservations.slot_id =
                      reservation_slots.id
            ) AS reservation_count

        FROM reservation_slots

        ORDER BY
            reservation_date ASC,
            reservation_time ASC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_reservation_slots.html",
        slots=slots
    )


# =========================
# 予約可能日時削除
# =========================

@app.route(
    "/admin/reservation-slots/delete/<int:slot_id>"
)
def delete_reservation_slot(slot_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    # 予約が入っているか確認
    reservation = conn.execute(
        """
        SELECT *
        FROM reservations
        WHERE slot_id = ?
        """,
        (slot_id,)
    ).fetchone()

    if reservation:

        flash(
            "すでに予約が入っている日時は削除できません。",
            "error"
        )

        conn.close()

        return redirect(
            url_for("admin_reservation_slots")
        )

    conn.execute(
        """
        DELETE FROM reservation_slots
        WHERE id = ?
        """,
        (slot_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "予約可能日時を削除しました。",
        "success"
    )

    return redirect(
        url_for("admin_reservation_slots")
    )

# =========================
# 打ち合わせ予約一覧
# =========================

@app.route("/admin/reservations")
def admin_reservations():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    reservations = conn.execute(
        """
        SELECT
            reservations.*,
            reservation_slots.reservation_date,
            reservation_slots.reservation_time
        FROM reservations
        INNER JOIN reservation_slots
            ON reservations.slot_id = reservation_slots.id
        ORDER BY
            reservation_slots.reservation_date ASC,
            reservation_slots.reservation_time ASC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_reservations.html",
        reservations=reservations
    )


# =========================
# 予約者を顧客として登録
# =========================

@app.route(
    "/admin/reservations/customer/<int:reservation_id>"
)
def reservation_to_customer(reservation_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    reservation = conn.execute(
        """
        SELECT
            reservations.*,
            reservation_slots.reservation_date,
            reservation_slots.reservation_time
        FROM reservations
        INNER JOIN reservation_slots
            ON reservations.slot_id = reservation_slots.id
        WHERE reservations.id = ?
        """,
        (reservation_id,)
    ).fetchone()

    if not reservation:

        conn.close()

        flash(
            "予約情報が見つかりません。",
            "error"
        )

        return redirect(
            url_for("admin_reservations")
        )

    existing_customer = conn.execute(
        """
        SELECT *
        FROM customers
        WHERE email = ?
        LIMIT 1
        """,
        (reservation["email"],)
    ).fetchone()

    if existing_customer:

        conn.close()

        flash(
            "このお客様はすでに顧客登録されています。",
            "error"
        )

        return redirect(
            url_for("admin_customers")
        )

    conn.execute(
        """
        INSERT INTO customers
        (
            name,
            company,
            email,
            phone,
            category,
            status,
            memo,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reservation["name"],
            "",
            reservation["email"],
            reservation["phone"] or "",
            "検討者",
            "商談中",
            (
                "打ち合わせ予約から登録。\n"
                f"打ち合わせ方法：{reservation['meeting_type']}\n"
                f"予約日時："
                f"{reservation['reservation_date']} "
                f"{reservation['reservation_time']}\n"
                f"相談内容："
                f"{reservation['message'] or 'なし'}"
            ),
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    conn.commit()
    conn.close()

    flash(
        "予約者を顧客として登録しました。",
        "success"
    )

    return redirect(
        url_for("admin_customers")
    )

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    reservations = conn.execute(
        """
        SELECT
            reservations.*,
            reservation_slots.reservation_date,
            reservation_slots.reservation_time
        FROM reservations
        INNER JOIN reservation_slots
            ON reservations.slot_id = reservation_slots.id
        ORDER BY
            reservation_slots.reservation_date ASC,
            reservation_slots.reservation_time ASC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_reservations.html",
        reservations=reservations
    )


# =========================
# 打ち合わせ予約削除
# =========================

@app.route(
    "/admin/reservations/delete/<int:reservation_id>"
)
def delete_reservation(reservation_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM reservations
        WHERE id = ?
        """,
        (reservation_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "打ち合わせ予約を削除しました。",
        "success"
    )

    return redirect(
        url_for("admin_reservations")
    )



    # =========================
    # 顧客管理
    # =========================
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT,
            phone TEXT,
            category TEXT NOT NULL DEFAULT '検討者',
            status TEXT NOT NULL DEFAULT '未対応',
            memo TEXT,
            created_at TEXT NOT NULL
        )
    """)


# =========================
# 案件管理
# =========================

@app.route("/admin/projects")
def admin_projects():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    keyword = request.args.get("keyword", "").strip()

    conn = get_db()

    if keyword:

        projects = conn.execute(
            """
            SELECT
                projects.*,
                customers.name AS customer_name,
                customers.company AS customer_company
            FROM projects
            INNER JOIN customers
                ON projects.customer_id = customers.id
            WHERE
                projects.project_name LIKE ?
                OR customers.name LIKE ?
                OR customers.company LIKE ?
                OR projects.project_type LIKE ?
                OR projects.status LIKE ?
                OR projects.memo LIKE ?
            ORDER BY projects.id DESC
            """,
            (
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%",
                f"%{keyword}%"
            )
        ).fetchall()

    else:

        projects = conn.execute(
            """
            SELECT
                projects.*,
                customers.name AS customer_name,
                customers.company AS customer_company
            FROM projects
            INNER JOIN customers
                ON projects.customer_id = customers.id
            ORDER BY projects.id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "admin_projects.html",
        projects=projects,
        keyword=keyword
    )


# =========================
# 案件登録
# =========================

@app.route("/admin/projects/new", methods=["GET", "POST"])
def admin_project_new():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    customers = conn.execute(
        """
        SELECT *
        FROM customers
        ORDER BY name ASC
        """
    ).fetchall()

    if request.method == "POST":

        customer_id = request.form.get("customer_id", "").strip()
        project_name = request.form.get("project_name", "").strip()
        project_type = request.form.get("project_type", "").strip()
        amount_text = request.form.get("amount", "0").strip()
        status = request.form.get("status", "問い合わせ").strip()
        start_date = request.form.get("start_date", "").strip()
        due_date = request.form.get("due_date", "").strip()
        memo = request.form.get("memo", "").strip()

        if not customer_id or not project_name:

            conn.close()

            flash(
                "顧客と案件名を入力してください。",
                "error"
            )

            return redirect(
                url_for("admin_project_new")
            )

        try:
            amount = int(amount_text or 0)

        except ValueError:

            conn.close()

            flash(
                "金額は数字で入力してください。",
                "error"
            )

            return redirect(
                url_for("admin_project_new")
            )

        conn.execute(
            """
            INSERT INTO projects
            (
                customer_id,
                project_name,
                project_type,
                amount,
                status,
                start_date,
                due_date,
                memo,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                project_name,
                project_type,
                amount,
                status,
                start_date,
                due_date,
                memo,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()
        conn.close()

        flash(
            "案件を登録しました。",
            "success"
        )

        return redirect(
            url_for("admin_projects")
        )

    conn.close()

    return render_template(
        "admin_project_new.html",
        customers=customers
    )


# =========================
# 案件編集
# =========================

@app.route(
    "/admin/projects/edit/<int:project_id>",
    methods=["GET", "POST"]
)
def edit_project(project_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    project = conn.execute(
        """
        SELECT *
        FROM projects
        WHERE id = ?
        """,
        (project_id,)
    ).fetchone()

    if not project:

        conn.close()

        flash(
            "案件が見つかりません。",
            "error"
        )

        return redirect(
            url_for("admin_projects")
        )

    customers = conn.execute(
        """
        SELECT *
        FROM customers
        ORDER BY name ASC
        """
    ).fetchall()

    if request.method == "POST":

        customer_id = request.form.get(
            "customer_id",
            ""
        ).strip()

        project_name = request.form.get(
            "project_name",
            ""
        ).strip()

        project_type = request.form.get(
            "project_type",
            ""
        ).strip()

        amount_text = request.form.get(
            "amount",
            "0"
        ).strip()

        status = request.form.get(
            "status",
            "問い合わせ"
        ).strip()

        start_date = request.form.get(
            "start_date",
            ""
        ).strip()

        due_date = request.form.get(
            "due_date",
            ""
        ).strip()

        memo = request.form.get(
            "memo",
            ""
        ).strip()

        if not customer_id or not project_name:

            conn.close()

            flash(
                "顧客と案件名を入力してください。",
                "error"
            )

            return redirect(
                url_for(
                    "edit_project",
                    project_id=project_id
                )
            )

        try:

            amount = int(
                amount_text or 0
            )

        except ValueError:

            conn.close()

            flash(
                "金額は数字で入力してください。",
                "error"
            )

            return redirect(
                url_for(
                    "edit_project",
                    project_id=project_id
                )
            )

        conn.execute(
            """
            UPDATE projects
            SET
                customer_id = ?,
                project_name = ?,
                project_type = ?,
                amount = ?,
                status = ?,
                start_date = ?,
                due_date = ?,
                memo = ?
            WHERE id = ?
            """,
            (
                customer_id,
                project_name,
                project_type,
                amount,
                status,
                start_date,
                due_date,
                memo,
                project_id
            )
        )

        conn.commit()
        conn.close()

        flash(
            "案件情報を更新しました。",
            "success"
        )

        return redirect(
            url_for("admin_projects")
        )

    conn.close()

    return render_template(
        "admin_project_edit.html",
        project=project,
        customers=customers
    )


# =========================
# 案件削除
# =========================

@app.route(
    "/admin/projects/delete/<int:project_id>",
    methods=["POST"]
)
def delete_project(project_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM projects
        WHERE id = ?
        """,
        (project_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "案件を削除しました。",
        "success"
    )

    return redirect(
        url_for("admin_projects")
    )


# =========================
# 案件CSV出力
# =========================
@app.route("/admin/projects/csv")
def export_projects_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    projects = conn.execute("""
        SELECT
            projects.*,
            customers.name AS customer_name,
            customers.company AS customer_company
        FROM projects
        LEFT JOIN customers
            ON projects.customer_id = customers.id
        ORDER BY projects.id DESC
    """).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "案件名",
        "顧客名",
        "会社名",
        "案件種類",
        "金額",
        "ステータス",
        "開始日",
        "納期",
        "メモ",
        "登録日時"
    ])

    for project in projects:
        writer.writerow([
            project["id"],
            project["project_name"],
            project["customer_name"],
            project["customer_company"],
            project["project_type"],
            project["amount"],
            project["status"],
            project["start_date"],
            project["due_date"],
            project["memo"],
            project["created_at"]
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers["Content-Disposition"] = (
        "attachment; filename=projects.csv"
    )

    return response

# =========================
# ログアウト
# =========================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))


# =========================
# アプリ起動
# =========================


    # =========================
# 打ち合わせ予約
# =========================

@app.route("/booking", methods=["GET", "POST"])
def booking():

    conn = get_db()

    if request.method == "POST":

        slot_id = request.form.get("slot_id")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        meeting_type = request.form.get("meeting_type", "").strip()
        message = request.form.get("message", "").strip()

        if not slot_id or not name or not email or not meeting_type:
            flash("必須項目を入力してください。", "error")
            conn.close()
            return redirect(url_for("booking"))

        # 選択した予約枠が存在するか確認
        slot = conn.execute(
            """
            SELECT *
            FROM reservation_slots
            WHERE id = ?
            """,
            (slot_id,)
        ).fetchone()

        if not slot:
            flash("選択した日時は利用できません。", "error")
            conn.close()
            return redirect(url_for("booking"))

        # すでに予約済みか確認
        existing = conn.execute(
            """
            SELECT *
            FROM reservations
            WHERE slot_id = ?
            """,
            (slot_id,)
        ).fetchone()

        if existing:
            flash("申し訳ありません。その日時はすでに予約されています。", "error")
            conn.close()
            return redirect(url_for("booking"))

        # 予約登録
        conn.execute(
            """
            INSERT INTO reservations
            (
                slot_id,
                name,
                email,
                phone,
                meeting_type,
                message,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slot_id,
                name,
                email,
                phone,
                meeting_type,
                message,
                "予約受付",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        conn.commit()
        conn.close()

        flash(
            "打ち合わせ予約を受け付けました。",
            "success"
        )

        return redirect(url_for("booking"))

    # 予約されていない日時だけ取得
    slots = conn.execute(
        """
        SELECT *
        FROM reservation_slots
        WHERE id NOT IN (
            SELECT slot_id
            FROM reservations
        )
        ORDER BY reservation_date, reservation_time
        """
    ).fetchall()

    conn.close()

    return render_template(
        "booking.html",
        slots=slots
    )

if __name__ == "__main__":
    app.run(debug=True)