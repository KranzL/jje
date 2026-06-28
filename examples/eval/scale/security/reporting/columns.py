from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    key: str
    db_column: str
    sortable: bool = True
    filterable: bool = True


REPORT_COLUMNS = (
    Column("id", "r.id", filterable=False),
    Column("title", "r.title"),
    Column("status", "r.status"),
    Column("region", "r.region"),
    Column("owner", "u.email"),
    Column("amount", "r.amount_cents"),
    Column("created_at", "r.created_at"),
)

FILTERABLE_COLUMNS = {
    col.key: col.db_column for col in REPORT_COLUMNS if col.filterable
}

SORTABLE_COLUMNS = {
    col.key: col.db_column for col in REPORT_COLUMNS if col.sortable
}

DEFAULT_SORT = "created_at"
