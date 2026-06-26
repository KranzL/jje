"""A tiny request handler with two planted defects, for exercising JJE:

1. SQL injection in build_user_query (security-juror should flag, blocking).
2. normalize_email does not strip surrounding whitespace, so its unit test
   fails (correctness-juror should flag the failing test, blocking).

A correct revise fixes both: parameterize the query and strip before lowercasing.
"""


def build_user_query(user_id):
    return "SELECT * FROM users WHERE id = '" + str(user_id) + "'"


def normalize_email(email):
    return email.lower()
