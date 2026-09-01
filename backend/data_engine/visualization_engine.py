import re

import pandas as pd
import plotly.express as px


# ============================================================
# SUPPORTED CHARTS
# ============================================================

SUPPORTED_CHARTS = [
    "bar",
    "line",
    "scatter",
    "pie",
    "horizontal_bar",
    "percentage",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _validate_columns(df, columns):
    """
    Validate that all requested columns exist in the dataframe.
    """
    missing_columns = [
        column
        for column in columns
        if column is not None and column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Column(s) not found in dataset: "
            f"{', '.join(map(str, missing_columns))}"
        )


def _normalize_column_name(column):
    """
    Normalize a column name for semantic checks.
    """
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(column).strip().lower(),
    ).strip("_")


def _safe_numeric(series):
    """
    Convert a series to numeric without raising.
    """
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(r"[$€£₹]", "", regex=True)
        .str.strip()
    )

    return pd.to_numeric(cleaned, errors="coerce")


# ============================================================
# TEMPORAL COLUMN CLASSIFICATION
# ============================================================

def _classify_temporal_column(series, column_name):
    """
    Determine what kind of temporal information a column represents.

    IMPORTANT:
    Numeric values must NOT automatically be converted to datetime.

    Examples:
        MONTH_ID = 1..12     -> month_number
        DAY_ID   = 1..31     -> day_number
        YEAR     = 2003..2026 -> year_number
        ORDERDATE = 1/10/2003 -> datetime
        TIMESTAMP -> datetime
    """
    normalized = _normalize_column_name(column_name)

    # --------------------------------------------------------
    # Explicit semantic signals from the column name
    # --------------------------------------------------------

    month_tokens = {
        "month",
        "month_id",
        "month_no",
        "month_num",
        "month_number",
        "mnth",
    }

    year_tokens = {
        "year",
        "year_id",
        "year_no",
        "year_num",
        "year_number",
    }

    day_tokens = {
        "day",
        "day_id",
        "day_no",
        "day_num",
        "day_number",
    }

    # Exact normalized names first.
    if normalized in month_tokens:
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1, 12).all():
            return "month_number"

    if normalized in year_tokens:
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1900, 2200).all():
            return "year_number"

    if normalized in day_tokens:
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1, 31).all():
            return "day_number"

    # --------------------------------------------------------
    # Semantic substring signals
    # --------------------------------------------------------

    if (
        "month_id" in normalized
        or normalized.endswith("_month")
        or normalized.startswith("month_")
    ):
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1, 12).all():
            return "month_number"

    if (
        normalized == "year"
        or normalized.endswith("_year")
        or normalized.startswith("year_")
    ):
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1900, 2200).all():
            return "year_number"

    if (
        "day_id" in normalized
        or normalized.endswith("_day")
        or normalized.startswith("day_")
    ):
        numeric = _safe_numeric(series).dropna()

        if not numeric.empty and numeric.between(1, 31).all():
            return "day_number"

    # --------------------------------------------------------
    # Actual pandas datetime
    # --------------------------------------------------------

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # --------------------------------------------------------
    # Object/string date detection
    # --------------------------------------------------------

    non_null = series.dropna()

    if not non_null.empty:
        sample = non_null.astype(str).str.strip()

        # Date-like column names are stronger evidence than arbitrary
        # numeric-looking object columns.
        date_name_signal = any(
            token in normalized
            for token in [
                "date",
                "datetime",
                "timestamp",
                "time",
                "ordered",
                "created",
                "updated",
                "purchased",
                "transaction_date",
            ]
        )

        try:
            converted = pd.to_datetime(
                sample,
                errors="coerce",
                format="mixed",
            )

            valid_ratio = converted.notna().mean()

            if valid_ratio >= (
                0.70 if date_name_signal else 0.90
            ):
                return "datetime"

        except Exception:
            pass

    # --------------------------------------------------------
    # Numeric year detection even when the column is not
    # literally named "year"
    # --------------------------------------------------------

    numeric = _safe_numeric(series).dropna()

    if not numeric.empty:
        if numeric.between(1900, 2200).mean() >= 0.95:
            if (
                "year" in normalized
                or "yr" in normalized
            ):
                return "year_number"

    return "non_temporal"


def _convert_to_datetime(series):
    """
    Safely convert a pandas Series to datetime.

    This helper is intentionally NOT used for numeric month/day/year
    identifiers. Those are handled by _classify_temporal_column().
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    try:
        return pd.to_datetime(
            series,
            errors="coerce",
            format="mixed",
        )

    except Exception:
        return pd.to_datetime(
            series,
            errors="coerce",
        )


# ============================================================
# TEMPORAL LABEL HELPERS
# ============================================================

_MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def _month_number_data(df, x_column, y_column, aggregation):
    """
    Aggregate a numeric month-id column without converting it to datetime.
    """
    data = df[[x_column, y_column]].copy()

    month_values = _safe_numeric(data[x_column])
    data["_month_number"] = month_values

    data = data[
        data["_month_number"].between(1, 12)
    ].copy()

    if data.empty:
        raise ValueError(
            f"Column '{x_column}' does not contain valid "
            "month numbers from 1 to 12."
        )

    data["_month_number"] = (
        data["_month_number"].round().astype(int)
    )

    if aggregation == "count":
        result = (
            data.groupby("_month_number")
            .size()
            .reset_index(name="count")
        )
    else:
        data[y_column] = _safe_numeric(data[y_column])

        grouped = data.groupby(
            "_month_number",
            dropna=False,
        )[y_column]

        if aggregation == "sum":
            result = grouped.sum().reset_index()
        elif aggregation == "mean":
            result = grouped.mean().reset_index()
        elif aggregation == "min":
            result = grouped.min().reset_index()
        elif aggregation == "max":
            result = grouped.max().reset_index()
        else:
            raise ValueError(
                "Unsupported aggregation. "
                "Use sum, mean, count, min, or max."
            )

    result[x_column] = result["_month_number"].map(
        _MONTH_NAMES
    )

    # Preserve chronological month order.
    result["_month_sort"] = result["_month_number"]

    result = result.sort_values(
        "_month_sort"
    ).drop(
        columns=[
            "_month_number",
            "_month_sort",
        ]
    )

    return result


def _year_number_data(df, x_column, y_column, aggregation):
    """
    Aggregate a numeric year column without converting years into
    Unix timestamps.
    """
    data = df[[x_column, y_column]].copy()

    data["_year_number"] = _safe_numeric(
        data[x_column]
    )

    data = data[
        data["_year_number"].between(1900, 2200)
    ].copy()

    if data.empty:
        raise ValueError(
            f"Column '{x_column}' does not contain valid year values."
        )

    data["_year_number"] = (
        data["_year_number"].round().astype(int)
    )

    if aggregation == "count":
        result = (
            data.groupby("_year_number")
            .size()
            .reset_index(name="count")
        )
    else:
        data[y_column] = _safe_numeric(data[y_column])

        grouped = data.groupby(
            "_year_number",
            dropna=False,
        )[y_column]

        if aggregation == "sum":
            result = grouped.sum().reset_index()
        elif aggregation == "mean":
            result = grouped.mean().reset_index()
        elif aggregation == "min":
            result = grouped.min().reset_index()
        elif aggregation == "max":
            result = grouped.max().reset_index()
        else:
            raise ValueError(
                "Unsupported aggregation. "
                "Use sum, mean, count, min, or max."
            )

    result[x_column] = result["_year_number"].astype(str)

    result["_year_sort"] = result["_year_number"]

    result = result.sort_values(
        "_year_sort"
    ).drop(
        columns=[
            "_year_number",
            "_year_sort",
        ]
    )

    return result


def _day_number_data(df, x_column, y_column, aggregation):
    """
    Aggregate a numeric day-of-month/day-id column without converting
    it into a datetime.
    """
    data = df[[x_column, y_column]].copy()

    data["_day_number"] = _safe_numeric(
        data[x_column]
    )

    data = data[
        data["_day_number"].between(1, 31)
    ].copy()

    if data.empty:
        raise ValueError(
            f"Column '{x_column}' does not contain valid day values."
        )

    data["_day_number"] = (
        data["_day_number"].round().astype(int)
    )

    if aggregation == "count":
        result = (
            data.groupby("_day_number")
            .size()
            .reset_index(name="count")
        )
    else:
        data[y_column] = _safe_numeric(data[y_column])

        grouped = data.groupby(
            "_day_number",
            dropna=False,
        )[y_column]

        if aggregation == "sum":
            result = grouped.sum().reset_index()
        elif aggregation == "mean":
            result = grouped.mean().reset_index()
        elif aggregation == "min":
            result = grouped.min().reset_index()
        elif aggregation == "max":
            result = grouped.max().reset_index()
        else:
            raise ValueError(
                "Unsupported aggregation. "
                "Use sum, mean, count, min, or max."
            )

    result[x_column] = result["_day_number"].astype(str)

    result["_day_sort"] = result["_day_number"]

    result = result.sort_values(
        "_day_sort"
    ).drop(
        columns=[
            "_day_number",
            "_day_sort",
        ]
    )

    return result


# ============================================================
# TEMPORAL AGGREGATION
# ============================================================

def _aggregate_temporal_data(
    df,
    x_column,
    y_column,
    aggregation="sum",
    time_granularity="month",
):
    """
    Aggregate temporal data dynamically.

    Supported granularities:
        day
        week
        month
        quarter
        year

    Numeric month/year/day identifier columns are handled as identifiers,
    not as Unix timestamps.
    """
    _validate_columns(
        df,
        [x_column, y_column],
    )

    time_granularity = str(
        time_granularity or "month"
    ).lower().strip()

    temporal_kind = _classify_temporal_column(
        df[x_column],
        x_column,
    )

    # --------------------------------------------------------
    # Numeric temporal identifiers
    # --------------------------------------------------------

    if temporal_kind == "month_number":
        return _month_number_data(
            df,
            x_column,
            y_column,
            aggregation,
        )

    if temporal_kind == "year_number":
        return _year_number_data(
            df,
            x_column,
            y_column,
            aggregation,
        )

    if temporal_kind == "day_number":
        return _day_number_data(
            df,
            x_column,
            y_column,
            aggregation,
        )

    # --------------------------------------------------------
    # Actual datetime
    # --------------------------------------------------------

    data = df.copy()

    data[x_column] = _convert_to_datetime(
        data[x_column]
    )

    data = data.dropna(
        subset=[x_column]
    )

    if data.empty:
        raise ValueError(
            f"Column '{x_column}' does not contain valid date/time values."
        )

    if time_granularity == "day":
        data["_time_bucket"] = (
            data[x_column].dt.floor("D")
        )

    elif time_granularity == "week":
        data["_time_bucket"] = (
            data[x_column]
            .dt.to_period("W")
            .dt.start_time
        )

    elif time_granularity == "month":
        data["_time_bucket"] = (
            data[x_column]
            .dt.to_period("M")
            .dt.start_time
        )

    elif time_granularity == "quarter":
        data["_time_bucket"] = (
            data[x_column]
            .dt.to_period("Q")
            .dt.start_time
        )

    elif time_granularity == "year":
        data["_time_bucket"] = (
            data[x_column]
            .dt.to_period("Y")
            .dt.start_time
        )

    else:
        raise ValueError(
            "Unsupported time granularity. "
            "Use day, week, month, quarter, or year."
        )

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    if aggregation == "sum":
        result = (
            data.groupby("_time_bucket")[y_column]
            .sum()
            .reset_index()
        )

    elif aggregation == "mean":
        result = (
            data.groupby("_time_bucket")[y_column]
            .mean()
            .reset_index()
        )

    elif aggregation == "min":
        result = (
            data.groupby("_time_bucket")[y_column]
            .min()
            .reset_index()
        )

    elif aggregation == "max":
        result = (
            data.groupby("_time_bucket")[y_column]
            .max()
            .reset_index()
        )

    elif aggregation == "count":
        result = (
            data.groupby("_time_bucket")
            .size()
            .reset_index(name="count")
        )

    else:
        raise ValueError(
            "Unsupported aggregation. "
            "Use sum, mean, count, min, or max."
        )

    result = result.rename(
        columns={
            "_time_bucket": x_column,
        }
    )

    return result.sort_values(
        by=x_column
    ).reset_index(drop=True)


# ============================================================
# STANDARD AGGREGATION
# ============================================================

def _aggregate_data(
    df,
    x_column,
    y_column=None,
    aggregation="sum",
):
    """
    Aggregate dataframe data for categorical/group charts.
    """
    _validate_columns(
        df,
        [x_column],
    )

    if aggregation == "count":
        return (
            df.groupby(
                x_column,
                dropna=False,
            )
            .size()
            .reset_index(name="count")
        )

    if y_column is None:
        raise ValueError(
            f"Value column is required for "
            f"'{aggregation}' aggregation."
        )

    _validate_columns(
        df,
        [y_column],
    )

    data = df.copy()

    # Make numeric aggregation reliable even when CSV/Excel values
    # contain commas or currency symbols.
    data[y_column] = _safe_numeric(
        data[y_column]
    )

    grouped = data.groupby(
        x_column,
        dropna=False,
    )[y_column]

    if aggregation == "sum":
        return grouped.sum().reset_index()

    if aggregation == "mean":
        return grouped.mean().reset_index()

    if aggregation == "min":
        return grouped.min().reset_index()

    if aggregation == "max":
        return grouped.max().reset_index()

    raise ValueError(
        "Unsupported aggregation. "
        "Use sum, mean, count, min, or max."
    )


# ============================================================
# BAR CHART
# ============================================================

def create_bar_chart(
    df,
    x_column,
    y_column,
    aggregation="sum",
    title=None,
):
    """
    Create a dynamic bar chart.
    """
    data = _aggregate_data(
        df,
        x_column,
        y_column,
        aggregation,
    )

    chart_y_column = (
        "count"
        if aggregation == "count"
        else y_column
    )

    data = data.sort_values(
        by=chart_y_column,
        ascending=False,
    )

    if len(data) > 30:
        data = data.head(30)

    if title is None:
        if aggregation == "count":
            title = (
                f"Count of records by "
                f"{x_column}"
            )
        else:
            title = (
                f"{aggregation.title()} of "
                f"{y_column} by {x_column}"
            )

    figure = px.bar(
        data,
        x=x_column,
        y=chart_y_column,
        title=title,
    )

    figure.update_layout(
        xaxis_title=x_column,
        yaxis_title=(
            "Count"
            if aggregation == "count"
            else y_column
        ),
        height=500,
    )

    return figure


# ============================================================
# LINE CHART
# ============================================================

def create_line_chart(
    df,
    x_column,
    y_column,
    aggregation="sum",
    title=None,
    time_granularity=None,
):
    """
    Create a dynamic line chart.

    The function distinguishes:
        - real datetime columns
        - numeric month identifiers
        - numeric year identifiers
        - numeric day identifiers
        - ordinary categorical/numeric columns

    Numeric temporal identifiers are never blindly passed through
    pd.to_datetime(), which prevents 1969/1970 Unix-epoch charts.
    """
    _validate_columns(
        df,
        [x_column, y_column],
    )

    temporal_kind = _classify_temporal_column(
        df[x_column],
        x_column,
    )

    # --------------------------------------------------------
    # Numeric month/year/day identifier
    # --------------------------------------------------------

    if temporal_kind in {
        "month_number",
        "year_number",
        "day_number",
    }:
        if not time_granularity:
            if temporal_kind == "month_number":
                time_granularity = "month"
            elif temporal_kind == "year_number":
                time_granularity = "year"
            else:
                time_granularity = "day"

        data = _aggregate_temporal_data(
            df,
            x_column,
            y_column,
            aggregation,
            time_granularity,
        )

        is_datetime = False
        temporal_identifier = True

    # --------------------------------------------------------
    # Actual datetime
    # --------------------------------------------------------

    elif temporal_kind == "datetime":
        is_datetime = True
        temporal_identifier = False

        if not time_granularity:
            time_granularity = "month"

        data = _aggregate_temporal_data(
            df,
            x_column,
            y_column,
            aggregation,
            time_granularity,
        )

    # --------------------------------------------------------
    # Non-temporal line chart
    # --------------------------------------------------------

    else:
        is_datetime = False
        temporal_identifier = False

        data = _aggregate_data(
            df,
            x_column,
            y_column,
            aggregation,
        )

        # Numeric X columns should be sorted numerically.
        # Categorical columns are sorted naturally.
        try:
            data = data.sort_values(
                by=x_column
            )
        except Exception:
            pass

    chart_y_column = (
        "count"
        if aggregation == "count"
        else y_column
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if title is None:
        if temporal_kind == "month_number":
            title = (
                f"{aggregation.title()} of "
                f"{y_column} by month"
            )

        elif temporal_kind == "year_number":
            title = (
                f"{aggregation.title()} of "
                f"{y_column} by year"
            )

        elif temporal_kind == "day_number":
            title = (
                f"{aggregation.title()} of "
                f"{y_column} by day"
            )

        elif is_datetime:
            title = (
                f"{aggregation.title()} of "
                f"{y_column} by "
                f"{time_granularity}"
            )

        else:
            title = (
                f"{aggregation.title()} of "
                f"{y_column} over "
                f"{x_column}"
            )

    # --------------------------------------------------------
    # Create figure
    # --------------------------------------------------------

    figure = px.line(
        data,
        x=x_column,
        y=chart_y_column,
        title=title,
        markers=True,
    )

    # --------------------------------------------------------
    # Axis labels
    # --------------------------------------------------------

    if temporal_kind == "month_number":
        xaxis_title = "Month"

    elif temporal_kind == "year_number":
        xaxis_title = "Year"

    elif temporal_kind == "day_number":
        xaxis_title = "Day"

    elif is_datetime:
        xaxis_title = (
            f"{x_column} "
            f"({time_granularity})"
        )

    else:
        xaxis_title = x_column

    figure.update_layout(
        xaxis_title=xaxis_title,
        yaxis_title=(
            "Count"
            if aggregation == "count"
            else y_column
        ),
        height=500,
        margin=dict(
            l=70,
            r=30,
            t=80,
            b=90,
        ),
    )

    # --------------------------------------------------------
    # Date display
    # --------------------------------------------------------

    if is_datetime:
        if time_granularity == "year":
            figure.update_xaxes(
                tickformat="%Y"
            )

        elif time_granularity == "quarter":
            figure.update_xaxes(
                tickformat="%b %Y"
            )

        elif time_granularity == "day":
            figure.update_xaxes(
                tickformat="%d %b %Y"
            )

        else:
            figure.update_xaxes(
                tickformat="%b %Y"
            )

    # Month/day identifiers are categorical labels and should
    # remain labels rather than becoming timestamps.
    if temporal_identifier:
        figure.update_xaxes(
            type="category"
        )

    return figure


# ============================================================
# SCATTER CHART
# ============================================================

def create_scatter_chart(
    df,
    x_column,
    y_column,
    title=None,
):
    """
    Create a scatter plot for relationships between two numerical columns.
    """
    _validate_columns(
        df,
        [x_column, y_column],
    )

    data = df[
        [x_column, y_column]
    ].copy()

    data[x_column] = _safe_numeric(
        data[x_column]
    )

    data[y_column] = _safe_numeric(
        data[y_column]
    )

    data = data.dropna(
        subset=[
            x_column,
            y_column,
        ]
    )

    if data.empty:
        raise ValueError(
            "No valid numerical data available "
            "for scatter plot."
        )

    if title is None:
        title = (
            f"{y_column} vs {x_column}"
        )

    figure = px.scatter(
        data,
        x=x_column,
        y=y_column,
        title=title,
    )

    figure.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column,
        height=500,
    )

    return figure


# ============================================================
# PIE CHART
# ============================================================

def create_pie_chart(
    df,
    category_column,
    value_column,
    aggregation="sum",
    title=None,
):
    """
    Create a pie chart showing contribution of each category.
    """
    data = _aggregate_data(
        df,
        category_column,
        value_column,
        aggregation,
    )

    chart_value_column = (
        "count"
        if aggregation == "count"
        else value_column
    )

    if len(data) > 8:
        data = data.sort_values(
            by=chart_value_column,
            ascending=False,
        )

        top_data = data.head(7)

        other_value = data.iloc[7:][
            chart_value_column
        ].sum()

        if other_value > 0:
            other_row = pd.DataFrame({
                category_column: ["Other"],
                chart_value_column: [other_value],
            })

            data = pd.concat(
                [
                    top_data,
                    other_row,
                ],
                ignore_index=True,
            )

    if title is None:
        title = (
            f"{aggregation.title()} of "
            f"{value_column} by "
            f"{category_column}"
        )

    figure = px.pie(
        data,
        names=category_column,
        values=chart_value_column,
        title=title,
    )

    figure.update_layout(
        height=500,
    )

    return figure


# ============================================================
# HORIZONTAL BAR CHART
# ============================================================

def create_horizontal_bar_chart(
    df,
    category_column,
    value_column,
    aggregation="sum",
    title=None,
):
    """
    Create a horizontal bar chart.
    """
    data = _aggregate_data(
        df,
        category_column,
        value_column,
        aggregation,
    )

    chart_value_column = (
        "count"
        if aggregation == "count"
        else value_column
    )

    data = data.sort_values(
        by=chart_value_column,
        ascending=True,
    )

    if len(data) > 30:
        data = data.tail(30)

    if title is None:
        if aggregation == "count":
            title = (
                f"Count of records by "
                f"{category_column}"
            )
        else:
            title = (
                f"{aggregation.title()} of "
                f"{value_column} by "
                f"{category_column}"
            )

    figure = px.bar(
        data,
        x=chart_value_column,
        y=category_column,
        orientation="h",
        title=title,
    )

    figure.update_layout(
        xaxis_title=(
            "Count"
            if aggregation == "count"
            else value_column
        ),
        yaxis_title=category_column,
        height=500,
    )

    return figure


# ============================================================
# PERCENTAGE CHART
# ============================================================

def create_percentage_chart(
    df,
    category_column,
    value_column,
    chart_type="pie",
    title=None,
):
    """
    Create a chart showing percentage contribution of a numerical
    value across categories.
    """
    _validate_columns(
        df,
        [
            category_column,
            value_column,
        ],
    )

    data = df.copy()

    data[value_column] = _safe_numeric(
        data[value_column]
    )

    data = (
        data.groupby(
            category_column,
            dropna=False,
        )[value_column]
        .sum()
        .reset_index()
    )

    total = data[
        value_column
    ].sum()

    if total == 0:
        raise ValueError(
            "Cannot calculate percentage "
            "because the total value is zero."
        )

    data["Percentage"] = (
        data[value_column] / total
    ) * 100

    data = data.sort_values(
        by="Percentage",
        ascending=False,
    )

    if len(data) > 8:
        top_data = data.head(7)

        other_percentage = data.iloc[7:][
            "Percentage"
        ].sum()

        other_row = pd.DataFrame({
            category_column: ["Other"],
            "Percentage": [other_percentage],
        })

        data = pd.concat(
            [
                top_data[
                    [
                        category_column,
                        "Percentage",
                    ]
                ],
                other_row,
            ],
            ignore_index=True,
        )

    if title is None:
        title = (
            f"Percentage of {value_column} "
            f"by {category_column}"
        )

    if chart_type == "pie":
        figure = px.pie(
            data,
            names=category_column,
            values="Percentage",
            title=title,
        )

    elif chart_type == "bar":
        figure = px.bar(
            data,
            x=category_column,
            y="Percentage",
            title=title,
        )

        figure.update_layout(
            xaxis_title=category_column,
            yaxis_title="Percentage (%)",
        )

    else:
        raise ValueError(
            "Unsupported percentage chart type. "
            "Use 'pie' or 'bar'."
        )

    figure.update_layout(
        height=500,
    )

    return figure


# ============================================================
# CHART FACTORY
# ============================================================

def create_chart(
    df,
    chart_type,
    x_column=None,
    y_column=None,
    aggregation="sum",
    title=None,
    time_granularity=None,
):
    """
    General chart factory.

    This is the single entry point used by the question processing
    pipeline.
    """
    if not chart_type:
        raise ValueError(
            "Chart type is required."
        )

    chart_type = str(
        chart_type
    ).lower().strip()

    if chart_type not in SUPPORTED_CHARTS:
        raise ValueError(
            f"Unsupported chart type: {chart_type}"
        )

    # ========================================================
    # BAR
    # ========================================================

    if chart_type == "bar":
        return create_bar_chart(
            df,
            x_column,
            y_column,
            aggregation,
            title,
        )

    # ========================================================
    # LINE
    # ========================================================

    if chart_type == "line":
        return create_line_chart(
            df,
            x_column,
            y_column,
            aggregation,
            title,
            time_granularity,
        )

    # ========================================================
    # SCATTER
    # ========================================================

    if chart_type == "scatter":
        return create_scatter_chart(
            df,
            x_column,
            y_column,
            title,
        )

    # ========================================================
    # PIE
    # ========================================================

    if chart_type == "pie":
        return create_pie_chart(
            df,
            x_column,
            y_column,
            aggregation,
            title,
        )

    # ========================================================
    # HORIZONTAL BAR
    # ========================================================

    if chart_type == "horizontal_bar":
        return create_horizontal_bar_chart(
            df,
            x_column,
            y_column,
            aggregation,
            title,
        )

    # ========================================================
    # PERCENTAGE
    # ========================================================

    if chart_type == "percentage":
        return create_percentage_chart(
            df,
            x_column,
            y_column,
            chart_type="pie",
            title=title,
        )

    raise ValueError(
        f"Unsupported chart type: {chart_type}"
    )