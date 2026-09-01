from data_loader import load_dataset
from data_profiler import profile_dataset


file_path = "../../data/test_sales.csv"

# Load dataset
df = load_dataset(file_path)

print("Dataset loaded successfully!")
print()

# Profile dataset
profile = profile_dataset(df)

print("Dataset Profile")
print("================")

print("Rows:", profile["rows"])
print("Columns:", profile["columns"])

print()

print("Column Details")
print("==============")

for column, details in profile["column_details"].items():

    print(f"\nColumn: {column}")
    print(f"Data Type: {details['data_type']}")
    print(f"Category: {details['category']}")
    print(f"Missing Values: {details['missing_values']}")
    print(f"Unique Values: {details['unique_values']}")