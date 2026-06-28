from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple


class Connection:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._tables: Dict[str, Dict[Tuple[Any, ...], Dict[str, Any]]] = {}

    @property
    def dsn(self) -> str:
        return self._dsn

    def fetch_one(
        self, query: str, params: Sequence[Any]
    ) -> Optional[Dict[str, Any]]:
        table = self._table_for(query)
        if table is None:
            return None
        key = tuple(params)
        return table.get(key)

    def execute(self, query: str, params: Sequence[Any]) -> None:
        table = self._table_for(query)
        if table is None:
            return
        key = (params[0],)
        table[key] = {"region": params[0], "rate": params[1]}

    def _table_for(self, query: str) -> Optional[Dict[Tuple[Any, ...], Dict[str, Any]]]:
        if "tax_rates" in query:
            return self._tables.setdefault("tax_rates", {})
        return None


_DEFAULT: Optional[Connection] = None


def get_default_connection() -> Connection:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Connection("memory://default")
    return _DEFAULT
