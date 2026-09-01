from backend.llm.llm_client import generate_response


def main():
    print("================================")
    print("LOCAL LLM CLIENT TEST")
    print("================================")

    prompt = """
You are testing the AI Data Analyst project.

Reply with exactly:
LLM client working successfully.
"""

    print("\nSending test request to Ollama...")

    try:
        response = generate_response(prompt)

        print("\nLLM Response:")
        print(response)

        print("\nTest completed successfully.")

    except Exception as error:
        print("\nLLM Test Failed:")
        print(error)


if __name__ == "__main__":
    main()