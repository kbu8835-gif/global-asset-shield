import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATABASE_PATH, DATABASE_URL, DEMO_EMAIL, DEMO_PASSWORD, DEMO_USERNAME
from schemas import JournalEntry
from security import hash_password


IS_POSTGRES = DATABASE_URL.startswith(("postgresql://", "postgres://"))


class DictRow(dict):
    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid: Optional[int] = None
        self.rowcount = cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        return DictRow(row) if row else None

    def fetchall(self):
        return [DictRow(row) for row in self._cursor.fetchall()]


class PostgresConnection:
    def __init__(self, raw):
        self._raw = raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type:
            self._raw.rollback()
        self._raw.close()

    def execute(self, query: str, params: tuple = ()):
        cursor = self._raw.cursor()
        translated = _translate_sql(query)
        cursor.execute(translated, params)
        wrapped = PostgresCursor(cursor)
        if _is_insert(translated):
            try:
                returned = cursor.fetchone()
                if returned and "id" in returned:
                    wrapped.lastrowid = int(returned["id"])
            except Exception:
                wrapped.lastrowid = None
        wrapped.rowcount = cursor.rowcount
        return wrapped

    def commit(self) -> None:
        self._raw.commit()


def _translate_sql(query: str) -> str:
    sql = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("?", "%s")
    if _is_insert(sql) and " RETURNING " not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
    return sql


def _is_insert(query: str) -> bool:
    return query.lstrip().upper().startswith("INSERT INTO")


def _sqlite_path_from_url() -> Path:
    if DATABASE_URL.startswith("sqlite:///"):
        raw = DATABASE_URL.replace("sqlite:///", "", 1)
        path = Path(raw)
        return path if path.is_absolute() else Path(__file__).resolve().parent / path
    return DATABASE_PATH


def get_connection():
    if IS_POSTGRES:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as exc:
            raise RuntimeError("PostgreSQL mode requires psycopg2-binary. Run pip install -r requirements.txt") from exc
        return PostgresConnection(psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor))

    db_path = _sqlite_path_from_url()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def is_database_connected() -> bool:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        demo_id = _ensure_demo_user(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                asset TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                user_intent TEXT,
                user_text TEXT,
                buy_reason TEXT,
                risk_score INTEGER NOT NULL,
                emotion_score INTEGER NOT NULL,
                bias_score INTEGER NOT NULL,
                conviction_score INTEGER NOT NULL,
                final_decision TEXT NOT NULL,
                summary TEXT NOT NULL,
                full_report_json TEXT NOT NULL,
                review_status TEXT DEFAULT 'pending'
            )
            """
        )
        _ensure_column(conn, "journal_entries", "user_id", "INTEGER")
        _ensure_column(conn, "journal_entries", "position_size", "TEXT")
        _ensure_column(conn, "journal_entries", "risk_awareness", "TEXT")
        _ensure_column(conn, "journal_entries", "worst_case_plan", "TEXT")
        _ensure_column(conn, "journal_entries", "decision", "TEXT")
        _ensure_column(conn, "journal_entries", "title", "TEXT")
        _ensure_column(conn, "journal_entries", "status", "TEXT DEFAULT 'Open'")
        _ensure_column(conn, "journal_entries", "entry_type", "TEXT DEFAULT 'immune_report'")
        _ensure_column(conn, "journal_entries", "notes", "TEXT")
        _ensure_column(conn, "journal_entries", "mistakes", "TEXT")
        _ensure_column(conn, "journal_entries", "lesson", "TEXT")
        _ensure_column(conn, "journal_entries", "next_action", "TEXT")
        _ensure_column(conn, "journal_entries", "review_date", "TEXT")
        _ensure_column(conn, "journal_entries", "updated_at", "TEXT")
        conn.execute("UPDATE journal_entries SET title = COALESCE(title, asset) WHERE title IS NULL")
        conn.execute("UPDATE journal_entries SET status = COALESCE(status, CASE WHEN review_status = 'reviewed' THEN 'Reviewed' ELSE 'Open' END) WHERE status IS NULL")
        conn.execute("UPDATE journal_entries SET entry_type = COALESCE(entry_type, 'immune_report') WHERE entry_type IS NULL")
        conn.execute("UPDATE journal_entries SET updated_at = COALESCE(updated_at, created_at) WHERE updated_at IS NULL")
        conn.execute("UPDATE journal_entries SET user_id = ? WHERE user_id IS NULL", (demo_id,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kol_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                twitter_handle TEXT,
                telegram_handle TEXT,
                youtube_channel TEXT,
                website TEXT,
                bio TEXT,
                trust_score INTEGER DEFAULT 50,
                total_calls INTEGER DEFAULT 0,
                win_rate_7d REAL DEFAULT 0,
                win_rate_30d REAL DEFAULT 0,
                average_roi_7d REAL DEFAULT 0,
                average_roi_30d REAL DEFAULT 0,
                average_max_gain REAL DEFAULT 0,
                average_max_drawdown REAL DEFAULT 0,
                risk_level TEXT DEFAULT 'Unknown',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_column(conn, "kol_profiles", "user_id", "INTEGER")
        conn.execute("UPDATE kol_profiles SET user_id = ? WHERE user_id IS NULL", (demo_id,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kol_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kol_id INTEGER,
                kol_name TEXT,
                asset TEXT NOT NULL,
                asset_type TEXT DEFAULT 'crypto',
                call_time TEXT,
                call_price REAL,
                current_price REAL,
                source TEXT,
                source_url TEXT,
                call_text TEXT,
                call_type TEXT,
                time_horizon TEXT,
                status TEXT DEFAULT 'open',
                roi_7d REAL,
                roi_30d REAL,
                current_roi REAL,
                max_gain REAL,
                max_drawdown REAL,
                result_label TEXT,
                emotion_tags TEXT,
                bias_tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        _ensure_column(conn, "kol_calls", "user_id", "INTEGER")
        conn.execute("UPDATE kol_calls SET user_id = ? WHERE user_id IS NULL", (demo_id,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investment_journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                asset_symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                action TEXT,
                reason TEXT,
                emotion_tag TEXT,
                risk_score INTEGER DEFAULT 0,
                behavior_risk_score INTEGER DEFAULT 0,
                ai_advice TEXT,
                user_decision TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investment_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                outcome_7d TEXT,
                outcome_30d TEXT,
                outcome_90d TEXT,
                user_feedback TEXT,
                ai_was_right INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investment_dna (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                fomo_score INTEGER DEFAULT 0,
                discipline_score INTEGER DEFAULT 50,
                patience_score INTEGER DEFAULT 50,
                research_score INTEGER DEFAULT 50,
                risk_control_score INTEGER DEFAULT 50,
                kol_dependency_score INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investment_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                health_score INTEGER DEFAULT 50,
                behavior_risk_score INTEGER DEFAULT 0,
                monthly_progress TEXT,
                avoided_risky_trades INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                usage_date TEXT NOT NULL,
                feature TEXT NOT NULL,
                call_count INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        conn.commit()


def _ensure_demo_user(conn: sqlite3.Connection) -> int:
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        """
        INSERT INTO users (email, username, password_hash, created_at, updated_at, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (DEMO_EMAIL, DEMO_USERNAME, hash_password(DEMO_PASSWORD), now, now),
    )
    return int(cursor.lastrowid)


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    if IS_POSTGRES:
        row = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table_name, column_name),
        ).fetchone()
        if row is None:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {_pg_type(column_type)}")
        return
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _pg_type(column_type: str) -> str:
    return column_type.replace("REAL", "DOUBLE PRECISION")


def create_user(email: str, username: Optional[str], password_hash: str) -> Dict[str, Any]:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (email, username, password_hash, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (email.lower(), username, password_hash, now, now),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM users WHERE id = ?", (int(cursor.lastrowid),)).fetchone())


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_demo_user() -> Dict[str, Any]:
    init_db()
    user = get_user_by_email(DEMO_EMAIL)
    if user is None:
        raise RuntimeError("demo user was not created")
    return user


def save_journal_entry(payload: Dict[str, Any], report: Dict[str, Any], user_id: int) -> int:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO journal_entries (
                created_at, updated_at, title, status, entry_type,
                user_id,
                asset, asset_type, user_intent, user_text, buy_reason, position_size, risk_awareness, worst_case_plan,
                risk_score, emotion_score, bias_score, conviction_score,
                decision, final_decision, summary, full_report_json, review_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (now := datetime.now(timezone.utc).isoformat()),
                now,
                payload.get("asset"),
                "Open",
                "immune_report",
                user_id,
                payload.get("asset"),
                payload.get("asset_type"),
                payload.get("user_intent"),
                payload.get("user_text"),
                payload.get("buy_reason"),
                payload.get("position_size"),
                payload.get("risk_awareness"),
                payload.get("worst_case_plan"),
                report["risk_scan"]["risk_score"],
                report["emotion_scan"]["emotion_score"],
                report["bias_detection"]["bias_score"],
                report["conviction_score"]["score"],
                report["final_decision"],
                report["final_decision"],
                report["summary"],
                json.dumps(report, ensure_ascii=False),
                "pending",
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_journal_entries(user_id: int) -> List[JournalEntry]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [JournalEntry(**dict(row)) for row in rows]


def get_journal_entry(journal_id: int, user_id: int) -> Optional[JournalEntry]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ? AND user_id = ?", (journal_id, user_id)).fetchone()
    return JournalEntry(**dict(row)) if row else None


def mark_reviewed(journal_id: int, user_id: int) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "UPDATE journal_entries SET review_status = 'reviewed', status = 'Reviewed', updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now(timezone.utc).isoformat(), journal_id, user_id),
        )
        conn.commit()
