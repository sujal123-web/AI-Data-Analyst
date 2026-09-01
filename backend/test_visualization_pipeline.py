from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_pipeline import process_question


# ============================================================
# LOAD DATASET
# ============================================================

file_path = "data/test_sales.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)


# ============================================================
# QUESTIONS
# ============================================================

questions = [
    "Show sales by region.",
    "Show sales over date.",
    "Is quantity related to sales?",
    "What percentage of sales comes from each region?",
    "Show the average sale for each region.",
    "How many orders came from each region.",
]


# ============================================================
# TEST
# ============================================================

print("=" * 60)
print("END-TO-END VISUALIZATION PIPELINE TEST")
print("=" * 60)

print(f"\nDataset: {file_path}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Total visualization tests: {len(questions)}")


for index, question in enumerate(questions, start=1):

    print()
    print("=" * 60)
    print(f"TEST {index} / {len(questions)}")
    print("=" * 60)

    print("\nQuestion:")
    print(question)

    try:

        response = process_question(
            df,
            profile,
            question
        )

        print("\nAnalysis Plan:")
        print(response.get("plan"))

        print("\nVisualization:")
        
        visualization = response.get(
            "visualization"
        )

        if not visualization:

            print("No visualization returned.")

        else:

            print(
                "Chart Type:",
                visualization.get("chart_type")
            )

            print(
                "X Column:",
                visualization.get("x_column")
            )

            print(
                "Y Column:",
                visualization.get("y_column")
            )

            print(
                "Aggregation:",
                visualization.get("aggregation")
            )

            figure = visualization.get(
                "figure"
            )

            if figure:

                print(
                    "Figure generated: YES"
                )

                print(
                    "Figure contains:",
                    len(figure.get("data", [])),
                    "trace(s)"
                )

            else:

                print(
                    "Figure generated: NO"
                )

            if visualization.get("error"):

                print(
                    "Visualization Error:",
                    visualization.get("error")
                )

    except Exception as error:

        print("\nTEST ERROR:")
        print(error)


print()
print("=" * 60)
print("END-TO-END VISUALIZATION TEST COMPLETED")
print("=" * 60)