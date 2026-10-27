import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def dumps(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, path, mode):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).parent.chmod(0o700)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        Path(path).chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,type TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS orders(client_id TEXT PRIMARY KEY,request TEXT NOT NULL,raw TEXT NOT NULL,status TEXT NOT NULL,external INTEGER NOT NULL DEFAULT 0,deadline REAL NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS fills(id TEXT PRIMARY KEY,client_id TEXT NOT NULL,at TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS equity(id INTEGER PRIMARY KEY,at TEXT NOT NULL,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,at TEXT NOT NULL,request TEXT NOT NULL,outcome TEXT NOT NULL,context TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS news(id TEXT NOT NULL,revision TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,revision));
          CREATE TABLE IF NOT EXISTS activities(id TEXT PRIMARY KEY,type TEXT NOT NULL,at TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS shadow(id INTEGER PRIMARY KEY,at TEXT NOT NULL,intent TEXT NOT NULL,result TEXT NOT NULL,context TEXT NOT NULL,input_hash TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS research(id INTEGER PRIMARY KEY,at TEXT NOT NULL,packet TEXT NOT NULL,result TEXT NOT NULL,usage TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS timing(id INTEGER PRIMARY KEY,at TEXT NOT NULL,symbol TEXT NOT NULL,strategy TEXT NOT NULL,result TEXT NOT NULL,context TEXT NOT NULL);
        """)
        from .activity_feed import SCHEMA
        self.db.executescript(SCHEMA)
        with self.transaction():
            existing = self.get("mode")
            if existing and existing != mode:
                raise ValueError("Database belongs to another execution mode; use a separate database")
            self.put("mode", mode)

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def get(self, key, default=None):
        with self.lock:
            row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.lock:
            self.db.execute("INSERT INTO state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, dumps(value)))

    def event(self, kind, payload):
        with self.lock:
            cur = self.db.execute("INSERT INTO events(at,type,payload) VALUES(?,?,?)", (utcnow(), kind, dumps(payload)))
            return cur.lastrowid

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def events_after(self, after, limit=250):
        return [{**r, "payload": json.loads(r["payload"])} for r in self.rows("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?", (after, limit))]

    def order(self, client_id):
        rows = self.rows("SELECT * FROM orders WHERE client_id=?", (client_id,))
        return rows[0] if rows else None

    def close(self):
        self.db.close()
