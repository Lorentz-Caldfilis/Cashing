"""All SQL lives here; money remains integer cents and connections always close."""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from domain import validate_record, shift_month, summarize_records


class DatabaseError(Exception):
    """User-facing error; never repair corruption by discarding user data."""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()

    @contextmanager
    def _connection(self, *, create=False):
        connection = None
        try:
            uri = self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw")
            connection = sqlite3.connect(uri, uri=True, timeout=3)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 3000")
            with connection:
                yield connection
        except sqlite3.Error as exc:
            raise DatabaseError(
                "无法读写账单数据库。请检查磁盘空间、文件权限，或稍后重试。"
                "原有账单不会被自动清空。"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _checked_record(row):
        record = dict(row)
        try:
            text = record["datetime"]
            when = datetime.strptime(text, "%Y-%m-%d %H:%M")
            if when.isoformat(sep=" ", timespec="minutes") != text:
                raise ValueError("Noncanonical local time")
            validate_record(record["amount_cents"], when, record["category"], record["description"])
            if type(record["id"]) is not int or record["id"] <= 0:
                raise ValueError("Invalid record ID")
        except (ValueError, TypeError, KeyError) as exc:
            raise DatabaseError("数据库中有无效账单或时间格式，请保留文件并从备份检查；未修改原记录。") from exc
        return record

    def initialize_database(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError("无法创建数据目录，请检查该目录的写入权限。") from exc
        with self._connection(create=True) as con:
            # Python's legacy sqlite3 transaction mode does not BEGIN for DDL.
            # Explicitly make the entire initialization atomic.
            con.execute("BEGIN IMMEDIATE")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise DatabaseError("数据库来自其他版本，请使用对应版本打开；未修改账单。")
            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise DatabaseError("数据库完整性检查失败，请保留文件并检查备份；未修改账单。")
            con.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount_cents INTEGER NOT NULL
                        CHECK(typeof(amount_cents) = 'integer'
                              AND amount_cents BETWEEN 1 AND 99999999999),
                    datetime TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('饮食','工具','娱乐')),
                    description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 200),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            columns = {row["name"]: row for row in con.execute("PRAGMA table_info(records)")}
            types = {"id": "INTEGER", "amount_cents": "INTEGER", "datetime": "TEXT",
                     "category": "TEXT", "description": "TEXT", "created_at": "TEXT", "updated_at": "TEXT"}
            if set(columns) != set(types) or any(
                columns[name]["type"].upper() != kind
                or columns[name]["pk"] != (1 if name == "id" else 0)
                or (name != "id" and not columns[name]["notnull"])
                for name, kind in types.items()
            ):
                raise DatabaseError("数据库结构不兼容，请保留文件并检查版本；未覆盖账单。")
            # Validate legacy data without changing any amounts, categories or timestamps.
            for row in con.execute("SELECT * FROM records"):
                self._checked_record(row)
            con.execute("CREATE INDEX IF NOT EXISTS idx_records_datetime ON records(datetime DESC, id DESC)")
            con.execute("PRAGMA user_version = 1")

    def add_record(self, amount_cents, when, category, description=""):
        validate_record(amount_cents, when, category, description)
        now = datetime.now().isoformat(timespec="seconds")
        with self._connection() as con:
            cursor = con.execute(
                "INSERT INTO records (amount_cents, datetime, category, description, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (amount_cents, when.isoformat(sep=" ", timespec="minutes"), category, description, now, now),
            )
            return cursor.lastrowid

    def update_record(self, record_id, amount_cents, when, category, description=""):
        validate_record(amount_cents, when, category, description)
        with self._connection() as con:
            cursor = con.execute(
                "UPDATE records SET amount_cents=?, datetime=?, category=?, description=?, updated_at=? WHERE id=?",
                (amount_cents, when.isoformat(sep=" ", timespec="minutes"), category, description,
                 datetime.now().isoformat(timespec="seconds"), record_id),
            )
            if cursor.rowcount != 1:
                raise DatabaseError("这条记录已不存在，请刷新账单。")

    def delete_record(self, record_id):
        with self._connection() as con:
            if con.execute("DELETE FROM records WHERE id=?", (record_id,)).rowcount != 1:
                raise DatabaseError("这条记录已不存在，请刷新账单。")

    def get_records_by_month(self, year, month):
        shift_month(year, month, 0)
        start = f"{year:04d}-{month:02d}-01 00:00"
        if (year, month) == (9999, 12):
            end = "9999-12-31 23:59:59"
        else:
            ny, nm = shift_month(year, month, 1)
            end = f"{ny:04d}-{nm:02d}-01 00:00"
        with self._connection() as con:
            return [self._checked_record(row) for row in con.execute(
                "SELECT * FROM records WHERE datetime >= ? AND datetime < ? ORDER BY datetime DESC, id DESC",
                (start, end),
            )]

    def get_month_statistics(self, year, month):
        return summarize_records(self.get_records_by_month(year, month))
