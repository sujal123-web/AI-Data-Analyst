from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_pipeline import process_question


# ============================================================
# LOAD EMPLOYEE DATASET
# ============================================================

file_path = "data/test_employees.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)


# ============================================================
# QUESTIONS
# ============================================================

questions = [

    "What is the total salary?",

    "What is the average salary?",

    "What is the highest salary?",

    "What is the lowest salary?",

    "How many employees are there?",

    "How many different departments do we have?",

    "What is the average salary for each department?",

    "How many employees are in each department?",

    "Which department has the highest salary?",

    "Which department has the lowest salary?",

    "Show me the top 2 departments by salary.",

    "Show me the bottom 2 departments by salary.",

    "Is salary related to experience?",

    "Give me statistics for salary.",
]


# ============================================================
# DISPLAY DATASET
# ============================================================

print("=" * 60)
print("ARBITRARY DATASET TEST")
print("=" * 60)

print("\nDataset:")
print(file_path)

print(f"\nRows: {profile.get('rows')}")
print(f"Columns: {profile.get('columns')}")

print("\nDetected columns:")

for column, details in profile.get(
    "column_details",
    {}
).items():

    print(
        f"  {column} -> "
        f"{details.get('category')}"
    )


# ============================================================
# RUN QUESTIONS
# ============================================================

for index, question in enumerate(
    questions,
    start=1
):

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

        print("\nGenerated Plan:")
        print(response.get("plan"))

        print("\nAnalysis Result:")
        print(response.get("result"))

        print("\nFinal Answer:")
        print(response.get("answer"))

    except Exception as error:

        print("\nTEST ERROR:")
        print(error)


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 60)
print("ARBITRARY DATASET TEST COMPLETED")
print("=" * 60)