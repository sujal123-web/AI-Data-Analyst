from backend.data_engine.data_loader import load_dataset

from backend.data_engine.analysis_engine import (
    group_max,
    group_min,
    top_n,
    bottom_n
)


file_path = "data/test_sales.csv"

df = load_dataset(file_path)


print("================================")
print("RANKING ANALYSIS TEST")
print("================================")


print("\nMaximum Sales by Region:")

print(
    group_max(
        df,
        "Region",
        "Sales"
    )
)


print("\nMinimum Sales by Region:")

print(
    group_min(
        df,
        "Region",
        "Sales"
    )
)


print("\nTop 3 Regions by Sales:")

print(
    top_n(
        df,
        "Region",
        "Sales",
        3
    )
)


print("\nBottom 2 Regions by Sales:")

print(
    bottom_n(
        df,
        "Region",
        "Sales",
        2
    )
)