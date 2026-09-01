from backend.data_engine.data_loader import load_dataset
from backend.data_engine.visualization_engine import (
    create_bar_chart,
    create_line_chart,
    create_scatter_chart,
    create_pie_chart,
    create_horizontal_bar_chart,
    create_percentage_chart,
    create_chart,
)


# Load dataset
file_path = "data/test_sales.csv"

df = load_dataset(file_path)


print("================================")
print("VISUALIZATION ENGINE TEST")
print("================================")


# Create a bar chart
bar_chart = create_bar_chart(
    df,
    "Region",
    "Sales",
    aggregation="sum"
)

bar_chart.show()


# Create a line chart
line_chart = create_line_chart(
    df,
    "Date",
    "Sales",
    aggregation="sum"
)

line_chart.show()


# Create a scatter chart
scatter_chart = create_scatter_chart(
    df,
    "Quantity",
    "Sales"
)

scatter_chart.show()