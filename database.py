"""All SQL lives here; money remains integer cents and connections always close.

Schema history
  v1  category TEXT NOT NULL IN ('饮食','工具','娱乐')
  v2  category TEXT NULL     IN ('生活','工具','娱乐');  '饮食' became '生活'.
      NULL means "not judged yet". Migration rebuilds the table inside one
      transaction after writing a file backup next to the ledger.
"""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from domain import CATEGORIES, validate_record, shift_month, summarize_records, parse_stored_datetime

SCHEMA_VERSION = 2
LEGACY_CATEGORY_MAP = {"饮食": "生活"}
BACKUP_SUFFIX = ".before-v2.bak"

CREATE_RECORDS = """
    CREATE TABLE {name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount_cents INTEGER NOT NULL
            CHECK(typeof(amount_cents) = 'integer'
                  AND amount_cents BETWEEN 1 AND 99999999999),
        datetime TEXT NOT NULL,
        category TEXT CHECK(category IS NULL OR category IN ('生活','工具','娱乐')),
        description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 200),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""
COLUMN_TYPES = {"id": "INTEGER", "amount_cents": "INTEGER", "datetime": "TEXT",
                "category": "TEXT", "description": "TEXT", "created_at": "TEXT", "updated_at": "TEXT"}


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
    def _checked_record(row, *, legacy=False):
        record = dict(row)
        try:
            when = parse_stored_datetime(record["datetime"])
            category = record["category"]
            if legacy:
                category = LEGACY_CATEGORY_MAP.get(category, category)
            validate_record(record["amount_cents"], when, category, record["description"])
            if type(record["id"]) is not int or record["id"] <= 0:
                raise ValueError("Invalid record ID")
        except (ValueError, TypeError, KeyError) as exc:
            raise DatabaseError("数据库中有无效账单或时间格式，请保留文件并从备份检查；未修改原记录。") from exc
        return record

    @staticmethod
    def _verify_shape(con):
        columns = {row["name"]: row for row in con.execute("PRAGMA table_info(records)")}
        if set(columns) != set(COLUMN_TYPES) or any(
            columns[name]["type"].upper() != kind
            or columns[name]["pk"] != (1 if name == "id" else 0)
            or (name not in ("id", "category") and not columns[name]["notnull"])
            for name, kind in COLUMN_TYPES.items()
        ):
            raise DatabaseError("数据库结构不兼容，请保留文件并检查版本；未覆盖账单。")
        return columns

    def _backup_before_migration(self, con):
        """Plain file copy of the untouched v1 ledger, made through SQLite so it is consistent."""
        target = self.path.with_name(self.path.name + BACKUP_SUFFIX)
        if target.exists():
            return
        try:
            backup = sqlite3.connect(target)
            try:
                con.backup(backup)
            finally:
                backup.close()
        except sqlite3.Error as exc:
            raise DatabaseError("无法在升级前备份账单文件，已停止升级；原有账单未被修改。") from exc

    def initialize_database(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError("无法创建数据目录，请检查该目录的写入权限。") from exc
        with self._connection(create=True) as con:
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, SCHEMA_VERSION):
                raise DatabaseError("数据库来自其他版本，请使用对应版本打开；未修改账单。")
            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise DatabaseError("数据库完整性检查失败，请保留文件并检查备份；未修改账单。")
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='records'").fetchone()
            legacy = bool(exists) and version < SCHEMA_VERSION
            if legacy:
                # Validate before touching anything; the backup precedes the rebuild.
                self._verify_legacy_shape(con)
                for row in con.execute("SELECT * FROM records"):
                    self._checked_record(row, legacy=True)
                self._backup_before_migration(con)
            # Python's legacy sqlite3 transaction mode does not BEGIN for DDL.
            # Explicitly make the entire initialization atomic.
            con.execute("BEGIN IMMEDIATE")
            if legacy:
                self._migrate_to_v2(con)
            elif not exists:
                con.execute(CREATE_RECORDS.format(name="records"))
            self._verify_shape(con)
            if not legacy:
                # Validate existing data without changing any amounts, categories or timestamps.
                for row in con.execute("SELECT * FROM records"):
                    self._checked_record(row)
            con.execute("CREATE INDEX IF NOT EXISTS idx_records_datetime ON records(datetime DESC, id DESC)")
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _verify_legacy_shape(con):
        columns = {row["name"]: row for row in con.execute("PRAGMA table_info(records)")}
        if set(columns) != set(COLUMN_TYPES) or any(
            columns[name]["type"].upper() != kind or columns[name]["pk"] != (1 if name == "id" else 0)
            for name, kind in COLUMN_TYPES.items()
        ):
            raise DatabaseError("数据库结构不兼容，请保留文件并检查版本；未覆盖账单。")

    @staticmethod
    def _migrate_to_v2(con):
        con.execute(CREATE_RECORDS.format(name="records_v2"))
        con.execute("""
            INSERT INTO records_v2 (id, amount_cents, datetime, category, description, created_at, updated_at)
            SELECT id, amount_cents, datetime,
                   CASE category WHEN '饮食' THEN '生活' ELSE category END,
                   description, created_at, updated_at
            FROM records ORDER BY id
        """)
        before = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        after = con.execute("SELECT COUNT(*) FROM records_v2").fetchone()[0]
        if before != after:
            raise DatabaseError("升级时记录数量不一致，已回滚；原有账单未被修改。")
        sequence = con.execute("SELECT seq FROM sqlite_sequence WHERE name='records'").fetchone()
        con.execute("DROP TABLE records")
        con.execute("ALTER TABLE records_v2 RENAME TO records")
        # Keep the id counter so deleted ids are never reused after the rebuild.
        con.execute("DELETE FROM sqlite_sequence WHERE name IN ('records', 'records_v2')")
        if sequence is not None:
            con.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('records', ?)", (sequence[0],))

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="seconds")

    def add_record(self, amount_cents, when, category=None, description=""):
        validate_record(amount_cents, when, category, description)
        now = self._now()
        with self._connection() as con:
            cursor = con.execute(
                "INSERT INTO records (amount_cents, datetime, category, description, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (amount_cents, when.isoformat(sep=" ", timespec="minutes"), category, description, now, now),
            )
            return cursor.lastrowid

    def restore_record(self, record):
        """Re-insert a deleted record with its original id and timestamps (undo delete)."""
        when = parse_stored_datetime(record["datetime"])
        validate_record(record["amount_cents"], when, record["category"], record["description"])
        with self._connection() as con:
            con.execute(
                "INSERT INTO records (id, amount_cents, datetime, category, description, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (record["id"], record["amount_cents"], record["datetime"], record["category"],
                 record["description"], record["created_at"], record["updated_at"]),
            )

    def update_record(self, record_id, amount_cents, when, category, description=""):
        validate_record(amount_cents, when, category, description)
        with self._connection() as con:
            cursor = con.execute(
                "UPDATE records SET amount_cents=?, datetime=?, category=?, description=?, updated_at=? WHERE id=?",
                (amount_cents, when.isoformat(sep=" ", timespec="minutes"), category, description,
                 self._now(), record_id),
            )
            if cursor.rowcount != 1:
                raise DatabaseError("这条记录已不存在，请刷新账单。")

    def delete_record(self, record_id):
        with self._connection() as con:
            if con.execute("DELETE FROM records WHERE id=?", (record_id,)).rowcount != 1:
                raise DatabaseError("这条记录已不存在，请刷新账单。")

    def get_record(self, record_id):
        with self._connection() as con:
            row = con.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise DatabaseError("这条记录已不存在，请刷新账单。")
        return self._checked_record(row)

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

    def search_records(self, text):
        """Case-insensitive (ASCII) substring match on the description, across all history."""
        needle = text.strip()
        if not needle:
            return []
        pattern = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self._connection() as con:
            return [self._checked_record(row) for row in con.execute(
                "SELECT * FROM records WHERE description LIKE ? ESCAPE '\\' ORDER BY datetime DESC, id DESC",
                (pattern,),
            )]

    def latest_category_for(self, description):
        """The category most recently given to an identical description, or None."""
        key = description.strip()
        if not key:
            return None
        with self._connection() as con:
            row = con.execute(
                "SELECT category FROM records WHERE category IS NOT NULL "
                "AND lower(trim(description)) = lower(?) ORDER BY updated_at DESC, id DESC LIMIT 1",
                (key,),
            ).fetchone()
        category = row["category"] if row else None
        return category if category in CATEGORIES else None
