from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_planner import plan_question


file_path = "data/test_sales.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)


questions = [
    "What is the total sales?",
    "What's the average quantity?",
    "How many different regions do we have?",
    "Show me the top 3 regions by sales.",
    "Which region has the highest sales?"
]


print("================================")
print("OLLAMA QUESTION PLANNER TEST")
print("================================")


for number, question in enumerate(questions, start=1):

    print(f"\nTEST {number}")
    print("--------------------------------")

    print("Question:")
    print(question)

    try:

        result = plan_question(
            question,
            profile
        )

        print("Generated Plan:")
        print(result)

    except Exception as error:

        print("Planner Error:")
        print(error)