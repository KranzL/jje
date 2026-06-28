from .columns import (
    DEFAULT_SORT,
    FILTERABLE_COLUMNS,
    SORTABLE_COLUMNS,
)

ALLOWED_DIRECTIONS = ("asc", "desc")
MAX_PAGE_SIZE = 200
MAX_PAGE = 10_000


def _coerce_int(value, default, *, minimum, maximum):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))


def build_filter_clause(filters):
    clauses = []
    params = []
    for key, value in filters.items():
        column = FILTERABLE_COLUMNS.get(key)
        if column is None:
            continue
        clauses.append(f"{column} = %s")
        params.append(value)
    where = " AND ".join(clauses) if clauses else "1=1"
    return where, params


def build_search_clause(term):
    if not term:
        return "", []
    pattern = f"%{term.strip()}%"
    return "(r.title ILIKE %s OR u.email ILIKE %s)", [pattern, pattern]


def build_order_clause(sort, direction):
    raw = (sort or DEFAULT_SORT).strip()
    descending = raw.startswith("-")
    field = raw.lstrip("-")

    if descending:
        dir_token = "desc"
    else:
        dir_token = (direction or "asc").lower()
        if dir_token not in ALLOWED_DIRECTIONS:
            dir_token = "asc"

    column = SORTABLE_COLUMNS.get(field, field)
    return f"ORDER BY {column} {dir_token}"


def build_report_query(*, filters, search, sort, direction, page, page_size):
    where, where_params = build_filter_clause(filters or {})
    search_sql, search_params = build_search_clause(search)
    order_sql = build_order_clause(sort, direction)

    limit = _coerce_int(page_size, 50, minimum=1, maximum=MAX_PAGE_SIZE)
    offset = (_coerce_int(page, 1, minimum=1, maximum=MAX_PAGE) - 1) * limit

    conditions = where
    if search_sql:
        conditions = f"({where}) AND {search_sql}"

    sql = (
        "SELECT r.id, r.title, r.status, r.region, u.email AS owner, "
        "r.amount_cents, r.created_at "
        "FROM reports r "
        "JOIN auth_user u ON u.id = r.owner_id "
        f"WHERE {conditions} "
        f"{order_sql} "
        f"LIMIT {limit} OFFSET {offset}"
    )
    return sql, where_params + search_params
