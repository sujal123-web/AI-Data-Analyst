from data_loader import load_dataset

from analysis_engine import (
    total,
    average,
    minimum,
    maximum,
    count,
    unique_count,
    missing_count,
    group_sum,
    group_average,
    group_count,
    correlation,
    describe_column
)


# Load dataset
file_path = "data/test_sales.csv"

df = load_dataset(file_path)


print("================================")
print("ANALYSIS ENGINE TEST")
print("================================")


print("\nTotal Sales:")
print(total(df, "Sales"))


print("\nAverage Sales:")
print(average(df, "Sales"))


print("\nMinimum Sales:")
print(minimum(df, "Sales"))


print("\nMaximum Sales:")
print(maximum(df, "Sales"))


print("\nNumber of Rows:")
print(count(df))


print("\nUnique Regions:")
print(unique_count(df, "Region"))


print("\nMissing Sales Values:")
print(missing_count(df, "Sales"))


print("\nSales by Region:")
print(group_sum(df, "Region", "Sales"))


print("\nAverage Sales by Region:")
print(group_average(df, "Region", "Sales"))


print("\nOrders by Region:")
print(group_count(df, "Region"))


print("\nCorrelation: Quantity vs Sales:")
print(correlation(df, "Quantity", "Sales"))


print("\nSales Statistics:")
print(describe_column(df, "Sales"))