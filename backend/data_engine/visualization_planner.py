import pandas as pd


SUPPORTED_CHARTS = [
    "bar",
    "line",
    "scatter",
    "pie",
    "none",
]


# ============================================================
# COLUMN HELPERS
# ============================================================

def _find_column(columns, target):
    """
    Find a column using case-insensitive matching.
    """

    if not target:
        return None

    target = str(target).strip().lower()

    for column in columns:

        if str(column).strip().lower() == target:
            return column

    return None


def _get_column_from_plan(plan, key):
    """
    Safely retrieve a column from an analysis plan.
    """

    value = plan.get(key)

    if value is None:
        return None

    return str(value).strip()


def _get_profile_column_details(profile):
    """
    Safely retrieve column metadata from the dataset profile.
    """

    if not isinstance(profile, dict):
        return {}

    details = profile.get("column_details")

    if isinstance(details, dict):
        return details

    return {}


def _get_column_metadata(profile, column):
    """
    Get metadata for a specific column.
    """

    details = _get_profile_column_details(profile)

    if not column:
        return {}

    # Exact match
    if column in details:
        return details[column]

    # Case-insensitive match
    target = str(column).lower().strip()

    for name, metadata in details.items():

        if str(name).lower().strip() == target:
            return metadata

    return {}


def _is_numeric_column(profile, column):
    """
    Determine whether a column is numerical using
    the dataset profile.
    """

    metadata = _get_column_metadata(
        profile,
        column
    )

    if metadata.get("category") == "numerical":
        return True

    dtype = str(
        metadata.get("data_type", "")
    ).lower()

    return any(
        numeric_type in dtype
        for numeric_type in [
            "int",
            "float",
            "decimal"
        ]
    )


def _is_temporal_column(profile, column):
    """
    Determine whether a column is temporal.
    """

    metadata = _get_column_metadata(
        profile,
        column
    )

    return (
        metadata.get("category") == "temporal"
    )


def _is_categorical_column(profile, column):
    """
    Determine whether a column is categorical.
    """

    metadata = _get_column_metadata(
        profile,
        column
    )

    return (
        metadata.get("category") == "categorical"
        or metadata.get("category") == "geographic"
    )


def _get_unique_values(profile, column):
    """
    Get the number of unique values for a column.
    """

    metadata = _get_column_metadata(
        profile,
        column
    )

    value = metadata.get(
        "unique_values",
        0
    )

    try:
        return int(value)

    except Exception:
        return 0


# ============================================================
# TEMPORAL INTELLIGENCE
# ============================================================

def _choose_time_granularity(profile, column):
    """
    Dynamically choose an appropriate time aggregation.

    This prevents charts from displaying thousands
    of individual date values.
    """

    unique_values = _get_unique_values(
        profile,
        column
    )

    if unique_values <= 31:
        return "day"

    if unique_values <= 180:
        return "week"

    if unique_values <= 730:
        return "month"

    return "year"


# ============================================================
# CATEGORY INTELLIGENCE
# ============================================================

def _should_use_bar_chart(profile, column):
    """
    Determine whether a categorical column has a
    reasonable number of categories for a bar chart.
    """

    unique_values = _get_unique_values(
        profile,
        column
    )

    # Very high-cardinality columns should not
    # become giant bar charts.
    return unique_values <= 30


def _should_use_pie_chart(profile, column):
    """
    Pie charts work best with a small number of
    categories.
    """

    unique_values = _get_unique_values(
        profile,
        column
    )

    return 2 <= unique_values <= 8


# ============================================================
# MAIN VISUALIZATION PLANNER
# ============================================================

def plan_visualization(
    question,
    analysis_plan,
    profile=None
):
    """
    Dynamically determine the most appropriate
    visualization for an analysis plan.

    This function DOES NOT create the chart.

    It creates a structured visualization plan
    that the visualization engine will execute.
    """

    if not isinstance(analysis_plan, dict):

        return {
            "chart_type": "none",
            "reason": "Invalid analysis plan."
        }

    operation = analysis_plan.get(
        "operation"
    )

    # ========================================================
    # UNSUPPORTED
    # ========================================================

    if operation in [
        None,
        "unsupported"
    ]:

        return {
            "chart_type": "none",
            "reason": "No visualization is required."
        }

    # ========================================================
    # EXTRACT COLUMNS
    # ========================================================

    group_column = _get_column_from_plan(
        analysis_plan,
        "group_column"
    )

    value_column = _get_column_from_plan(
        analysis_plan,
        "value_column"
    )

    column = _get_column_from_plan(
        analysis_plan,
        "column"
    )

    column1 = _get_column_from_plan(
        analysis_plan,
        "column1"
    )

    column2 = _get_column_from_plan(
        analysis_plan,
        "column2"
    )

    # ========================================================
    # 1. CORRELATION
    # ========================================================

    if operation == "correlation":

        if not column1 or not column2:

            return {
                "chart_type": "none",
                "reason": (
                    "Two numerical columns are required."
                )
            }

        if not _is_numeric_column(
            profile,
            column1
        ):

            return {
                "chart_type": "none",
                "reason": (
                    f"'{column1}' is not numerical."
                )
            }

        if not _is_numeric_column(
            profile,
            column2
        ):

            return {
                "chart_type": "none",
                "reason": (
                    f"'{column2}' is not numerical."
                )
            }

        return {
            "chart_type": "scatter",
            "x_column": column1,
            "y_column": column2,
            "aggregation": None
        }

    # ========================================================
    # 2. GROUP PERCENTAGE
    # ========================================================

    if operation == "group_percentage":

        if not group_column or not value_column:

            return {
                "chart_type": "none",
                "reason": (
                    "Group and value columns are required."
                )
            }

        # Pie only when category count is small.
        if _should_use_pie_chart(
            profile,
            group_column
        ):

            return {
                "chart_type": "pie",
                "x_column": group_column,
                "y_column": value_column,
                "aggregation": "sum"
            }

        # Otherwise bar chart is easier to read.
        return {
            "chart_type": "bar",
            "x_column": group_column,
            "y_column": value_column,
            "aggregation": "sum"
        }

    # ========================================================
    # 3. GROUP COUNT
    # ========================================================

    if operation == "group_count":

        if not group_column:

            return {
                "chart_type": "none",
                "reason": (
                    "A group column is required."
                )
            }

        # High-cardinality grouping should not create
        # an unreadable chart.
        if not _should_use_bar_chart(
            profile,
            group_column
        ):

            return {
                "chart_type": "none",
                "reason": (
                    "The grouping column contains too many "
                    "categories for a readable chart."
                )
            }

        return {
            "chart_type": "bar",
            "x_column": group_column,
            "y_column": group_column,
            "aggregation": "count"
        }

    # ========================================================
    # 4. TOP / BOTTOM
    # ========================================================

    if operation in [
        "top_n",
        "bottom_n"
    ]:

        if not group_column or not value_column:

            return {
                "chart_type": "none",
                "reason": (
                    "Group and value columns are required."
                )
            }

        return {
            "chart_type": "bar",
            "x_column": group_column,
            "y_column": value_column,
            "aggregation": "sum"
        }

    # ========================================================
    # 5. GROUP OPERATIONS
    # ========================================================

    if operation in [
        "group_sum",
        "group_average",
        "group_max",
        "group_min"
    ]:

        if not group_column or not value_column:

            return {
                "chart_type": "none",
                "reason": (
                    "Group and value columns are required."
                )
            }

        aggregation_map = {

            "group_sum": "sum",

            "group_average": "mean",

            "group_max": "max",

            "group_min": "min",
        }

        aggregation = aggregation_map[
            operation
        ]

        # ====================================================
        # TEMPORAL GROUP
        # ====================================================

        if _is_temporal_column(
            profile,
            group_column
        ):

            granularity = _choose_time_granularity(
                profile,
                group_column
            )

            return {
                "chart_type": "line",
                "x_column": group_column,
                "y_column": value_column,
                "aggregation": aggregation,

                # IMPORTANT:
                # The visualization engine will use this
                # to aggregate the date column.
                "time_granularity": granularity
            }

        # ====================================================
        # CATEGORICAL GROUP
        # ====================================================

        if _should_use_bar_chart(
            profile,
            group_column
        ):

            return {
                "chart_type": "bar",
                "x_column": group_column,
                "y_column": value_column,
                "aggregation": aggregation
            }

        # Too many categories
        return {
            "chart_type": "none",
            "reason": (
                "The grouping column contains too many "
                "unique values for a readable visualization."
            )
        }

    # ========================================================
    # 6. SCALAR OPERATIONS
    # ========================================================

    if operation in [

        "total",
        "average",
        "minimum",
        "maximum",
        "describe",
        "unique_count",
        "missing_count",
        "count",
    ]:

        return {
            "chart_type": "none",
            "reason": (
                "A single scalar result does not require "
                "a chart."
            )
        }

    # ========================================================
    # FALLBACK
    # ========================================================

    return {
        "chart_type": "none",
        "reason": (
            f"No visualization rule exists "
            f"for '{operation}'."
        )
    }