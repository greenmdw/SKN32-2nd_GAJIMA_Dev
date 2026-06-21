# -*- coding: utf-8 -*-
"""db/migrate — schema_mysql.sql 적용(15테이블). 실행: python db/migrate.py
.env(MYSQL_*) 필요. 주석/빈 줄 제거 후 세미콜론 단위 실행(Node migrate.js 포팅)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import MYSQL                                      # noqa: E402


def main():
    if not MYSQL:
        print("[migrate] MYSQL 미설정(.env). 중단.")
        return 1
    import mysql.connector
    sql_path = Path(__file__).resolve().parent / "schema_mysql.sql"
    raw = sql_path.read_text(encoding="utf-8")
    body = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("--"))
    stmts = [s.strip() for s in body.split(";") if s.strip()]
    conn = mysql.connector.connect(charset="utf8mb4", **MYSQL)
    cur = conn.cursor()
    ok = 0
    for s in stmts:
        cur.execute(s)
        ok += 1
    conn.commit()
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    print(f"[migrate] {ok}/{len(stmts)} statements 적용. 테이블 {len(tables)}개: {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
