from app.handler import normalize_email


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  Foo@Bar.COM ") == "foo@bar.com"


def test_normalize_email_plain():
    assert normalize_email("a@b.com") == "a@b.com"
