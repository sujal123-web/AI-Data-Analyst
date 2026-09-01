from backend.data_engine.analysis_engine import (
    total,
    average,
    minimum,
    maximum,
    count,
    unique_count,
    missing_count,
    group_sum,
    group_average,
    group_count,
    group_max,
    group_min,
    top_n,
    bottom_n,
    group_percentage,
    correlation,
    describe_column,
)


def execute_plan(df, plan):
    """
    Execute a structured analysis plan using the analysis engine.

    The executor does not assume any fixed dataset structure.
    Column names and parameters come from the generated plan.
    """

    operation = plan.get("operation")

    try:

        # -----------------------------
        # Basic numerical operations
        # -----------------------------

        if operation == "total":

            return total(
                df,
                plan.get("column")
            )

        elif operation == "average":

            return average(
                df,
                plan.get("column")
            )

        elif operation == "minimum":

            return minimum(
                df,
                plan.get("column")
            )

        elif operation == "maximum":

            return maximum(
                df,
                plan.get("column")
            )

        # -----------------------------
        # Dataset-level operations
        # -----------------------------

        elif operation == "count":

            return count(df)

        elif operation == "unique_count":

            return unique_count(
                df,
                plan.get("column")
            )

        elif operation == "missing_count":

            return missing_count(
                df,
                plan.get("column")
            )

        # -----------------------------
        # Group operations
        # -----------------------------

        elif operation == "group_sum":

            return group_sum(
                df,
                plan.get("group_column"),
                plan.get("value_column")
            )

        elif operation == "group_average":

            return group_average(
                df,
                plan.get("group_column"),
                plan.get("value_column")
            )

        elif operation == "group_count":

            return group_count(
                df,
                plan.get("group_column")
            )

        elif operation == "group_max":

            return group_max(
                df,
                plan.get("group_column"),
                plan.get("value_column")
            )

        elif operation == "group_min":

            return group_min(
                df,
                plan.get("group_column"),
                plan.get("value_column")
            )

        # -----------------------------
        # Percentage analysis
        # -----------------------------

        elif operation == "group_percentage":

            return group_percentage(
                df,
                plan.get("group_column"),
                plan.get("value_column")
            )

        # -----------------------------
        # Statistical operations
        # -----------------------------

        elif operation == "correlation":

            return correlation(
                df,
                plan.get("column1"),
                plan.get("column2")
            )

        elif operation == "describe":

            return describe_column(
                df,
                plan.get("column")
            )

        # -----------------------------
        # Ranking operations
        # -----------------------------

        elif operation == "top_n":

            n = plan.get("n", 5)

            return top_n(
                df,
                plan.get("group_column"),
                plan.get("value_column"),
                int(n)
            )

        elif operation == "bottom_n":

            n = plan.get("n", 5)

            return bottom_n(
                df,
                plan.get("group_column"),
                plan.get("value_column"),
                int(n)
            )

        # -----------------------------
        # Unsupported operation
        # -----------------------------

        elif operation == "unsupported":

            return {
                "error": plan.get(
                    "reason",
                    "This question cannot be answered from the dataset."
                )
            }

        else:

            return {
                "error": f"Unsupported operation: {operation}"
            }

    except (ValueError, KeyError, TypeError) as error:

        return {
            "error": str(error)
        }