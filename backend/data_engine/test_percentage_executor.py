from backend.data_engine.data_loader import load_dataset
from backend.data_engine.analysis_executor import execute_plan


file_path = "data/test_sales.csv"

df = load_dataset(file_path)


print("================================")
print("PERCENTAGE EXECUTOR TEST")
print("================================")


plan = {
    "operation": "group_percentage",
    "group_column": "Region",
    "value_column": "Sales"
}


print("\nPlan:")
print(plan)


result = execute_plan(df, plan)


print("\nResult:")
print(result)