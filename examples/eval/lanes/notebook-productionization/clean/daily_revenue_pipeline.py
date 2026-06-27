import pandas as pd

run_date = "2025-01-01"
orders_path = "s3://warehouse/orders/"
output_path = "s3://marts/daily_revenue/"


def load_orders(path: str, run_date: str) -> pd.DataFrame:
    orders = pd.read_parquet(f"{path}date={run_date}/")
    amount = pd.to_numeric(orders["amount"], errors="raise")
    assert amount.notna().all(), "amount column contains nulls after parse"
    orders["amount"] = amount
    return orders


def summarize_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    revenue = (
        orders.groupby("region", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "gross_revenue"})
    )
    return revenue


def main() -> None:
    orders = load_orders(orders_path, run_date)
    revenue = summarize_revenue(orders)
    revenue.to_parquet(f"{output_path}date={run_date}/")


if __name__ == "__main__":
    main()
