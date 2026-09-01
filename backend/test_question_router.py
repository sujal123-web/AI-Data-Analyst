from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_router import route_question


file_path = "data/test_sales.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)


questions = [
    "What is the total sales?",
    "What's the average quantity?",
    "What is the smallest sales value?",
    "What is the largest sales value?",
    "How many records are there?",
    "How many different regions do we have?",
    "Are there any missing sales values?",
    "Which region performed the best?"
]


print("================================")
print("LOCAL QUESTION ROUTER TEST")
print("================================")


for question in questions:

    result = route_question(
        question,
        profile
    )

    print("\nQuestion:")
    print(question)

    print("Local Route:")
    print(result)