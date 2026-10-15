"""SQLite ledger; one Render instance with a persistent disk. No session-only quotas."""
from contextlib import contextmanager
import json
import sqlite3
import time
import uuid
from pathlib import Path


class AccessDenied(RuntimeError):
    pass


class UsageStore:
    def __init__(self, path, daily_limit=100, global_daily_limit=500, cooldown_seconds=10):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.daily_limit = daily_limit
        self.global_daily_limit = global_daily_limit
        self.cooldown = cooldown_seconds
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
              CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, trial_used INTEGER NOT NULL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL,
                status TEXT NOT NULL, created REAL NOT NULL, trial INTEGER NOT NULL,
                payload TEXT, selected_answer INTEGER
              );
              CREATE INDEX IF NOT EXISTS requests_user ON requests(user_id, created);
              CREATE TABLE IF NOT EXISTS events (name TEXT NOT NULL, user_id TEXT, created REAL NOT NULL);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        try:
            yield db
        finally:
            db.close()

    def trial_used(self, user_id):
        with self.connection() as db:
            row = db.execute("SELECT trial_used FROM users WHERE id=?", (user_id,)).fetchone()
            return bool(row and row[0])

    def reserve(self, user_id, subscribed, kind="scenario", now=None):
        now = time.time() if now is None else now
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT OR IGNORE INTO users(id) VALUES (?)", (user_id,))
                # A killed worker must not reserve the free trial forever.
                db.execute("UPDATE requests SET status='expired' WHERE status='pending' AND created<?", (now - 600,))
                if db.execute("SELECT 1 FROM requests WHERE user_id=? AND status='pending'", (user_id,)).fetchone():
                    raise AccessDenied("A request is already running. Please wait.")
                if not subscribed:
                    if kind != "scenario" or db.execute("SELECT trial_used FROM users WHERE id=?", (user_id,)).fetchone()[0]:
                        raise AccessDenied("Your free scenario has been used. Subscribe to continue.")
                today = int(now // 86400) * 86400
                if db.execute("SELECT COUNT(*) FROM requests WHERE created>=?", (today,)).fetchone()[0] >= self.global_daily_limit:
                    raise AccessDenied("The tutor has reached today's service limit. Please try tomorrow.")
                count = db.execute("SELECT COUNT(*) FROM requests WHERE user_id=? AND created>=?", (user_id, today)).fetchone()[0]
                if count >= self.daily_limit:
                    raise AccessDenied("You have reached today's practice limit. Please try tomorrow.")
                last = db.execute("SELECT MAX(created) FROM requests WHERE user_id=?", (user_id,)).fetchone()[0]
                if last is not None and now - last < self.cooldown:
                    raise AccessDenied("Please wait a few seconds before the next request.")
                request_id = str(uuid.uuid4())
                db.execute("INSERT INTO requests(id,user_id,kind,status,created,trial) VALUES (?,?,?,'pending',?,?)",
                           (request_id, user_id, kind, now, int(not subscribed)))
                db.execute("COMMIT")
                return request_id
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def complete(self, request_id, user_id, payload=None):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT trial FROM requests WHERE id=? AND user_id=? AND status='pending'", (request_id, user_id)).fetchone()
                if row is None:
                    raise AccessDenied("This request is no longer active. Please refresh.")
                db.execute("UPDATE requests SET status='complete',payload=? WHERE id=?", (json.dumps(payload) if payload else None, request_id))
                if row[0]:
                    db.execute("UPDATE users SET trial_used=1 WHERE id=?", (user_id,))
                db.execute("INSERT INTO events VALUES (?,?,?)", ("request_complete", user_id, time.time()))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def fail(self, request_id, user_id):
        with self.connection() as db:
            db.execute("UPDATE requests SET status='failed' WHERE id=? AND user_id=? AND status='pending'", (request_id, user_id))

    def latest_scenario(self, user_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM requests WHERE user_id=? AND kind='scenario' AND status='complete' AND payload IS NOT NULL ORDER BY created DESC LIMIT 1", (user_id,)).fetchone()
            return dict(row) if row else None

    def answer(self, request_id, user_id, selected):
        with self.connection() as db:
            db.execute("UPDATE requests SET selected_answer=? WHERE id=? AND user_id=? AND kind='scenario' AND selected_answer IS NULL", (selected, request_id, user_id))

    def event(self, name, user_id=None):
        if name not in {"visit", "login", "paywall_view", "checkout_click", "billing_refresh", "answer_submitted"}:
            raise ValueError("Unknown event")
        with self.connection() as db:
            db.execute("INSERT INTO events VALUES (?,?,?)", (name, user_id, time.time()))

    def metrics(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT date(created,'unixepoch') AS day,name,COUNT(*) AS count FROM events GROUP BY day,name ORDER BY day DESC,name")]
