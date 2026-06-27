import json
import sqlite3
from http.server import BaseHTTPRequestHandler

DB_PATH = "catalog.db"

SEARCHABLE_TABLES = {"products", "inventory", "price_history"}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_lookup(table, criteria, limit):
    clauses = []
    bindings = []
    for field, value in criteria.items():
        clauses.append("{0} = ?".format(field))
        bindings.append(value)
    predicate = " AND ".join(clauses) if clauses else "1"
    bindings.append(limit)
    statement = "SELECT * FROM {0} WHERE {1} LIMIT ?".format(table, predicate)
    return statement, bindings


class CatalogSearchHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return

        table = payload.get("table", "products")
        if table not in SEARCHABLE_TABLES:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"unknown table")
            return

        criteria = payload.get("where", {})
        limit = min(int(payload.get("limit", 50)), 200)

        statement, bindings = build_lookup(table, criteria, limit)

        conn = connect()
        try:
            rows = conn.execute(statement, bindings).fetchall()
        finally:
            conn.close()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps([dict(r) for r in rows]).encode())
