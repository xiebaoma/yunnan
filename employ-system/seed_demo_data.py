import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data.db"


def build_records():
    base_date = datetime.now() - timedelta(days=19)
    enterprises = [
        ("昆明云能科技有限公司", "昆明"),
        ("曲靖智造产业有限公司", "曲靖"),
        ("玉溪新材料制造公司", "玉溪"),
        ("昭通农产加工企业", "昭通"),
        ("大理文旅服务集团", "大理"),
    ]

    records = []
    for i in range(20):
        enterprise_name, region = enterprises[i % len(enterprises)]
        report_type = "周报" if i % 2 == 0 else "月报"
        employee_count = 80 + (i % 7) * 15
        new_employment = 3 + (i % 6)
        resignation_count = 1 + (i % 5)
        recruitment_need = 8 + (i % 8) * 3

        # 制造少量异常样本，便于课堂展示 Agent 和统计风险指标
        if i in (6, 13, 18):
            resignation_count = max(resignation_count, int(employee_count * 0.6))
        if i in (4, 11, 17):
            recruitment_need = max(recruitment_need, int(employee_count * 0.9))

        status = "待审核"
        review_comment = ""
        if i % 4 == 0:
            status = "已通过"
            review_comment = "数据合理，审核通过"
        elif i % 7 == 0:
            status = "已退回"
            review_comment = "建议补充人员变动说明"

        created_at = (base_date + timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
        remark = f"演示样本数据第{i + 1}条"

        records.append(
            (
                1,
                enterprise_name,
                region,
                report_type,
                employee_count,
                new_employment,
                resignation_count,
                recruitment_need,
                remark,
                status,
                review_comment,
                created_at,
            )
        )

    return records


def seed(reset=True):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if reset:
        cur.execute("DELETE FROM employment_records")

    records = build_records()
    cur.executemany(
        """
        INSERT INTO employment_records (
            user_id, enterprise_name, region, report_type,
            employee_count, new_employment, resignation_count,
            recruitment_need, remark, status, review_comment, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )

    conn.commit()
    conn.close()
    print(f"已写入 {len(records)} 条演示数据")


if __name__ == "__main__":
    seed(reset=True)
