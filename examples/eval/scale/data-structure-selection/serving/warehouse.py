from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Protocol


class WarehouseClient(Protocol):
    def query(self, sql: str, params: dict[str, Any]) -> list[dict]:
        ...


class DatabricksClient:
    def __init__(self, http_path: str, token: str) -> None:
        self._http_path = http_path
        self._token = token

    def query(self, sql: str, params: dict[str, Any]) -> list[dict]:
        from databricks import sql as dbsql

        with dbsql.connect(
            server_hostname=os.environ["DATABRICKS_HOST"],
            http_path=self._http_path,
            access_token=self._token,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                columns = [c[0] for c in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]


@lru_cache(maxsize=1)
def get_client() -> WarehouseClient:
    return DatabricksClient(
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        token=os.environ["DATABRICKS_TOKEN"],
    )
