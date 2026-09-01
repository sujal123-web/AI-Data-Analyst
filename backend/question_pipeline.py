import json
import re
from difflib import SequenceMatcher

import pandas as pd

from backend.data_engine.analysis_executor import execute_plan
from backend.data_engine.visualization_engine import create_chart
from backend.data_engine.visualization_planner import plan_visualization
from backend.agents.insight_agent import InsightAgent
from backend.question_planner import plan_question


# ============================================================
# COLUMN RESOLUTION
# ============================================================

PLAN_COLUMN_KEYS = [
    "column",
    "group_column",
    "value_column",
    "column1",
    "column2",
    "x_column",
    "y_column",
]


def _normalize_column_name(name):
    """Normalize a column name for safe matching."""

    if name is None:
        return ""

    name = str(name).strip().lower()
    return re.sub(r"[^a-z0-9]", "", name)


def _build_column_map(df):
    """Build a normalized column-name lookup."""

    column_map = {}

    for column in df.columns:
        normalized = _normalize_column_name(column)

        if normalized and normalized not in column_map:
            column_map[normalized] = column

    return column_map


def _resolve_column(df, requested_column):
    """
    Resolve an LLM-generated column name to an actual
    dataframe column.
    """

    if not requested_column:
        return requested_column

    requested_column = str(requested_column).strip()

    # 1. Exact
    if requested_column in df.columns:
        return requested_column

    # 2. Case-insensitive
    requested_lower = requested_column.lower()

    for column in df.columns:
        if str(column).strip().lower() == requested_lower:
            return column

    # 3. Normalized
    normalized_requested = _normalize_column_name(
        requested_column
    )

    column_map = _build_column_map(df)

    if normalized_requested in column_map:
        return column_map[normalized_requested]

    # 4. Safe fuzzy matching
    if not normalized_requested:
        return None

    candidates = []

    for normalized, actual_column in column_map.items():

        similarity = SequenceMatcher(
            None,
            normalized_requested,
            normalized
        ).ratio()

        candidates.append(
            (
                similarity,
                actual_column
            )
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if candidates:

        best_score, best_column = candidates[0]

        if best_score >= 0.88:
            return best_column

    return None


def _resolve_plan_columns(df, plan):
    """Resolve all column references contained in an analysis plan."""

    if not isinstance(plan, dict):
        return plan, []

    resolved_plan = dict(plan)
    unresolved_columns = []

    for key in PLAN_COLUMN_KEYS:

        if key not in resolved_plan:
            continue

        value = resolved_plan.get(key)

        if value is None:
            continue

        if isinstance(value, str):

            resolved_column = _resolve_column(
                df,
                value
            )

            if resolved_column is None:

                unresolved_columns.append(
                    {
                        "plan_key": key,
                        "requested": value
                    }
                )

            else:

                resolved_plan[key] = resolved_column

        elif isinstance(value, list):

            resolved_list = []

            for item in value:

                if not isinstance(item, str):
                    resolved_list.append(item)
                    continue

                resolved_column = _resolve_column(
                    df,
                    item
                )

                if resolved_column is None:

                    unresolved_columns.append(
                        {
                            "plan_key": key,
                            "requested": item
                        }
                    )

                else:

                    resolved_list.append(
                        resolved_column
                    )

            resolved_plan[key] = resolved_list

    return resolved_plan, unresolved_columns


# ============================================================
# TEMPORAL COLUMN / GRANULARITY HANDLING
# ============================================================

VALID_TIME_GRANULARITIES = {
    "day",
    "week",
    "month",
    "quarter",
    "year",
}


def _detect_time_granularity(question, plan):
    """
    Determine the requested temporal granularity.

    Planner output has priority. Natural-language detection is
    used as a safety net so a weak LLM plan cannot silently turn
    a yearly question into a monthly query.
    """

    if isinstance(plan, dict):

        value = plan.get("time_granularity")

        if value:
            value = str(value).strip().lower()

            aliases = {
                "daily": "day",
                "weekly": "week",
                "monthly": "month",
                "quarterly": "quarter",
                "yearly": "year",
                "annual": "year",
            }

            value = aliases.get(value, value)

            if value in VALID_TIME_GRANULARITIES:
                return value

    q = str(question or "").strip().lower()

    if any(
        phrase in q
        for phrase in [
            "yearly",
            "annual",
            "by year",
            "over the years",
            "year wise",
            "year-wise",
        ]
    ):
        return "year"

    if any(
        phrase in q
        for phrase in [
            "quarterly",
            "by quarter",
            "over the quarters",
            "quarter wise",
            "quarter-wise",
        ]
    ):
        return "quarter"

    if any(
        phrase in q
        for phrase in [
            "weekly",
            "by week",
            "over the weeks",
            "week wise",
            "week-wise",
        ]
    ):
        return "week"

    if any(
        phrase in q
        for phrase in [
            "monthly",
            "by month",
            "over the months",
            "month wise",
            "month-wise",
        ]
    ):
        return "month"

    if any(
        phrase in q
        for phrase in [
            "daily",
            "by day",
            "by date",
            "over the days",
            "day wise",
            "day-wise",
        ]
    ):
        return "day"

    # Generic "over time/date" defaults to month.
    if any(
        phrase in q
        for phrase in [
            "over time",
            "over date",
            "over order date",
            "by date",
            "by order date",
            "trend",
            "trends",
        ]
    ):
        return "month"

    return None


def _column_name_score(column, keywords):
    """Return a simple semantic score based on column name."""

    normalized = _normalize_column_name(column)

    score = 0

    for keyword in keywords:

        normalized_keyword = _normalize_column_name(keyword)

        if not normalized_keyword:
            continue

        if normalized == normalized_keyword:
            score += 100

        elif normalized_keyword in normalized:
            score += 30

    return score


def _find_temporal_column(df, granularity, preferred_column=None):
    """
    Select the safest temporal column for the requested
    granularity.

    Priority:
      1. Existing planner column if it is genuinely temporal.
      2. Datetime/date columns.
      3. Explicit YEAR/YEAR_ID, MONTH/MONTH_ID, DAY/DAY_ID.
    """

    columns = list(df.columns)

    # --------------------------------------------------------
    # 1. Prefer planner-selected column if it is appropriate
    # --------------------------------------------------------

    if preferred_column in columns:

        series = df[preferred_column]

        if pd.api.types.is_datetime64_any_dtype(series):
            return preferred_column

        name = _normalize_column_name(preferred_column)

        temporal_tokens = [
            "date",
            "datetime",
            "timestamp",
            "time",
            "year",
            "month",
            "day",
        ]

        if any(token in name for token in temporal_tokens):
            return preferred_column

    # --------------------------------------------------------
    # 2. Search actual datetime columns
    # --------------------------------------------------------

    datetime_candidates = []

    for column in columns:

        series = df[column]

        if pd.api.types.is_datetime64_any_dtype(series):
            datetime_candidates.append(column)
            continue

        if series.dtype == "object":

            sample = series.dropna().head(200)

            if len(sample) == 0:
                continue

            converted = pd.to_datetime(
                sample,
                errors="coerce"
            )

            if converted.notna().mean() >= 0.80:

                datetime_candidates.append(column)

    if datetime_candidates:

        scored = []

        for column in datetime_candidates:

            score = _column_name_score(
                column,
                [
                    "orderdate",
                    "order_date",
                    "order date",
                    "date",
                    "datetime",
                    "timestamp",
                    "transactiondate",
                    "transaction_date",
                ]
            )

            scored.append(
                (
                    score,
                    column
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return scored[0][1]

    # --------------------------------------------------------
    # 3. Explicit temporal ID/name columns
    # --------------------------------------------------------

    if granularity == "year":

        keywords = [
            "year",
            "year_id",
            "yearid",
        ]

    elif granularity == "quarter":

        keywords = [
            "quarter",
            "quarter_id",
            "quarterid",
        ]

    elif granularity == "month":

        keywords = [
            "month",
            "month_id",
            "monthid",
        ]

    elif granularity == "day":

        keywords = [
            "day",
            "day_id",
            "dayid",
        ]

    else:
        keywords = [
            "week",
            "week_id",
            "weekid",
        ]

    candidates = []

    for column in columns:

        score = _column_name_score(
            column,
            keywords
        )

        if score > 0:
            candidates.append(
                (
                    score,
                    column
                )
            )

    if candidates:

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return candidates[0][1]

    return None


def _is_temporal_question(question, plan):
    """Return True when the question requires time aggregation."""

    if not isinstance(plan, dict):
        return False

    if plan.get("time_granularity"):
        return True

    q = str(question or "").lower()

    temporal_terms = [
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "yearly",
        "annual",
        "by day",
        "by date",
        "by week",
        "by month",
        "by quarter",
        "by year",
        "over time",
        "over date",
        "trend",
        "trends",
    ]

    return any(
        term in q
        for term in temporal_terms
    )


def _prepare_temporal_plan(df, question, plan):
    """
    Enforce a safe temporal plan.

    This is intentionally done after the LLM planner and column
    resolver. It prevents a question such as "yearly sales" from
    accidentally using MONTH_ID just because the LLM selected it.
    """

    if not _is_temporal_question(question, plan):
        return plan

    if not isinstance(plan, dict):
        return plan

    granularity = _detect_time_granularity(
        question,
        plan
    )

    if granularity not in VALID_TIME_GRANULARITIES:
        return plan

    current_group_column = plan.get(
        "group_column"
    )

    temporal_column = _find_temporal_column(
        df,
        granularity,
        preferred_column=current_group_column
    )

    if temporal_column is None:
        return plan

    updated_plan = dict(plan)

    updated_plan["group_column"] = temporal_column
    updated_plan["time_granularity"] = granularity

    # Temporal questions should use a grouped numerical value.
    # Preserve the planner's value column.
    if updated_plan.get("operation") in [
        "group_sum",
        "group_average",
        "group_max",
        "group_min",
    ]:
        return updated_plan

    # Some planners may produce a generic group operation without
    # setting the operation correctly.
    if updated_plan.get("operation") is None:
        updated_plan["operation"] = "group_sum"

    return updated_plan


# ============================================================
# TEMPORAL ANALYSIS EXECUTION
# ============================================================

def _temporal_group_result(
    df,
    group_column,
    value_column,
    granularity,
    aggregation="sum",
):
    """
    Execute a temporal aggregation directly.

    This keeps the analysis result consistent with the requested
    day/week/month/quarter/year granularity. The visualization
    engine performs its own chart aggregation, but the InsightAgent
    also needs the correct analytical result.
    """

    if group_column not in df.columns:
        raise ValueError(
            f"Column '{group_column}' does not exist in the dataset."
        )

    if value_column not in df.columns:
        raise ValueError(
            f"Column '{value_column}' does not exist in the dataset."
        )

    if not pd.api.types.is_numeric_dtype(
        df[value_column]
    ):
        raise ValueError(
            f"Column '{value_column}' is not numerical."
        )

    working = df[
        [group_column, value_column]
    ].copy()

    # --------------------------------------------------------
    # Numeric temporal IDs
    # --------------------------------------------------------

    group_name = _normalize_column_name(
        group_column
    )

    if (
        granularity == "year"
        and (
            group_name in {"year", "yearid"}
            or "year" in group_name
        )
    ):
        grouped = (
            working.groupby(group_column)[value_column]
            .agg(aggregation)
        )

        return grouped.sort_index()

    if (
        granularity == "month"
        and (
            group_name in {"month", "monthid"}
            or "month" in group_name
        )
    ):
        grouped = (
            working.groupby(group_column)[value_column]
            .agg(aggregation)
        )

        return grouped.sort_index()

    if (
        granularity == "day"
        and (
            group_name in {"day", "dayid"}
            or "day" in group_name
        )
    ):
        grouped = (
            working.groupby(group_column)[value_column]
            .agg(aggregation)
        )

        return grouped.sort_index()

    if (
        granularity == "quarter"
        and "quarter" in group_name
    ):
        grouped = (
            working.groupby(group_column)[value_column]
            .agg(aggregation)
        )

        return grouped.sort_index()

    # --------------------------------------------------------
    # Real date/datetime column
    # --------------------------------------------------------

    dates = pd.to_datetime(
        working[group_column],
        errors="coerce"
    )

    valid = dates.notna()

    if not valid.any():
        raise ValueError(
            f"Column '{group_column}' could not be interpreted as dates."
        )

    working = working.loc[valid].copy()
    dates = dates.loc[valid]

    if granularity == "day":

        working["_time_key"] = dates.dt.to_period(
            "D"
        )

    elif granularity == "week":

        working["_time_key"] = dates.dt.to_period(
            "W"
        )

    elif granularity == "month":

        working["_time_key"] = dates.dt.to_period(
            "M"
        )

    elif granularity == "quarter":

        working["_time_key"] = dates.dt.to_period(
            "Q"
        )

    elif granularity == "year":

        working["_time_key"] = dates.dt.to_period(
            "Y"
        )

    else:

        raise ValueError(
            f"Unsupported time granularity: {granularity}"
        )

    grouped = (
        working.groupby("_time_key")[value_column]
        .agg(aggregation)
        .sort_index()
    )

    # Use readable labels while retaining chronological order.
    if granularity == "day":
        grouped.index = grouped.index.astype(str)

    elif granularity == "week":
        grouped.index = grouped.index.astype(str)

    elif granularity == "month":
        grouped.index = grouped.index.strftime("%Y-%m")

    elif granularity == "quarter":
        grouped.index = grouped.index.astype(str)

    elif granularity == "year":
        grouped.index = grouped.index.astype(str)

    return grouped


def _execute_with_temporal_support(df, plan):
    """
    Execute a plan while honoring time_granularity when present.
    """

    if not isinstance(plan, dict):
        return execute_plan(df, plan)

    granularity = plan.get(
        "time_granularity"
    )

    operation = plan.get(
        "operation"
    )

    if (
        granularity in VALID_TIME_GRANULARITIES
        and operation in [
            "group_sum",
            "group_average",
            "group_max",
            "group_min",
        ]
    ):

        aggregation_map = {
            "group_sum": "sum",
            "group_average": "mean",
            "group_max": "max",
            "group_min": "min",
        }

        return _temporal_group_result(
            df=df,
            group_column=plan.get(
                "group_column"
            ),
            value_column=plan.get(
                "value_column"
            ),
            granularity=granularity,
            aggregation=aggregation_map[
                operation
            ],
        )

    return execute_plan(
        df,
        plan
    )


# ============================================================
# FIGURE SERIALIZATION
# ============================================================

def _serialize_figure(figure):
    """Convert a Plotly Figure into a JSON-compatible dictionary."""

    if figure is None:
        return None

    try:

        return json.loads(
            figure.to_json()
        )

    except Exception as error:

        return {
            "error": f"Could not serialize chart: {error}"
        }


# ============================================================
# MAIN QUESTION PIPELINE
# ============================================================

def process_question(df, profile, question):
    """
    Process a natural-language question from start to finish.

    Complete flow:

        User Question
              ↓
        Question Planner
              ↓
        Column Resolver
              ↓
        Temporal Safety Layer
              ↓
        Analysis Executor
              ↓
        Visualization Planner
              ↓
        Visualization Engine
              ↓
        Insight Agent
              ↓
        Complete Response
    """

    # ========================================================
    # STEP 1: CREATE ANALYSIS PLAN
    # ========================================================

    try:

        plan = plan_question(
            question,
            profile
        )

        print("\n========== DEBUG PLAN ==========")
        print(plan)
        print("================================\n")

    except Exception as error:

        return {
            "question": question,
            "plan": None,
            "result": None,
            "visualization": None,
            "answer": (
                "I could not process this question. "
                f"Planner error: {error}"
            )
        }

    # ========================================================
    # STEP 2: HANDLE PLANNER FAILURE
    # ========================================================

    if not plan:

        return {
            "question": question,
            "plan": None,
            "result": None,
            "visualization": None,
            "answer": "I could not understand the question."
        }

    # ========================================================
    # STEP 3: HANDLE UNSUPPORTED QUESTIONS
    # ========================================================

    if plan.get("operation") == "unsupported":

        reason = plan.get(
            "reason",
            "This question cannot be answered from the dataset."
        )

        return {
            "question": question,
            "plan": plan,
            "result": None,
            "visualization": {
                "chart_type": "none",
                "reason": "Question is unsupported."
            },
            "answer": reason
        }

    # ========================================================
    # STEP 4: RESOLVE DATAFRAME COLUMNS
    # ========================================================

    plan, unresolved_columns = _resolve_plan_columns(
        df,
        plan
    )

    # ========================================================
    # STEP 5: HANDLE INVALID COLUMN REFERENCES
    # ========================================================

    if unresolved_columns:

        requested = [
            item["requested"]
            for item in unresolved_columns
        ]

        available_columns = [
            str(column)
            for column in df.columns
        ]

        return {
            "question": question,
            "plan": plan,
            "result": {
                "error": (
                    "The requested column(s) could not "
                    "be matched to the dataset."
                ),
                "requested_columns": requested,
                "available_columns": available_columns
            },
            "visualization": {
                "chart_type": "none",
                "reason": "Column resolution failed."
            },
            "answer": (
                "I couldn't find "
                + ", ".join(
                    f"'{column}'"
                    for column in requested
                )
                + " in the dataset."
            )
        }

    # ========================================================
    # STEP 6: ENFORCE TEMPORAL GRANULARITY
    # ========================================================

    plan = _prepare_temporal_plan(
        df,
        question,
        plan
    )

    print("\n======= FINAL RESOLVED PLAN =======")
    print(plan)
    print("===================================\n")

    # ========================================================
    # STEP 7: EXECUTE ANALYSIS
    # ========================================================

    try:

        result = _execute_with_temporal_support(
            df,
            plan
        )

    except Exception as error:

        return {
            "question": question,
            "plan": plan,
            "result": {
                "error": str(error)
            },
            "visualization": {
                "chart_type": "none",
                "reason": "Analysis failed."
            },
            "answer": (
                f"I could not complete the analysis: {error}"
            )
        }

    # ========================================================
    # STEP 8: HANDLE ANALYSIS ERRORS
    # ========================================================

    if isinstance(result, dict) and "error" in result:

        return {
            "question": question,
            "plan": plan,
            "result": result,
            "visualization": {
                "chart_type": "none",
                "reason": "Analysis failed."
            },
            "answer": result["error"]
        }

    # ========================================================
    # STEP 9: CREATE VISUALIZATION PLAN
    # ========================================================

    try:

        visualization_plan = plan_visualization(
            question,
            plan,
            profile
        )

    except Exception as error:

        visualization_plan = {
            "chart_type": "none",
            "reason": str(error)
        }

    # ========================================================
    # STEP 10: PROPAGATE TEMPORAL GRANULARITY
    # ========================================================

    if isinstance(visualization_plan, dict):

        visualization_plan = dict(
            visualization_plan
        )

        if plan.get("time_granularity"):

            visualization_plan[
                "time_granularity"
            ] = plan.get(
                "time_granularity"
            )

        # If visualization planner chose the wrong temporal
        # grouping column, force the safe resolved column.
        if (
            plan.get("time_granularity")
            and plan.get("group_column")
        ):

            if visualization_plan.get(
                "x_column"
            ):

                visualization_plan[
                    "x_column"
                ] = plan.get(
                    "group_column"
                )

            if visualization_plan.get(
                "chart_type"
            ) == "line":

                visualization_plan[
                    "x_column"
                ] = plan.get(
                    "group_column"
                )

    # ========================================================
    # STEP 11: RESOLVE COLUMNS IN VISUALIZATION PLAN
    # ========================================================

    visualization_plan, visualization_unresolved = (
        _resolve_plan_columns(
            df,
            visualization_plan
        )
    )

    # Temporal plan takes priority over generic visualization
    # planner guesses.
    if (
        plan.get("time_granularity")
        and plan.get("group_column")
        and isinstance(visualization_plan, dict)
    ):

        visualization_plan[
            "x_column"
        ] = plan.get(
            "group_column"
        )

        visualization_plan[
            "time_granularity"
        ] = plan.get(
            "time_granularity"
        )

    if visualization_unresolved:

        visualization_plan = {
            **visualization_plan,
            "chart_type": "none",
            "reason": (
                "Visualization column could not be resolved."
            )
        }

    # ========================================================
    # STEP 12: CREATE ACTUAL CHART
    # ========================================================

    visualization_response = dict(
        visualization_plan
    )

    chart_type = visualization_plan.get(
        "chart_type"
    )

    # --------------------------------------------------------
    # No chart required
    # --------------------------------------------------------

    if chart_type in [
        None,
        "none"
    ]:

        visualization_response[
            "figure"
        ] = None

    # --------------------------------------------------------
    # Chart required
    # --------------------------------------------------------

    else:

        try:

            figure = create_chart(
                df=df,
                chart_type=chart_type,
                x_column=visualization_plan.get(
                    "x_column"
                ),
                y_column=visualization_plan.get(
                    "y_column"
                ),
                aggregation=visualization_plan.get(
                    "aggregation",
                    "sum"
                ),
                time_granularity=visualization_plan.get(
                    "time_granularity"
                )
            )

            visualization_response[
                "figure"
            ] = _serialize_figure(
                figure
            )

        except TypeError as error:

            # Compatibility fallback for older create_chart()
            # signatures that do not yet accept time_granularity.
            if "time_granularity" in str(error):

                try:

                    figure = create_chart(
                        df=df,
                        chart_type=chart_type,
                        x_column=visualization_plan.get(
                            "x_column"
                        ),
                        y_column=visualization_plan.get(
                            "y_column"
                        ),
                        aggregation=visualization_plan.get(
                            "aggregation",
                            "sum"
                        )
                    )

                    visualization_response[
                        "figure"
                    ] = _serialize_figure(
                        figure
                    )

                except Exception as fallback_error:

                    visualization_response = {
                        **visualization_plan,
                        "figure": None,
                        "error": str(
                            fallback_error
                        )
                    }

            else:

                visualization_response = {
                    **visualization_plan,
                    "figure": None,
                    "error": str(error)
                }

        except Exception as error:

            visualization_response = {
                **visualization_plan,
                "figure": None,
                "error": str(error)
            }

    # ========================================================
    # STEP 13: GENERATE BUSINESS-FRIENDLY ANSWER
    # ========================================================

    try:

        insight_agent = InsightAgent(
            df,
            profile
        )

        answer = insight_agent.answer(
            question,
            plan,
            result
        )

    except Exception as error:

        answer = (
            "The analysis completed successfully, "
            "but I could not generate the explanation: "
            f"{error}"
        )

    # ========================================================
    # STEP 14: RETURN COMPLETE RESPONSE
    # ========================================================

    return {
        "question": question,
        "plan": plan,
        "result": result,
        "visualization": visualization_response,
        "answer": answer
    }
