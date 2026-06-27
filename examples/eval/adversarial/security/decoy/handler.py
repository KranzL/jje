import json
import sqlite3
from http.server import BaseHTTPRequestHandler

DB_PATH = "catalog.db"

COLUMN_BINDINGS = {
    "name": "name",
    "sku": "sku",
    "category": "category_id",
    "active": "is_active",
    "vendor": "vendor_id",
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_lookup(criteria, limit):
    clauses = []
    bindings = []
    for field, value in criteria.items():
        column = COLUMN_BINDINGS.get(field)
        if column is None:
            continue
        clauses.append("{0} = ?".format(column))
        bindings.append(value)
    predicate = " AND ".join(clauses) if clauses else "1"
    bindings.append(limit)
    statement = "SELECT * FROM products WHERE {0} LIMIT ?".format(predicate)
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

        criteria = payload.get("where", {})
        limit = min(int(payload.get("limit", 50)), 200)

        statement, bindings = build_lookup(criteria, limit)

        conn = connect()
        try:
            rows = conn.execute(statement, bindings).fetchall()
        finally:
            conn.close()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps([dict(r) for r in rows]).encode())
