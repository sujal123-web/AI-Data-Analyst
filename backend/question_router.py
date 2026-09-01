import re


def normalize_question(question):
    """
    Normalize the user's question for easier matching.
    """

    return question.lower().strip()


def find_column(question, columns):
    """
    Find a dataset column mentioned in the user's question.

    Matching is based on the actual columns present in the dataset.
    """

    question_lower = normalize_question(question)

    # Try longer column names first
    sorted_columns = sorted(
        columns,
        key=lambda column: len(str(column)),
        reverse=True
    )

    for column in sorted_columns:

        column_text = str(column).lower()

        if column_text in question_lower:
            return column

    return None


def route_question(question, profile):
    """
    Determine whether a question can be handled locally.

    Returns a structured plan when a clear operation can be identified.
    Otherwise returns None, meaning the LLM planner may be required.
    """

    question_lower = normalize_question(question)

    column_details = profile.get(
        "column_details",
        {}
    )

    columns = list(column_details.keys())

    column = find_column(
        question,
        columns
    )

    # ---------------------------------
    # Count rows
    # ---------------------------------

    if (
        "how many records" in question_lower
        or "how many rows" in question_lower
        or "number of records" in question_lower
        or "number of rows" in question_lower
    ):

        return {
            "operation": "count"
        }

    # ---------------------------------
    # Total
    # ---------------------------------

    if column and (
        "total" in question_lower
        or "sum" in question_lower
        or "overall" in question_lower
    ):

        if column_details[column]["category"] == "numerical":

            return {
                "operation": "total",
                "column": column
            }

    # ---------------------------------
    # Average
    # ---------------------------------

    if column and (
        "average" in question_lower
        or "mean" in question_lower
        or "typical" in question_lower
    ):

        if column_details[column]["category"] == "numerical":

            return {
                "operation": "average",
                "column": column
            }

    # ---------------------------------
    # Minimum
    # ---------------------------------

    if column and (
        "minimum" in question_lower
        or "minimum value" in question_lower
        or "smallest" in question_lower
        or "lowest" in question_lower
    ):

        if column_details[column]["category"] == "numerical":

            return {
                "operation": "minimum",
                "column": column
            }

    # ---------------------------------
    # Maximum
    # ---------------------------------

    if column and (
        "maximum" in question_lower
        or "maximum value" in question_lower
        or "largest" in question_lower
        or "highest" in question_lower
    ):

        if column_details[column]["category"] == "numerical":

            return {
                "operation": "maximum",
                "column": column
            }

    # ---------------------------------
    # Unique count
    # ---------------------------------

    if column and (
        "unique" in question_lower
        or "different" in question_lower
        or "distinct" in question_lower
    ):

        return {
            "operation": "unique_count",
            "column": column
        }

    # ---------------------------------
    # Missing values
    # ---------------------------------

    if column and (
        "missing" in question_lower
        or "null" in question_lower
        or "empty" in question_lower
    ):

        return {
            "operation": "missing_count",
            "column": column
        }

    # ---------------------------------
    # No clear local operation
    # ---------------------------------

    return None