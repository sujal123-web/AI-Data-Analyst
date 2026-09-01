from backend.data_engine.data_loader import load_dataset
from backend.data_engine.analysis_engine import group_percentage


file_path = "data/test_sales.csv"

df = load_dataset(file_path)


print("================================")
print("PERCENTAGE ANALYSIS TEST")
print("================================")


result = group_percentage(
    df,
    "Region",
    "Sales"
)


print("\nSales Percentage by Region:")

print(result)


print("\nTotal Percentage:")

print(result.sum())