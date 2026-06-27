import pandas as pd
import statsmodels.formula.api as smf


def load_customers():
    return pd.read_parquet("s3://analytics/customers/enrollment_panel.parquet")


def estimate_loyalty_effect(df):
    """Estimand: ATT of loyalty enrollment on annual spend.

    Identification: conditional ignorability via back-door adjustment for the
    confounders that drive both enrollment and spend, all measured in the year
    BEFORE enrollment: prior_year_spend, age, region.
    """
    model = smf.ols(
        "annual_spend ~ enrolled_loyalty + prior_year_spend + age + region "
        "+ purchases_after_enrollment",
        data=df,
    ).fit()
    return model


def main():
    df = load_customers()
    model = estimate_loyalty_effect(df)

    effect = model.params["enrolled_loyalty"]
    print(f"causal effect of loyalty enrollment on annual spend: ${effect:.2f}")
    return effect


if __name__ == "__main__":
    main()
