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
# TEST CASES
# ============================================================

test_cases = [

    {
        "question": "What is the total sales?",
        "expected_operation": "total",
        "expected_column": "Sales",
    },

    {
        "question": "What's the average quantity?",
        "expected_operation": "average",
        "expected_column": "Quantity",
    },

    {
        "question": "What is the smallest sales value?",
        "expected_operation": "minimum",
        "expected_column": "Sales",
    },

    {
        "question": "What is the largest sales value?",
        "expected_operation": "maximum",
        "expected_column": "Sales",
    },

    {
        "question": "How many records are there?",
        "expected_operation": "count",
    },

    {
        "question": "How many different regions do we have?",
        "expected_operation": "unique_count",
        "expected_column": "Region",
    },

    {
        "question": "Are there any missing sales values?",
        "expected_operation": "missing_count",
        "expected_column": "Sales",
    },

    {
        "question": "Show sales by region.",
        "expected_operation": "group_sum",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },

    {
        "question": "What's the average sale for each region?",
        "expected_operation": "group_average",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },

    {
        "question": "How many orders came from each region?",
        "expected_operation": "group_count",
        "expected_group_column": "Region",
    },

    {
        "question": "Which region has the highest sales?",
        "expected_operation": "group_max",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },

    {
        "question": "Which region has the lowest sales?",
        "expected_operation": "group_min",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },

    {
        "question": "Show me the top 3 regions by sales.",
        "expected_operation": "top_n",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
        "expected_n": 3,
    },

    {
        "question": "Show me the bottom 2 regions by sales.",
        "expected_operation": "bottom_n",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
        "expected_n": 2,
    },

    {
        "question": "What percentage of sales comes from each region?",
        "expected_operation": "group_percentage",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },

    {
        "question": "Is quantity related to sales?",
        "expected_operation": "correlation",
        "expected_columns": ["Quantity", "Sales"],
    },

    {
        "question": "Give me statistics for sales.",
        "expected_operation": "describe",
        "expected_column": "Sales",
    },

    {
        "question": "How much money did we make overall?",
        "expected_operation": "total",
        "expected_column": "Sales",
    },

    {
        "question": "Which market performed the best?",
        "expected_operation": "group_sum",
        "expected_group_column": "Region",
        "expected_value_column": "Sales",
    },
]


# ============================================================
# PLAN VALIDATION
# ============================================================

def validate_plan(plan, test_case):
    """
    Validate whether the generated plan matches
    the expected operation and parameters.
    """

    if not plan:
        return False, "No plan generated."

    if plan.get("operation") != test_case["expected_operation"]:
        return (
            False,
            f"Expected operation "
            f"'{test_case['expected_operation']}' "
            f"but got '{plan.get('operation')}'."
        )

    if "expected_column" in test_case:

        if plan.get("column") != test_case["expected_column"]:

            return (
                False,
                f"Expected column "
                f"'{test_case['expected_column']}' "
                f"but got '{plan.get('column')}'."
            )

    if "expected_group_column" in test_case:

        if (
            plan.get("group_column")
            != test_case["expected_group_column"]
        ):

            return (
                False,
                f"Expected group column "
                f"'{test_case['expected_group_column']}' "
                f"but got "
                f"'{plan.get('group_column')}'."
            )

    if "expected_value_column" in test_case:

        if (
            plan.get("value_column")
            != test_case["expected_value_column"]
        ):

            return (
                False,
                f"Expected value column "
                f"'{test_case['expected_value_column']}' "
                f"but got "
                f"'{plan.get('value_column')}'."
            )

    if "expected_n" in test_case:

        if plan.get("n") != test_case["expected_n"]:

            return (
                False,
                f"Expected n="
                f"{test_case['expected_n']} "
                f"but got "
                f"{plan.get('n')}."
            )

    if "expected_columns" in test_case:

        expected_columns = set(
            test_case["expected_columns"]
        )

        generated_columns = {
            plan.get("column1"),
            plan.get("column2"),
        }

        if expected_columns != generated_columns:

            return (
                False,
                f"Expected columns "
                f"{expected_columns} "
                f"but got "
                f"{generated_columns}."
            )

    return True, "Plan matches expected structure."


# ============================================================
# START TEST
# ============================================================

print("=" * 60)
print("AI DATA ANALYST — PLANNER EVALUATION")
print("=" * 60)

print(f"\nDataset: {file_path}")
print(f"Rows: {profile.get('rows')}")
print(f"Columns: {profile.get('columns')}")
print(f"Total tests: {len(test_cases)}")


passed_tests = 0
failed_tests = 0


# ============================================================
# RUN TESTS
# ============================================================

for index, test_case in enumerate(test_cases, start=1):

    question = test_case["question"]

    print()
    print("=" * 60)
    print(f"TEST {index} / {len(test_cases)}")
    print("=" * 60)

    print("\nQuestion:")
    print(question)

    try:

        response = process_question(
            df,
            profile,
            question
        )

        plan = response.get("plan")
        result = response.get("result")
        answer = response.get("answer")

        # ----------------------------------------------------
        # Display generated plan
        # ----------------------------------------------------

        print("\nGenerated Plan:")
        print(plan)

        # ----------------------------------------------------
        # Validate planner
        # ----------------------------------------------------

        plan_valid, validation_message = validate_plan(
            plan,
            test_case
        )

        print("\nPlanner Validation:")
        print(validation_message)

        # ----------------------------------------------------
        # Display analysis result
        # ----------------------------------------------------

        print("\nAnalysis Result:")
        print(result)

        # ----------------------------------------------------
        # Display final answer
        # ----------------------------------------------------

        print("\nFinal Answer:")
        print(answer)

        # ----------------------------------------------------
        # Determine status
        # ----------------------------------------------------

        if plan_valid:

            print("\nSTATUS: PASSED")

            passed_tests += 1

        else:

            print("\nSTATUS: FAILED")

            failed_tests += 1

    except Exception as error:

        print("\nTEST ERROR:")
        print(error)

        print("\nSTATUS: FAILED")

        failed_tests += 1


# ============================================================
# SUMMARY
# ============================================================

total_tests = len(test_cases)

success_rate = (
    passed_tests / total_tests * 100
    if total_tests > 0
    else 0
)


print()
print("=" * 60)
print("PLANNER TEST SUMMARY")
print("=" * 60)

print(f"\nTotal Tests : {total_tests}")
print(f"Passed      : {passed_tests}")
print(f"Failed      : {failed_tests}")
print(f"Success Rate: {success_rate:.1f}%")


# ============================================================
# FINAL STATUS
# ============================================================

print()

if failed_tests == 0:

    print("=" * 60)
    print("ALL PLANNER TESTS PASSED")
    print("=" * 60)

else:

    print("=" * 60)
    print("PLANNER NEEDS IMPROVEMENT")
    print("=" * 60)

print()