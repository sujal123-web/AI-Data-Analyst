from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_planner import plan_question
from backend.data_engine.visualization_planner import plan_visualization


# -----------------------------------------
# Load dataset
# -----------------------------------------

file_path = "data/test_sales.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)


# -----------------------------------------
# Questions to test
# -----------------------------------------

questions = [
    "Show sales by region.",
    "Show me the top 3 regions by sales.",
    "What's the average sale for each region?",
    "Show sales over date.",
    "Is quantity related to sales?",
    "What percentage of sales comes from each region?",
    "Show the number of orders by region.",
    "Show the highest sales by region.",
]


# -----------------------------------------
# Run tests
# -----------------------------------------

print("=" * 60)
print("VISUALIZATION PLANNER TEST")
print("=" * 60)

print(f"\nDataset: {file_path}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Total questions: {len(questions)}")


for index, question in enumerate(questions, start=1):

    print()
    print("=" * 60)
    print(f"TEST {index} / {len(questions)}")
    print("=" * 60)

    print("\nQuestion:")
    print(question)

    try:

        # -----------------------------------------
        # Step 1: Generate analysis plan
        # -----------------------------------------

        analysis_plan = plan_question(
            question,
            profile
        )

        print("\nAnalysis Plan:")
        print(analysis_plan)

        # -----------------------------------------
        # Step 2: Generate visualization plan
        # -----------------------------------------

        visualization_plan = plan_visualization(
            question,
            analysis_plan,
            profile
        )

        print("\nVisualization Plan:")
        print(visualization_plan)

    except Exception as error:

        print("\nTEST ERROR:")
        print(error)


print()
print("=" * 60)
print("VISUALIZATION PLANNER TEST COMPLETED")
print("=" * 60)