import os
import sqlite3
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "data.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "yunnan-employment-demo-secret"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            enterprise_name TEXT NOT NULL,
            region TEXT NOT NULL,
            report_type TEXT NOT NULL,
            employee_count INTEGER NOT NULL,
            new_employment INTEGER NOT NULL,
            resignation_count INTEGER NOT NULL,
            recruitment_need INTEGER NOT NULL,
            remark TEXT,
            status TEXT NOT NULL DEFAULT '待审核',
            review_comment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    default_users = [
        ("enterprise1", "123456", "enterprise"),
        ("reviewer1", "123456", "reviewer"),
        ("admin1", "123456", "admin"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        default_users,
    )

    db.commit()
    db.close()


def login_required(roles=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                flash("无权限访问该页面")
                return redirect(url_for("home"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def analyze_record(record):
    employee_count = record["employee_count"]
    new_employment = record["new_employment"]
    resignation_count = record["resignation_count"]
    recruitment_need = record["recruitment_need"]

    flags = []
    suggestions = []

    if employee_count > 0 and resignation_count > employee_count * 0.5:
        flags.append("离职率过高，疑似异常")
        suggestions.append("建议重点核查企业近期人员流失原因，必要时要求补充说明")

    if recruitment_need > max(20, employee_count * 0.8):
        flags.append("招聘需求波动较大")
        suggestions.append("建议关注岗位结构变化，核实是否存在集中扩招计划")

    if new_employment <= 3 and resignation_count <= 3 and recruitment_need <= 10:
        flags.append("数据基本正常")
        suggestions.append("可按常规流程审核通过")

    if not flags:
        flags.append("未发现明显异常")
        suggestions.append("建议结合历史数据进行人工复核后处理")

    analysis_text = (
        f"企业【{record['enterprise_name']}】本期在职 {employee_count} 人，"
        f"新增就业 {new_employment} 人，离职 {resignation_count} 人，招聘需求 {recruitment_need} 人。"
        f"系统判断：{'; '.join(flags)}。"
    )
    suggestion_text = "；".join(suggestions)
    return analysis_text, suggestion_text


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session.get("role")
    if role == "enterprise":
        return redirect(url_for("enterprise_report"))
    if role == "reviewer":
        return redirect(url_for("review_list"))
    return redirect(url_for("stats"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))

        flash("用户名或密码错误")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/enterprise/report", methods=["GET", "POST"])
@login_required(roles=["enterprise"])
def enterprise_report():
    db = get_db()
    if request.method == "POST":
        form = request.form
        db.execute(
            """
            INSERT INTO employment_records (
                user_id, enterprise_name, region, report_type,
                employee_count, new_employment, resignation_count,
                recruitment_need, remark, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '待审核')
            """,
            (
                session["user_id"],
                form.get("enterprise_name", "").strip(),
                form.get("region", "").strip(),
                form.get("report_type", "").strip(),
                int(form.get("employee_count", 0)),
                int(form.get("new_employment", 0)),
                int(form.get("resignation_count", 0)),
                int(form.get("recruitment_need", 0)),
                form.get("remark", "").strip(),
            ),
        )
        db.commit()
        flash("填报成功，已提交审核")
        return redirect(url_for("enterprise_report"))

    records = db.execute(
        """
        SELECT id, enterprise_name, region, report_type, status, created_at
        FROM employment_records
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    return render_template("enterprise_form.html", records=records)


@app.route("/review/list")
@login_required(roles=["reviewer", "admin"])
def review_list():
    db = get_db()
    records = db.execute(
        """
        SELECT id, enterprise_name, region, report_type, employee_count,
               new_employment, resignation_count, recruitment_need,
               status, created_at
        FROM employment_records
        ORDER BY id DESC
        """
    ).fetchall()
    return render_template("review_list.html", records=records)


@app.route("/review/<int:record_id>", methods=["GET", "POST"])
@login_required(roles=["reviewer", "admin"])
def review_detail(record_id):
    db = get_db()
    record = db.execute(
        "SELECT * FROM employment_records WHERE id = ?", (record_id,)
    ).fetchone()

    if not record:
        flash("记录不存在")
        return redirect(url_for("review_list"))

    if request.method == "POST":
        action = request.form.get("action")
        comment = request.form.get("review_comment", "").strip()

        if action == "approve":
            status = "已通过"
        elif action == "reject":
            status = "已退回"
        else:
            flash("无效操作")
            return redirect(url_for("review_detail", record_id=record_id))

        db.execute(
            "UPDATE employment_records SET status = ?, review_comment = ? WHERE id = ?",
            (status, comment, record_id),
        )
        db.commit()
        flash("审核结果已保存")
        return redirect(url_for("review_detail", record_id=record_id))

    analysis_text, suggestion_text = analyze_record(record)
    return render_template(
        "review_detail.html",
        record=record,
        analysis_text=analysis_text,
        suggestion_text=suggestion_text,
    )


@app.route("/stats")
@login_required(roles=["reviewer", "admin"])
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS c FROM employment_records").fetchone()["c"]
    approved = db.execute(
        "SELECT COUNT(*) AS c FROM employment_records WHERE status = '已通过'"
    ).fetchone()["c"]
    pending = db.execute(
        "SELECT COUNT(*) AS c FROM employment_records WHERE status = '待审核'"
    ).fetchone()["c"]
    rejected = db.execute(
        "SELECT COUNT(*) AS c FROM employment_records WHERE status = '已退回'"
    ).fetchone()["c"]

    totals = db.execute(
        """
        SELECT
            COALESCE(SUM(employee_count), 0) AS employee_total,
            COALESCE(SUM(new_employment), 0) AS new_total,
            COALESCE(SUM(resignation_count), 0) AS resignation_total,
            COALESCE(SUM(recruitment_need), 0) AS recruitment_total
        FROM employment_records
        """
    ).fetchone()

    employee_total = totals["employee_total"]
    new_total = totals["new_total"]
    resignation_total = totals["resignation_total"]
    recruitment_total = totals["recruitment_total"]
    net_growth = new_total - resignation_total
    approval_rate = (approved / total * 100) if total else 0
    resignation_rate = (resignation_total / employee_total * 100) if employee_total else 0

    high_risk_count = db.execute(
        """
        SELECT COUNT(*) AS c
        FROM employment_records
        WHERE (employee_count > 0 AND resignation_count > employee_count * 0.5)
           OR recruitment_need > MAX(20, employee_count * 0.8)
        """
    ).fetchone()["c"]

    region_stats = db.execute(
        """
        SELECT
            region,
            COUNT(*) AS record_count,
            COALESCE(SUM(employee_count), 0) AS employee_total,
            COALESCE(SUM(new_employment), 0) AS new_total,
            COALESCE(SUM(resignation_count), 0) AS resignation_total,
            COALESCE(SUM(recruitment_need), 0) AS recruitment_total
        FROM employment_records
        GROUP BY region
        ORDER BY record_count DESC
        """
    ).fetchall()
    report_type_stats = db.execute(
        """
        SELECT
            report_type,
            COUNT(*) AS record_count,
            COALESCE(SUM(new_employment), 0) AS new_total,
            COALESCE(SUM(resignation_count), 0) AS resignation_total
        FROM employment_records
        GROUP BY report_type
        ORDER BY record_count DESC
        """
    ).fetchall()

    latest_records = db.execute(
        """
        SELECT id, enterprise_name, region, new_employment, resignation_count, status, created_at
        FROM employment_records
        ORDER BY id DESC
        LIMIT 5
        """
    ).fetchall()

    trend_rows = db.execute(
        """
        SELECT
            DATE(created_at) AS report_date,
            COUNT(*) AS record_count,
            COALESCE(SUM(new_employment), 0) AS new_total,
            COALESCE(SUM(resignation_count), 0) AS resignation_total,
            COALESCE(SUM(recruitment_need), 0) AS recruitment_total
        FROM employment_records
        WHERE DATE(created_at) >= DATE('now', '-13 day')
        GROUP BY DATE(created_at)
        ORDER BY report_date
        """
    ).fetchall()

    # 没有近14天数据时，回退展示全部日期趋势
    if not trend_rows:
        trend_rows = db.execute(
            """
            SELECT
                DATE(created_at) AS report_date,
                COUNT(*) AS record_count,
                COALESCE(SUM(new_employment), 0) AS new_total,
                COALESCE(SUM(resignation_count), 0) AS resignation_total,
                COALESCE(SUM(recruitment_need), 0) AS recruitment_total
            FROM employment_records
            GROUP BY DATE(created_at)
            ORDER BY report_date
            """
        ).fetchall()

    max_trend_value = 1
    trend_data = []
    for row in trend_rows:
        net_total = row["new_total"] - row["resignation_total"]
        max_trend_value = max(
            max_trend_value,
            row["new_total"],
            row["resignation_total"],
            row["recruitment_total"],
            abs(net_total),
        )
        trend_data.append(
            {
                "report_date": row["report_date"],
                "record_count": row["record_count"],
                "new_total": row["new_total"],
                "resignation_total": row["resignation_total"],
                "recruitment_total": row["recruitment_total"],
                "net_total": net_total,
            }
        )

    for item in trend_data:
        item["new_pct"] = int(item["new_total"] * 100 / max_trend_value) if max_trend_value else 0
        item["resignation_pct"] = int(item["resignation_total"] * 100 / max_trend_value) if max_trend_value else 0
        item["recruitment_pct"] = int(item["recruitment_total"] * 100 / max_trend_value) if max_trend_value else 0

    return render_template(
        "stats.html",
        total=total,
        approved=approved,
        pending=pending,
        rejected=rejected,
        employee_total=employee_total,
        new_total=new_total,
        resignation_total=resignation_total,
        recruitment_total=recruitment_total,
        net_growth=net_growth,
        approval_rate=approval_rate,
        resignation_rate=resignation_rate,
        high_risk_count=high_risk_count,
        region_stats=region_stats,
        report_type_stats=report_type_stats,
        latest_records=latest_records,
        trend_data=trend_data,
    )


@app.route("/agent", methods=["GET", "POST"])
@login_required(roles=["reviewer", "admin"])
def agent():
    db = get_db()
    records = db.execute(
        "SELECT id, enterprise_name, created_at FROM employment_records ORDER BY id DESC"
    ).fetchall()

    selected_record = None
    analysis_text = None
    suggestion_text = None

    if request.method == "POST":
        record_id = request.form.get("record_id", type=int)
        if record_id:
            selected_record = db.execute(
                "SELECT * FROM employment_records WHERE id = ?", (record_id,)
            ).fetchone()
            if selected_record:
                analysis_text, suggestion_text = analyze_record(selected_record)

    return render_template(
        "agent.html",
        records=records,
        selected_record=selected_record,
        analysis_text=analysis_text,
        suggestion_text=suggestion_text,
    )


@app.context_processor
def inject_user():
    return {
        "session_user": {
            "username": session.get("username"),
            "role": session.get("role"),
        }
    }


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
