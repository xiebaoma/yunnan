import sqlite3

DB_PATH = "data.db"

records = [
    (1, "昆明云能科技有限公司", "昆明", "月报", 120, 8, 5, 20, "业务稳定", "待审核", ""),
    (1, "曲靖智造产业有限公司", "曲靖", "周报", 60, 1, 35, 55, "新线投产，人员调整", "待审核", ""),
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO employment_records (
            user_id, enterprise_name, region, report_type,
            employee_count, new_employment, resignation_count,
            recruitment_need, remark, status, review_comment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    conn.commit()
    conn.close()
    print("演示数据已插入")


if __name__ == "__main__":
    seed()
