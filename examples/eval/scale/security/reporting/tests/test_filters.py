from reporting.filters import (
    build_filter_clause,
    build_order_clause,
    build_report_query,
    build_search_clause,
)


def test_filter_clause_uses_placeholders():
    where, params = build_filter_clause({"status": "approved", "region": "emea"})
    assert where == "r.status = %s AND r.region = %s"
    assert params == ["approved", "emea"]


def test_filter_clause_drops_unknown_keys():
    where, params = build_filter_clause({"bogus": "1", "status": "draft"})
    assert where == "r.status = %s"
    assert params == ["draft"]


def test_search_clause_is_parameterized():
    sql, params = build_search_clause("acme")
    assert sql == "(r.title ILIKE %s OR u.email ILIKE %s)"
    assert params == ["%acme%", "%acme%"]


def test_order_clause_known_column():
    assert build_order_clause("amount", "desc") == "ORDER BY r.amount_cents desc"


def test_order_clause_default():
    assert build_order_clause(None, None) == "ORDER BY r.created_at asc"


def test_order_clause_prefix_descending():
    assert build_order_clause("-created_at", "asc") == "ORDER BY r.created_at desc"


def test_report_query_paginates():
    sql, params = build_report_query(
        filters={"status": "approved"},
        search=None,
        sort="created_at",
        direction="desc",
        page=3,
        page_size=25,
    )
    assert "LIMIT 25 OFFSET 50" in sql
    assert params == ["approved"]
