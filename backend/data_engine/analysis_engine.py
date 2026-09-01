import re

import pandas as pd


# =========================================================
# COLUMN UTILITIES
# =========================================================

def resolve_column(df, column):
    """
    Resolve a column name safely.

    Matching order:
        1. Exact match
        2. Case-insensitive match
        3. Trimmed case-insensitive match

    Returns the actual dataframe column name.
    """

    if column is None:
        raise ValueError("No column was specified.")

    requested = str(column).strip()

    if requested in df.columns:
        return requested

    requested_lower = requested.lower()

    for actual_column in df.columns:

        if str(actual_column).strip().lower() == requested_lower:
            return actual_column

    raise ValueError(
        f"Column '{column}' does not exist in the dataset."
    )


def validate_column(df, column):
    """
    Check whether a column exists.

    Returns the actual dataframe column name.
    """

    return resolve_column(df, column)


# =========================================================
# NUMERIC UTILITIES
# =========================================================

def _clean_numeric_value(value):
    """
    Convert common human-readable numeric formats
    into values that pandas can interpret as numbers.

    Examples:

        "3,500"       -> 3500
        "$3,500"      -> 3500
        "₹3,500"      -> 3500
        "(3,500)"     -> -3500
        "45%"         -> 45

    Values that cannot safely be interpreted as numbers
    become None.
    """

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()

    if not text:
        return None

    negative = False

    # Accounting format:
    # (3500) -> -3500
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    # Remove common currency symbols and formatting.
    text = re.sub(
        r"[$₹€£¥]",
        "",
        text
    )

    # Remove commas.
    text = text.replace(",", "")

    # Remove percentage sign.
    text = text.replace("%", "")

    # Remove surrounding whitespace.
    text = text.strip()

    try:

        number = float(text)

        if negative:
            number = -number

        return number

    except (ValueError, TypeError):
        return None


def _numeric_series(df, column):
    """
    Return a safely converted numerical Series.

    This allows the system to work with:
        - integer columns
        - float columns
        - numeric strings
        - comma-formatted numbers
        - common currency-formatted numbers
    """

    actual_column = resolve_column(
        df,
        column
    )

    original = df[actual_column]

    # Already numeric
    if pd.api.types.is_numeric_dtype(original):

        return pd.to_numeric(
            original,
            errors="coerce"
        )

    # Try normal conversion first.
    converted = pd.to_numeric(
        original,
        errors="coerce"
    )

    valid_ratio = converted.notna().mean()

    # If most values converted successfully,
    # use the result.
    if valid_ratio >= 0.8:

        return converted

    # Otherwise clean common formatting.
    cleaned = original.apply(
        _clean_numeric_value
    )

    converted = pd.to_numeric(
        cleaned,
        errors="coerce"
    )

    return converted


def validate_numeric_column(df, column):
    """
    Check whether a column contains usable numerical data.

    Returns the actual dataframe column name.
    """

    actual_column = resolve_column(
        df,
        column
    )

    numeric = _numeric_series(
        df,
        actual_column
    )

    valid_values = numeric.notna().sum()

    if valid_values == 0:

        raise ValueError(
            f"Column '{actual_column}' does not contain numerical data."
        )

    return actual_column


# =========================================================
# BASIC NUMERICAL OPERATIONS
# =========================================================

def total(df, column):
    """
    Calculate the total of a numerical column.
    """

    actual_column = validate_numeric_column(
        df,
        column
    )

    values = _numeric_series(
        df,
        actual_column
    )

    return values.sum()


def average(df, column):
    """
    Calculate the average of a numerical column.
    """

    actual_column = validate_numeric_column(
        df,
        column
    )

    values = _numeric_series(
        df,
        actual_column
    )

    return values.mean()


def minimum(df, column):
    """
    Find the minimum value of a numerical column.
    """

    actual_column = validate_numeric_column(
        df,
        column
    )

    values = _numeric_series(
        df,
        actual_column
    )

    return values.min()


def maximum(df, column):
    """
    Find the maximum value of a numerical column.
    """

    actual_column = validate_numeric_column(
        df,
        column
    )

    values = _numeric_series(
        df,
        actual_column
    )

    return values.max()


# =========================================================
# DATASET-LEVEL OPERATIONS
# =========================================================

def count(df):
    """
    Count the number of rows.
    """

    return len(df)


def unique_count(df, column):
    """
    Count unique values in a column.
    """

    actual_column = validate_column(
        df,
        column
    )

    return int(
        df[actual_column].nunique(
            dropna=True
        )
    )


def missing_count(df, column):
    """
    Count missing values in a column.
    """

    actual_column = validate_column(
        df,
        column
    )

    return int(
        df[actual_column].isna().sum()
    )


# =========================================================
# GROUP OPERATIONS
# =========================================================

def group_sum(df, group_column, value_column):
    """
    Calculate the sum of a numerical column
    grouped by another column.
    """

    actual_group = validate_column(
        df,
        group_column
    )

    actual_value = validate_numeric_column(
        df,
        value_column
    )

    values = _numeric_series(
        df,
        actual_value
    )

    working_df = pd.DataFrame(
        {
            "_group": df[actual_group],
            "_value": values,
        }
    )

    result = (
        working_df
        .dropna(subset=["_value"])
        .groupby("_group")["_value"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    return result


def group_average(df, group_column, value_column):
    """
    Calculate the average of a numerical column
    grouped by another column.
    """

    actual_group = validate_column(
        df,
        group_column
    )

    actual_value = validate_numeric_column(
        df,
        value_column
    )

    values = _numeric_series(
        df,
        actual_value
    )

    working_df = pd.DataFrame(
        {
            "_group": df[actual_group],
            "_value": values,
        }
    )

    result = (
        working_df
        .dropna(subset=["_value"])
        .groupby("_group")["_value"]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    return result


def group_count(df, group_column):
    """
    Count rows for each category.
    """

    actual_group = validate_column(
        df,
        group_column
    )

    result = (
        df
        .groupby(
            actual_group,
            dropna=False
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    return result


def group_max(df, group_column, value_column):
    """
    Find the highest value for each group.
    """

    actual_group = validate_column(
        df,
        group_column
    )

    actual_value = validate_numeric_column(
        df,
        value_column
    )

    values = _numeric_series(
        df,
        actual_value
    )

    working_df = pd.DataFrame(
        {
            "_group": df[actual_group],
            "_value": values,
        }
    )

    result = (
        working_df
        .dropna(subset=["_value"])
        .groupby("_group")["_value"]
        .max()
        .sort_values(
            ascending=False
        )
    )

    return result


def group_min(df, group_column, value_column):
    """
    Find the lowest value for each group.
    """

    actual_group = validate_column(
        df,
        group_column
    )

    actual_value = validate_numeric_column(
        df,
        value_column
    )

    values = _numeric_series(
        df,
        actual_value
    )

    working_df = pd.DataFrame(
        {
            "_group": df[actual_group],
            "_value": values,
        }
    )

    result = (
        working_df
        .dropna(subset=["_value"])
        .groupby("_group")["_value"]
        .min()
        .sort_values(
            ascending=True
        )
    )

    return result


# =========================================================
# RANKING OPERATIONS
# =========================================================

def top_n(df, group_column, value_column, n):
    """
    Return the top N groups based on
    the sum of a numerical column.
    """

    if n is None:
        n = 5

    try:
        n = int(n)
    except (ValueError, TypeError):

        raise ValueError(
            "N must be a valid integer."
        )

    if n <= 0:

        raise ValueError(
            "N must be greater than zero."
        )

    result = group_sum(
        df,
        group_column,
        value_column
    )

    return result.head(n)


def bottom_n(df, group_column, value_column, n):
    """
    Return the bottom N groups based on
    the sum of a numerical column.
    """

    if n is None:
        n = 5

    try:
        n = int(n)
    except (ValueError, TypeError):

        raise ValueError(
            "N must be a valid integer."
        )

    if n <= 0:

        raise ValueError(
            "N must be greater than zero."
        )

    result = group_sum(
        df,
        group_column,
        value_column
    )

    return result.sort_values(
        ascending=True
    ).head(n)


# =========================================================
# PERCENTAGE ANALYSIS
# =========================================================

def group_percentage(df, group_column, value_column):
    """
    Calculate each group's percentage contribution
    to the total of a numerical column.
    """

    grouped = group_sum(
        df,
        group_column,
        value_column
    )

    total_value = grouped.sum()

    if pd.isna(total_value):

        return grouped * 0

    if total_value == 0:

        return grouped * 0

    result = (
        (grouped / total_value) * 100
    ).sort_values(
        ascending=False
    )

    return result


# =========================================================
# CORRELATION
# =========================================================

def correlation(df, column1, column2):
    """
    Calculate correlation between two numerical columns.
    """

    actual_column1 = validate_numeric_column(
        df,
        column1
    )

    actual_column2 = validate_numeric_column(
        df,
        column2
    )

    values1 = _numeric_series(
        df,
        actual_column1
    )

    values2 = _numeric_series(
        df,
        actual_column2
    )

    working_df = pd.DataFrame(
        {
            "_x": values1,
            "_y": values2,
        }
    ).dropna()

    if len(working_df) < 2:

        raise ValueError(
            "At least two valid observations are required "
            "to calculate correlation."
        )

    result = working_df["_x"].corr(
        working_df["_y"]
    )

    if pd.isna(result):

        raise ValueError(
            "Correlation could not be calculated. "
            "The columns may have no variation."
        )

    return result


# =========================================================
# DESCRIPTIVE STATISTICS
# =========================================================

def describe_column(df, column):
    """
    Return basic statistical information
    about a numerical column.
    """

    actual_column = validate_numeric_column(
        df,
        column
    )

    values = (
        _numeric_series(
            df,
            actual_column
        )
        .dropna()
    )

    if len(values) == 0:

        raise ValueError(
            f"Column '{actual_column}' has no valid numerical values."
        )

    return {
        "count": int(
            values.count()
        ),

        "mean": float(
            values.mean()
        ),

        "minimum": float(
            values.min()
        ),

        "maximum": float(
            values.max()
        ),

        "median": float(
            values.median()
        ),

        "standard_deviation": float(
            values.std()
        ),
    }