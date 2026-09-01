from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.agents.insight_agent import InsightAgent


file_path = "data/test_sales.csv"

df = load_dataset(file_path)

profile = profile_dataset(df)

agent = InsightAgent(
    dataframe=df,
    profile=profile
)


questions = [
    "What is the total sales?",
    "What is the average quantity?",
    "Which region has the highest sales?",
]


print("================================")
print("INSIGHT AGENT TEST")
print("================================")


for question in questions:

    print("\nUser Question:")
    print(question)

    answer = agent.answer(question)

    print("\nAI Answer:")
    print(answer)