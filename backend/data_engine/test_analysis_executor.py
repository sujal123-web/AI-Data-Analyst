from backend.data_engine.data_loader import load_dataset
from backend.data_engine.analysis_executor import execute_plan


file_path = "data/test_sales.csv"

df = load_dataset(file_path)


plans = [

    {
        "operation": "total",
        "column": "Sales"
    },

    {
        "operation": "average",
        "column": "Quantity"
    },

    {
        "operation": "minimum",
        "column": "Sales"
    },

    {
        "operation": "maximum",
        "column": "Sales"
    },

    {
        "operation": "count"
    },

    {
        "operation": "group_sum",
        "group_column": "Region",
        "value_column": "Sales"
    },

    {
        "operation": "group_average",
        "group_column": "Region",
        "value_column": "Sales"
    }
]


print("================================")
print("ANALYSIS EXECUTOR TEST")
print("================================")


for plan in plans:

    print("\nPlan:")
    print(plan)

    result = execute_plan(
        df,
        plan
    )

    print("Result:")
    print(result)