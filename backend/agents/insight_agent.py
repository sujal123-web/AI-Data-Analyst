import pandas as pd

from backend.llm.llm_client import generate_response


class InsightAgent:
    """
    Agent responsible for converting verified analysis results
    into clear, business-friendly answers.

    Python/Pandas is always the source of truth.

    The LLM is used only when natural-language explanation
    actually adds value.
    """

    def __init__(self, dataframe, profile):
        self.dataframe = dataframe
        self.profile = profile

    # ============================================================
    # VERIFIED RESULT PREPARATION
    # ============================================================

    def _prepare_verified_result(self, plan, result):
        """
        Convert Python/Pandas results into a clean structure
        that can safely be provided to the LLM.
        """

        operation = plan.get("operation")

        # --------------------------------------------------------
        # Scalar result
        # --------------------------------------------------------

        if not isinstance(
            result,
            (pd.Series, pd.DataFrame, dict)
        ):

            return {
                "type": "scalar_result",
                "operation": operation,
                "value": result
            }

        # --------------------------------------------------------
        # Pandas Series
        # --------------------------------------------------------

        if isinstance(result, pd.Series):

            values = {
                str(key): value
                for key, value in result.to_dict().items()
            }

            verified = {
                "type": "grouped_result",
                "operation": operation,
                "values": values
            }

            # ----------------------------------------------------
            # Highest
            # ----------------------------------------------------

            if (
                len(result) > 0
                and operation in [
                    "group_max",
                    "group_sum",
                    "group_average",
                    "top_n"
                ]
            ):

                highest_index = result.idxmax()
                highest_value = result.max()

                verified["highest"] = {
                    "category": str(highest_index),
                    "value": highest_value
                }

            # ----------------------------------------------------
            # Lowest
            # ----------------------------------------------------

            if (
                len(result) > 0
                and operation in [
                    "group_min",
                    "bottom_n"
                ]
            ):

                lowest_index = result.idxmin()
                lowest_value = result.min()

                verified["lowest"] = {
                    "category": str(lowest_index),
                    "value": lowest_value
                }

            return verified

        # --------------------------------------------------------
        # DataFrame
        # --------------------------------------------------------

        if isinstance(result, pd.DataFrame):

            return {
                "type": "table_result",
                "operation": operation,
                "values": result.to_dict(
                    orient="records"
                )
            }

        # --------------------------------------------------------
        # Dictionary
        # --------------------------------------------------------

        if isinstance(result, dict):

            return {
                "type": "dictionary_result",
                "operation": operation,
                "values": result
            }

        # --------------------------------------------------------
        # Fallback
        # --------------------------------------------------------

        return {
            "type": "result",
            "operation": operation,
            "value": str(result)
        }

    # ============================================================
    # ANSWER GENERATION
    # ============================================================

    def answer(self, question, plan, result):
        """
        Generate a final business-friendly answer.

        Simple deterministic operations are answered directly
        using Python.

        More complex grouped/statistical questions can use
        Ollama for natural-language explanation.
        """

        operation = plan.get("operation")

        # ========================================================
        # SIMPLE SCALAR OPERATIONS
        # ========================================================

        if operation == "total":

            column = plan.get(
                "column",
                "value"
            )

            return (
                f"The total {column.lower()} is "
                f"{result:,.2f}."
            ).replace(".00.", ".")

        # --------------------------------------------------------
        # Average
        # --------------------------------------------------------

        if operation == "average":

            column = plan.get(
                "column",
                "value"
            )

            return (
                f"The average {column.lower()} is "
                f"{result:,.2f}."
            )

        # --------------------------------------------------------
        # Minimum
        # --------------------------------------------------------

        if operation == "minimum":

            column = plan.get(
                "column",
                "value"
            )

            return (
                f"The minimum {column.lower()} is "
                f"{result:,.2f}."
            ).replace(".00.", ".")

        # --------------------------------------------------------
        # Maximum
        # --------------------------------------------------------

        if operation == "maximum":

            column = plan.get(
                "column",
                "value"
            )

            return (
                f"The maximum {column.lower()} is "
                f"{result:,.2f}."
            ).replace(".00.", ".")

        # --------------------------------------------------------
        # Count
        # --------------------------------------------------------

        if operation == "count":

            return (
                f"There are {int(result):,} records "
                f"in the dataset."
            )

        # --------------------------------------------------------
        # Unique Count
        # --------------------------------------------------------

        if operation == "unique_count":

            column = plan.get(
                "column",
                "column"
            )

            return (
                f"There are {int(result):,} unique "
                f"values in {column}."
            )

        # --------------------------------------------------------
        # Missing Count
        # --------------------------------------------------------

        if operation == "missing_count":

            column = plan.get(
                "column",
                "column"
            )

            count = int(result)

            if count == 0:

                return (
                    f"There are no missing values "
                    f"in {column}."
                )

            return (
                f"There are {count:,} missing values "
                f"in {column}."
            )

        # ========================================================
        # GROUP COUNT
        # ========================================================

        if operation == "group_count":

            if isinstance(result, pd.Series):

                parts = []

                for category, value in result.items():

                    parts.append(
                        f"{category}: {int(value):,}"
                    )

                return (
                    "Orders by "
                    f"{plan.get('group_column', 'category')}: "
                    + ", ".join(parts)
                    + "."
                )

        # ========================================================
        # GROUP MAX
        # ========================================================

        if operation == "group_max":

            if isinstance(result, pd.Series) and not result.empty:

                category = result.idxmax()
                value = result.max()

                column = plan.get(
                    "value_column",
                    "value"
                )

                return (
                    f"{category} has the highest "
                    f"{column.lower()} at "
                    f"{value:,.0f}."
                )

        # ========================================================
        # GROUP MIN
        # ========================================================

        if operation == "group_min":

            if isinstance(result, pd.Series) and not result.empty:

                category = result.idxmin()
                value = result.min()

                column = plan.get(
                    "value_column",
                    "value"
                )

                return (
                    f"{category} has the lowest "
                    f"{column.lower()} at "
                    f"{value:,.0f}."
                )

        # ========================================================
        # TOP N
        # ========================================================

        if operation == "top_n":

            if isinstance(result, pd.Series) and not result.empty:

                parts = []

                for position, (category, value) in enumerate(
                    result.items(),
                    start=1
                ):

                    parts.append(
                        f"{position}. {category}: "
                        f"{value:,.0f}"
                    )

                return (
                    "Top "
                    f"{len(result)} "
                    f"{plan.get('group_column', 'categories')} "
                    "by "
                    f"{plan.get('value_column', 'value')}: "
                    + "; ".join(parts)
                    + "."
                )

        # ========================================================
        # BOTTOM N
        # ========================================================

        if operation == "bottom_n":

            if isinstance(result, pd.Series) and not result.empty:

                parts = []

                for position, (category, value) in enumerate(
                    result.items(),
                    start=1
                ):

                    parts.append(
                        f"{position}. {category}: "
                        f"{value:,.0f}"
                    )

                return (
                    "Bottom "
                    f"{len(result)} "
                    f"{plan.get('group_column', 'categories')} "
                    "by "
                    f"{plan.get('value_column', 'value')}: "
                    + "; ".join(parts)
                    + "."
                )

        # ========================================================
        # GROUP SUM
        # ========================================================

        if operation == "group_sum":

            if isinstance(result, pd.Series):

                parts = []

                for category, value in result.items():

                    parts.append(
                        f"{category}: {value:,.0f}"
                    )

                return (
                    f"{plan.get('value_column', 'Value')} "
                    "by "
                    f"{plan.get('group_column', 'category')}: "
                    + ", ".join(parts)
                    + "."
                )

        # ========================================================
        # GROUP AVERAGE
        # ========================================================

        if operation == "group_average":

            if isinstance(result, pd.Series):

                parts = []

                for category, value in result.items():

                    parts.append(
                        f"{category}: {value:,.2f}"
                    )

                return (
                    f"Average "
                    f"{plan.get('value_column', 'value')} "
                    "by "
                    f"{plan.get('group_column', 'category')}: "
                    + ", ".join(parts)
                    + "."
                )

        # ========================================================
        # GROUP PERCENTAGE
        # ========================================================

        if operation == "group_percentage":

            if isinstance(result, pd.Series):

                parts = []

                for category, value in result.items():

                    parts.append(
                        f"{category}: {value:.2f}%"
                    )

                return (
                    f"Percentage of "
                    f"{plan.get('value_column', 'value')} "
                    "by "
                    f"{plan.get('group_column', 'category')}: "
                    + ", ".join(parts)
                    + "."
                )

        # ========================================================
        # CORRELATION
        # ========================================================

        if operation == "correlation":

            column1 = plan.get(
                "column1",
                "Column 1"
            )

            column2 = plan.get(
                "column2",
                "Column 2"
            )

            correlation_value = float(result)

            if correlation_value > 0:

                direction = "positive"

            elif correlation_value < 0:

                direction = "negative"

            else:

                direction = "no"

            return (
                f"The correlation between {column1} "
                f"and {column2} is "
                f"{correlation_value:.2f}, indicating a "
                f"{direction} relationship."
            )

        # ========================================================
        # DESCRIBE
        # ========================================================

        if operation == "describe":

            if isinstance(result, dict):

                column = plan.get(
                    "column",
                    "column"
                )

                count = result.get(
                    "count"
                )

                mean = result.get(
                    "mean"
                )

                minimum = result.get(
                    "minimum"
                )

                maximum = result.get(
                    "maximum"
                )

                median = result.get(
                    "median"
                )

                standard_deviation = result.get(
                    "standard_deviation"
                )

                return (
                    f"Statistics for {column}: "
                    f"count={count}, "
                    f"mean={mean:.2f}, "
                    f"minimum={minimum:.2f}, "
                    f"maximum={maximum:.2f}, "
                    f"median={median:.2f}, "
                    f"standard deviation="
                    f"{standard_deviation:.2f}."
                )

        # ========================================================
        # FALLBACK — OLLAMA
        # ========================================================

        verified_result = self._prepare_verified_result(
            plan,
            result
        )

        prompt = f"""
You are an AI Data Analyst.

USER QUESTION:
{question}

ANALYSIS PLAN:
{plan}

VERIFIED PYTHON RESULT:
{verified_result}

Python/Pandas has already performed the analysis.

Your job is ONLY to explain the verified result.

Rules:

- Use ONLY the verified result.
- Never invent numbers.
- Never change numbers.
- Never perform another calculation.
- Never return JSON.
- Never return a Python dictionary.
- Never return code.
- Return plain natural-language text.
- Keep the answer concise.
- Answer the user's actual question.

Return only the final answer.
"""

        response = generate_response(prompt)

        if not response:

            return (
                "I was unable to generate "
                "a response."
            )

        return response.strip()