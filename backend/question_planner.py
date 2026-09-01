import json
import re

from backend.llm.llm_client import generate_response


SUPPORTED_OPERATIONS = [
    "total",
    "average",
    "minimum",
    "maximum",
    "count",
    "unique_count",
    "missing_count",
    "group_sum",
    "group_average",
    "group_count",
    "group_max",
    "group_min",
    "top_n",
    "bottom_n",
    "correlation",
    "describe",
    "group_percentage",
    "unsupported",
]


# ============================================================
# RESPONSE CLEANING
# ============================================================

def clean_response(response):
    """
    Clean common Markdown formatting from the LLM response.
    """

    if not response:
        return ""

    response = response.strip()

    # Remove ```json
    response = re.sub(
        r"^```json\s*",
        "",
        response,
        flags=re.IGNORECASE
    )

    # Remove ```
    response = re.sub(
        r"^```\s*",
        "",
        response
    )

    # Remove closing ```
    response = re.sub(
        r"\s*```$",
        "",
        response
    )

    return response.strip()


# ============================================================
# COLUMN RESOLUTION
# ============================================================

def _normalize_column_name(value):
    """
    Normalize a column name for flexible comparison.

    Examples:
        "Sales"       -> "sales"
        "SALES"       -> "sales"
        "Order Date"  -> "orderdate"
        "Order_Date"  -> "orderdate"
        "Order-Date"  -> "orderdate"
    """

    if value is None:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def _resolve_column(profile, requested_column):
    """
    Resolve an LLM-generated or user-requested column name
    to the exact original dataset column.

    Matching priority:

        1. Exact match
        2. Case-insensitive match
        3. Normalized match
        4. Semantic synonym match
        5. Category-aware match

    Returns:
        Exact original dataset column name
        or None if no confident match exists.
    """

    if not requested_column:
        return None

    if not isinstance(profile, dict):
        return None

    column_details = profile.get(
        "column_details",
        {}
    )

    if not isinstance(column_details, dict):
        return None

    requested = str(
        requested_column
    ).strip()

    if not requested:
        return None

    # ========================================================
    # 1. EXACT MATCH
    # ========================================================

    if requested in column_details:
        return requested

    # ========================================================
    # 2. CASE-INSENSITIVE MATCH
    # ========================================================

    requested_lower = requested.lower()

    for column in column_details.keys():

        if str(column).strip().lower() == requested_lower:
            return column

    # ========================================================
    # 3. NORMALIZED MATCH
    # ========================================================

    requested_normalized = _normalize_column_name(
        requested
    )

    if requested_normalized:

        for column in column_details.keys():

            column_normalized = _normalize_column_name(
                column
            )

            if (
                column_normalized
                and column_normalized == requested_normalized
            ):
                return column

    # ========================================================
    # 4. SEMANTIC SYNONYMS
    # ========================================================

    semantic_groups = {

        "sales": [
            "sales",
            "sale",
            "salesamount",
            "sales_amount",
            "total_sales",
            "total sales",
            "salesvalue",
            "sales_value",
            "revenue",
            "total_revenue",
            "total revenue",
            "revenueamount",
            "revenue_amount",
            "turnover",
            "order_value",
            "order value",
            "transaction_value",
            "transaction value",
            "amount"
        ],

        "quantity": [
            "quantity",
            "qty",
            "quantityordered",
            "quantity_ordered",
            "units",
            "units_sold",
            "unitssold",
            "number_of_units",
            "number of units"
        ],

        "date": [
            "date",
            "orderdate",
            "order_date",
            "order date",
            "transactiondate",
            "transaction_date",
            "transaction date",
            "salesdate",
            "sales_date",
            "sale_date",
            "purchase_date",
            "purchase date",
            "created_date",
            "created date",
            "timestamp",
            "datetime",
            "time"
        ],

        "country": [
            "country",
            "nation",
            "location_country",
            "customer_country",
            "shipping_country"
        ],

        "region": [
            "region",
            "area",
            "territory",
            "zone"
        ],

        "product": [
            "product",
            "product_name",
            "productname",
            "item",
            "item_name",
            "itemname"
        ],

        "category": [
            "category",
            "product_category",
            "productcategory",
            "type",
            "class"
        ],

        "customer": [
            "customer",
            "customer_name",
            "customername",
            "client",
            "client_name"
        ]
    }

    requested_normalized = _normalize_column_name(
        requested
    )

    requested_group = None

    for group, synonyms in semantic_groups.items():

        normalized_synonyms = [
            _normalize_column_name(item)
            for item in synonyms
        ]

        if (
            requested_normalized in normalized_synonyms
        ):
            requested_group = group
            break

    # ========================================================
    # 5. SCORE SEMANTIC CANDIDATES
    # ========================================================

    if requested_group:

        candidates = []

        synonyms = semantic_groups[
            requested_group
        ]

        normalized_synonyms = [
            _normalize_column_name(item)
            for item in synonyms
        ]

        for column, details in column_details.items():

            column_string = str(column).strip()

            column_normalized = _normalize_column_name(
                column_string
            )

            category = details.get(
                "category"
            )

            score = 0

            # ------------------------------------------------
            # Exact semantic synonym
            # ------------------------------------------------

            if column_normalized in normalized_synonyms:
                score += 100

            # ------------------------------------------------
            # Requested concept contained in column
            # ------------------------------------------------

            for synonym in normalized_synonyms:

                if not synonym:
                    continue

                if synonym in column_normalized:
                    score += 40

                elif column_normalized in synonym:
                    score += 25

            # ------------------------------------------------
            # Category awareness
            # ------------------------------------------------

            if requested_group in [
                "sales",
                "quantity"
            ]:

                if category == "numerical":
                    score += 30

            elif requested_group in [
                "date"
            ]:

                if category == "temporal":
                    score += 50

            elif requested_group in [
                "country",
                "region",
                "product",
                "category",
                "customer"
            ]:

                if category in [
                    "categorical",
                    "geographic",
                    "temporal"
                ]:
                    score += 20

            # ------------------------------------------------
            # Strong name indicators
            # ------------------------------------------------

            if requested_group == "sales":

                if "sales" in column_normalized:
                    score += 35

                if "revenue" in column_normalized:
                    score += 30

                if "profit" in column_normalized:
                    score -= 60

                if "cost" in column_normalized:
                    score -= 50

            # ------------------------------------------------
            # Keep candidates with useful scores
            # ------------------------------------------------

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

            best_score, best_column = candidates[0]

            # Require reasonable confidence.
            if best_score >= 50:
                return best_column

    # ========================================================
    # 6. GENERIC FUZZY CONTAINMENT
    # ========================================================

    for column in column_details.keys():

        column_normalized = _normalize_column_name(
            column
        )

        if not column_normalized:
            continue

        if (
            requested_normalized
            and requested_normalized in column_normalized
        ):
            return column

    return None


# ============================================================
# TIME / DATE RESOLUTION
# ============================================================

def _find_exact_column(profile, candidates):
    """
    Return the first exact dataset column matching one of the
    supplied names, case-insensitively/normalized.
    """
    columns = profile.get("column_details", {})

    if not isinstance(columns, dict):
        return None

    for candidate in candidates:
        if candidate in columns:
            return candidate

        candidate_lower = str(candidate).strip().lower()

        for column in columns.keys():
            if str(column).strip().lower() == candidate_lower:
                return column

    normalized_candidates = {
        _normalize_column_name(candidate)
        for candidate in candidates
    }

    for column in columns.keys():
        if _normalize_column_name(column) in normalized_candidates:
            return column

    return None


def _find_date_column(profile):
    """
    Find the real date column. Prefer ORDERDATE/date-like columns
    over derived numeric time IDs.
    """
    preferred = _find_exact_column(
        profile,
        [
            "ORDERDATE",
            "ORDER_DATE",
            "OrderDate",
            "date",
            "DATE",
            "transaction_date",
            "TRANSACTION_DATE",
            "sales_date",
            "SALES_DATE",
            "purchase_date",
            "PURCHASE_DATE",
        ],
    )

    if preferred:
        return preferred

    return _find_column(
        profile,
        [
            "orderdate",
            "order_date",
            "date",
            "transactiondate",
            "transaction_date",
            "salesdate",
            "sales_date",
            "sale_date",
            "purchase_date",
            "created_date",
            "timestamp",
            "datetime",
        ],
        category="temporal",
    )


def _find_time_group_column(profile, granularity):
    """
    Resolve the correct dataset column for a requested time
    granularity.

    year    -> YEAR_ID when available
    quarter -> QTR_ID when available
    month   -> MONTH_ID when available
    day/week -> real date column
    """
    granularity = str(granularity or "").strip().lower()

    if granularity == "year":
        return _find_exact_column(
            profile,
            ["YEAR_ID", "YEAR", "year_id", "year"],
        ) or _find_date_column(profile)

    if granularity == "quarter":
        return _find_exact_column(
            profile,
            ["QTR_ID", "QUARTER_ID", "QUARTER", "quarter"],
        ) or _find_date_column(profile)

    if granularity == "month":
        return _find_exact_column(
            profile,
            ["MONTH_ID", "MONTH", "month_id", "month"],
        ) or _find_date_column(profile)

    if granularity in {"day", "week"}:
        return _find_date_column(profile)

    return None


def _is_time_dimension_column(column, granularity):
    """
    Determine whether a column is an acceptable time dimension
    for the requested granularity.

    Numeric YEAR_ID/MONTH_ID/QTR_ID columns are intentionally
    accepted because they are time IDs, not ordinary measures.
    """
    normalized = _normalize_column_name(column)
    granularity = str(granularity or "").strip().lower()

    aliases = {
        "year": {
            "year",
            "yearid",
        },
        "quarter": {
            "quarter",
            "quarterid",
            "qtr",
            "qtrid",
        },
        "month": {
            "month",
            "monthid",
        },
        "day": {
            "date",
            "orderdate",
            "transactiondate",
            "salesdate",
            "saledate",
            "purchasedate",
            "createddate",
            "timestamp",
            "datetime",
        },
        "week": {
            "date",
            "orderdate",
            "transactiondate",
            "salesdate",
            "saledate",
            "purchasedate",
            "createddate",
            "timestamp",
            "datetime",
        },
    }

    return normalized in aliases.get(granularity, set())


def _normalize_time_plan(plan, profile):
    """
    Deterministically repair temporal plans.

    The LLM may identify the requested granularity, but the
    matching time column is selected by deterministic rules.
    """
    if not isinstance(plan, dict):
        return plan

    granularity = plan.get("time_granularity")

    if not granularity:
        return plan

    granularity = str(granularity).strip().lower()

    aliases = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "quarterly": "quarter",
        "yearly": "year",
        "annual": "year",
    }

    granularity = aliases.get(granularity, granularity)

    if granularity not in {
        "day",
        "week",
        "month",
        "quarter",
        "year",
    }:
        return plan

    time_column = _find_time_group_column(
        profile,
        granularity
    )

    if time_column:
        plan["group_column"] = time_column

    plan["time_granularity"] = granularity

    return plan


# ============================================================
# PLAN VALIDATION
# ============================================================

def validate_plan(plan, profile):
    """
    Validate the LLM-generated analysis plan against
    the actual dataset profile.
    """

    if not isinstance(plan, dict):

        return {
            "operation": "unsupported",
            "reason": "Invalid analysis plan."
        }

    # --------------------------------------------------------
    # Deterministically repair temporal plans BEFORE resolving
    # normal columns. This prevents questions such as
    # "yearly sales" from becoming:
    #     group_column = MONTH_ID
    #     time_granularity = year
    # --------------------------------------------------------

    plan = _normalize_time_plan(
        plan,
        profile
    )

    operation = plan.get("operation")

    # --------------------------------------------------------
    # Resolve LLM-generated column names
    # to the actual dataset column names
    # --------------------------------------------------------

    column_fields = [
        "column",
        "group_column",
        "value_column",
        "column1",
        "column2",
    ]

    for field in column_fields:

        if plan.get(field):

            resolved_column = _resolve_column(
                profile,
                plan.get(field)
            )

            if resolved_column:
                plan[field] = resolved_column

    # --------------------------------------------------------
    # Validate operation
    # --------------------------------------------------------

    if operation not in SUPPORTED_OPERATIONS:

        return {
            "operation": "unsupported",
            "reason": f"Unsupported operation: {operation}"
        }

    column_details = profile.get(
        "column_details",
        {}
    )

    # --------------------------------------------------------
    # Count
    # --------------------------------------------------------

    if operation == "count":

        return {
            "operation": "count"
        }

    # --------------------------------------------------------
    # Single-column operations
    # --------------------------------------------------------

    single_column_operations = [
        "total",
        "average",
        "minimum",
        "maximum",
        "unique_count",
        "missing_count",
        "describe",
    ]

    if operation in single_column_operations:

        column = plan.get("column")

        if not column:

            return {
                "operation": "unsupported",
                "reason": "No column was specified."
            }

        if column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{column}' does not exist."
                )
            }

        # Numerical operations
        if operation in [
            "total",
            "average",
            "minimum",
            "maximum",
            "describe",
        ]:

            if (
                column_details[column].get("category")
                != "numerical"
            ):

                return {
                    "operation": "unsupported",
                    "reason": (
                        f"Column '{column}' is not numerical."
                    )
                }

        return plan

    # --------------------------------------------------------
    # Group value operations
    # --------------------------------------------------------

    group_value_operations = [
        "group_sum",
        "group_average",
        "group_max",
        "group_min",
        "group_percentage",
    ]

    if operation in group_value_operations:

        group_column = plan.get("group_column")
        value_column = plan.get("value_column")

        if not group_column:

            return {
                "operation": "unsupported",
                "reason": "No group column was specified."
            }

        if not value_column:

            return {
                "operation": "unsupported",
                "reason": "No value column was specified."
            }

        if group_column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' does not exist."
                )
            }

        if value_column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{value_column}' does not exist."
                )
            }

        # Value column must be numerical
        if (
            column_details[value_column].get("category")
            != "numerical"
        ):

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{value_column}' is not numerical."
                )
            }

        # --------------------------------------------------------
        # Temporal aggregation validation
        # --------------------------------------------------------

        time_granularity = plan.get("time_granularity")

        if time_granularity is not None:

            allowed_granularities = {
                "day",
                "week",
                "month",
                "quarter",
                "year",
            }

            if time_granularity not in allowed_granularities:
                return {
                    "operation": "unsupported",
                    "reason": (
                        "Invalid time_granularity. Use one of: "
                        "day, week, month, quarter, year."
                    ),
                }

            group_category = column_details[group_column].get(
                "category"
            )

            # Real date columns are temporal. Derived time IDs such
            # as YEAR_ID, MONTH_ID and QTR_ID may be numerical, but
            # they are still valid time dimensions.
            is_time_id = _is_time_dimension_column(
                group_column,
                time_granularity
            )

            if (
                group_category != "temporal"
                and not is_time_id
            ):
                return {
                    "operation": "unsupported",
                    "reason": (
                        f"Column '{group_column}' is not a valid "
                        f"time column for {time_granularity} aggregation."
                    ),
                }

        # Ordinary numerical columns are not valid group columns.
        # Time IDs are the intentional exception above.
        if (
            column_details[group_column].get("category")
            == "numerical"
            and not _is_time_dimension_column(
                group_column,
                plan.get("time_granularity")
            )
        ):
            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' should be "
                    "categorical, temporal, or geographic."
                )
            }

        return plan

    # --------------------------------------------------------
    # Group count
    # --------------------------------------------------------

    if operation == "group_count":

        group_column = plan.get("group_column")

        if not group_column:

            return {
                "operation": "unsupported",
                "reason": "No group column was specified."
            }

        if group_column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' does not exist."
                )
            }

        if (
            column_details[group_column].get("category")
            == "numerical"
        ):

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' should not "
                    "be numerical."
                )
            }

        return plan

    # --------------------------------------------------------
    # Top / Bottom N
    # --------------------------------------------------------

    if operation in [
        "top_n",
        "bottom_n",
    ]:

        group_column = plan.get("group_column")
        value_column = plan.get("value_column")
        n = plan.get("n")

        if not group_column or not value_column:

            return {
                "operation": "unsupported",
                "reason": (
                    "Ranking operation requires "
                    "group_column and value_column."
                )
            }

        if group_column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' does not exist."
                )
            }

        if value_column not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{value_column}' does not exist."
                )
            }

        if (
            column_details[value_column].get("category")
            != "numerical"
        ):

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{value_column}' is not numerical."
                )
            }

        if (
            column_details[group_column].get("category")
            == "numerical"
        ):

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{group_column}' should be "
                    "categorical, temporal, or geographic."
                )
            }

        try:

            n = int(n)

        except (TypeError, ValueError):

            return {
                "operation": "unsupported",
                "reason": "n must be a positive integer."
            }

        if n <= 0:

            return {
                "operation": "unsupported",
                "reason": "n must be greater than zero."
            }

        return {
            "operation": operation,
            "group_column": group_column,
            "value_column": value_column,
            "n": n,
        }

    # --------------------------------------------------------
    # Correlation
    # --------------------------------------------------------

    if operation == "correlation":

        column1 = plan.get("column1")
        column2 = plan.get("column2")

        if not column1 or not column2:

            return {
                "operation": "unsupported",
                "reason": (
                    "Correlation requires two columns."
                )
            }

        if column1 not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{column1}' does not exist."
                )
            }

        if column2 not in column_details:

            return {
                "operation": "unsupported",
                "reason": (
                    f"Column '{column2}' does not exist."
                )
            }

        if (
            column_details[column1].get("category")
            != "numerical"
            or
            column_details[column2].get("category")
            != "numerical"
        ):

            return {
                "operation": "unsupported",
                "reason": (
                    "Correlation requires two numerical columns."
                )
            }

        return plan

    # --------------------------------------------------------
    # Unsupported
    # --------------------------------------------------------

    if operation == "unsupported":

        return {
            "operation": "unsupported",
            "reason": plan.get(
                "reason",
                "The question cannot be answered."
            )
        }

    return plan


# ============================================================
# FAST QUESTION PLANNER
# ============================================================

def _find_column(profile, keywords, category=None):
    """
    Find the best matching dataset column using
    semantic scoring rather than first-match logic.

    This prevents accidental selection of the wrong
    column when multiple columns contain similar words.
    """

    columns = profile.get(
        "column_details",
        {}
    )

    if not isinstance(columns, dict):
        return None

    if not keywords:
        return None

    candidates = []

    for column, details in columns.items():

        if category:

            if details.get("category") != category:
                continue

        column_name = str(column).strip()

        normalized_column = _normalize_column_name(
            column_name
        )

        if not normalized_column:
            continue

        score = 0

        for keyword in keywords:

            keyword_string = str(
                keyword
            ).strip()

            normalized_keyword = _normalize_column_name(
                keyword_string
            )

            if not normalized_keyword:
                continue

            # ---------------------------------------------
            # Exact
            # ---------------------------------------------

            if column_name.lower() == keyword_string.lower():

                score = max(
                    score,
                    100
                )

            # ---------------------------------------------
            # Normalized exact
            # ---------------------------------------------

            elif (
                normalized_column
                == normalized_keyword
            ):

                score = max(
                    score,
                    95
                )

            # ---------------------------------------------
            # Starts with
            # ---------------------------------------------

            elif normalized_column.startswith(
                normalized_keyword
            ):

                score = max(
                    score,
                    75
                )

            # ---------------------------------------------
            # Ends with
            # ---------------------------------------------

            elif normalized_column.endswith(
                normalized_keyword
            ):

                score = max(
                    score,
                    70
                )

            # ---------------------------------------------
            # Contains
            # ---------------------------------------------

            elif normalized_keyword in normalized_column:

                score = max(
                    score,
                    60
                )

        if score > 0:

            # Numerical columns get preference when
            # numerical category was requested.
            if category == "numerical":
                score += 20

            candidates.append(
                (
                    score,
                    column
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]

def _find_numerical_column(profile, keywords):
    """
    Find a numerical column using semantic keywords.
    """

    return _find_column(
        profile,
        keywords,
        category="numerical"
    )


def _find_categorical_column(profile, keywords):
    """
    Find the best categorical, geographic, or temporal column
    using semantic scoring rather than first-match logic.
    """

    columns = profile.get(
        "column_details",
        {}
    )

    if not isinstance(columns, dict) or not keywords:
        return None

    candidates = []

    for column, details in columns.items():

        category = details.get("category")

        if category not in [
            "categorical",
            "geographic",
            "temporal",
        ]:
            continue

        name = str(column).strip()
        normalized_name = _normalize_column_name(name)
        score = 0

        for keyword in keywords:

            keyword = str(keyword).strip()
            normalized_keyword = _normalize_column_name(keyword)

            if not normalized_keyword:
                continue

            if name.lower() == keyword.lower():
                score = max(score, 100)
            elif normalized_name == normalized_keyword:
                score = max(score, 95)
            elif normalized_name.startswith(normalized_keyword):
                score = max(score, 75)
            elif normalized_name.endswith(normalized_keyword):
                score = max(score, 70)
            elif normalized_keyword in normalized_name:
                score = max(score, 60)

        if score > 0:

            # Temporal columns are preferred for date/time keywords.
            normalized_keywords = {
                _normalize_column_name(keyword)
                for keyword in keywords
            }

            if category == "temporal" and normalized_keywords.intersection({
                "date", "orderdate", "transactiondate",
                "salesdate", "saledate", "purchasedate",
                "month", "year", "day", "time",
                "timestamp", "datetime"
            }):
                score += 25

            candidates.append((score, column))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def _is_likely_sales_column(column_name):
    """
    Determine whether a column name is likely to represent
    sales/revenue rather than profit, cost, tax, or discount.
    """

    if not column_name:
        return False

    name = _normalize_column_name(column_name)

    negative_terms = [
        "profit",
        "cost",
        "expense",
        "tax",
        "discount",
        "margin",
    ]

    positive_terms = [
        "sales",
        "sale",
        "revenue",
        "turnover",
        "ordervalue",
        "transactionvalue",
    ]

    for term in negative_terms:
        if _normalize_column_name(term) in name:
            return False

    for term in positive_terms:
        if _normalize_column_name(term) in name:
            return True

    return False


# ============================================================
# FAST QUESTION PLANNER
# ============================================================

def fast_plan_question(question, profile):
    """
    Handle common/simple questions without calling Ollama.

    Returns:
        dict -> analysis plan
        None -> let Ollama handle the question
    """

    if not question:
        return None

    q = question.lower().strip()

    # --------------------------------------------------------
    # Find common columns
    # --------------------------------------------------------

    sales_column = _find_column(
        profile,
        [
            "sales",
            "sale",
            "revenue",
            "total_sales",
            "sales_amount",
            "sales_value",
            "revenue_amount",
            "total_revenue",
            "turnover",
            "order_value",
            "transaction_value",
            "amount",
            "income",
        ],
        category="numerical"
    )

    # Prevent generic monetary columns such as Profit, Cost,
    # Tax, Discount, etc. from being treated as Sales when a
    # stronger sales/revenue candidate exists.
    if sales_column and not _is_likely_sales_column(sales_column):

        sales_candidates = []

        for column, details in profile.get(
            "column_details",
            {}
        ).items():

            if details.get("category") != "numerical":
                continue

            if _is_likely_sales_column(column):
                sales_candidates.append(column)

        if sales_candidates:
            sales_column = _find_column(
                profile,
                [
                    "sales",
                    "sale",
                    "revenue",
                    "total_sales",
                    "sales_amount",
                    "sales_value",
                    "revenue_amount",
                    "total_revenue",
                    "turnover",
                    "order_value",
                    "transaction_value",
                ],
                category="numerical"
            )

    quantity_column = _find_numerical_column(
        profile,
        [
            "quantity",
            "qty",
            "quantityordered",
            "quantity_ordered",
            "units",
            "units_sold",
        ]
    )

    # ========================================================
    # COMMON GROUP/CATEGORY COLUMN
    # ========================================================

    group_column = _find_categorical_column(
        profile,
        [
            "country",
            "region",
            "market",
            "category",
            "product",
            "productline",
            "department",
            "segment",
            "customer",
        ]
    )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    if sales_column and any(
        phrase in q
        for phrase in [
            "total sales",
            "total revenue",
            "overall sales",
            "overall revenue",
            "sales in total",
            "revenue in total",
            "how much did we make",
            "how much money did we make",
        ]
    ):

        return {
            "operation": "total",
            "column": sales_column,
        }

    # --------------------------------------------------------
    # AVERAGE
    # --------------------------------------------------------

    if sales_column and any(
        phrase in q
        for phrase in [
            "average sales",
            "average sale",
            "mean sales",
            "mean sale",
            "average revenue",
            "mean revenue",
        ]
    ):

        return {
            "operation": "average",
            "column": sales_column,
        }

    # --------------------------------------------------------
    # HIGHEST / LOWEST SALES BY CATEGORY
    #
    # Example:
    # "Which country has the highest sales?"
    #
    # This is TOP_N, NOT group_max.
    # --------------------------------------------------------

    if sales_column and group_column:

        if any(
            phrase in q
            for phrase in [
                "highest sales",
                "largest sales",
                "most sales",
                "best sales",
                "highest revenue",
                "largest revenue",
                "most revenue",
                "best revenue",
            ]
        ):

            return {
                "operation": "top_n",
                "group_column": group_column,
                "value_column": sales_column,
                "n": 1,
            }

        if any(
            phrase in q
            for phrase in [
                "lowest sales",
                "smallest sales",
                "least sales",
                "lowest revenue",
                "smallest revenue",
                "least revenue",
            ]
        ):

            return {
                "operation": "bottom_n",
                "group_column": group_column,
                "value_column": sales_column,
                "n": 1,
            }

    # --------------------------------------------------------
    # MAXIMUM SINGLE SALES VALUE
    # --------------------------------------------------------

    if sales_column and any(
        phrase in q
        for phrase in [
            "highest sales value",
            "largest sales value",
            "maximum sales",
            "maximum sale",
            "highest sale value",
            "largest sale value",
        ]
    ):

        return {
            "operation": "maximum",
            "column": sales_column,
        }

    # --------------------------------------------------------
    # MINIMUM SINGLE SALES VALUE
    # --------------------------------------------------------

    if sales_column and any(
        phrase in q
        for phrase in [
            "lowest sales value",
            "smallest sales value",
            "minimum sales",
            "minimum sale",
            "lowest sale value",
            "smallest sale value",
        ]
    ):

        return {
            "operation": "minimum",
            "column": sales_column,
        }

    # --------------------------------------------------------
    # TOP N
    # --------------------------------------------------------

    if sales_column and group_column:

        top_match = re.search(
            r"\btop\s+(\d+)\b",
            q
        )

        if top_match and (
            "sales" in q
            or "revenue" in q
        ):

            n = int(
                top_match.group(1)
            )

            return {
                "operation": "top_n",
                "group_column": group_column,
                "value_column": sales_column,
                "n": n,
            }

        bottom_match = re.search(
            r"\bbottom\s+(\d+)\b",
            q
        )

        if bottom_match and (
            "sales" in q
            or "revenue" in q
        ):

            n = int(
                bottom_match.group(1)
            )

            return {
                "operation": "bottom_n",
                "group_column": group_column,
                "value_column": sales_column,
                "n": n,
            }

    # --------------------------------------------------------
    # COUNT BY CATEGORY
    # --------------------------------------------------------

    if any(
        phrase in q
        for phrase in [
            "how many orders",
            "number of orders",
            "orders by",
            "orders for each",
            "how many records",
            "number of records",
            "how many entries",
            "number of entries",
            "how many items",
        ]
    ):

        if group_column:

            return {
                "operation": "group_count",
                "group_column": group_column,
            }

    # --------------------------------------------------------
    # SALES BY REGION / CATEGORY
    # --------------------------------------------------------

    if sales_column and any(
        phrase in q
        for phrase in [
            "sales by region",
            "sales by market",
            "sales by category",
            "sales by country",
            "sales by product",
            "sales by productline",
            "sales by department",
            "sales by segment",
            "sales for each region",
            "sales for each market",
            "sales for each category",
            "sales for each country",
            "sales for each product",
        ]
    ):

        group_column = _find_categorical_column(
            profile,
            [
                "region",
                "market",
                "category",
                "country",
                "product",
                "productline",
                "department",
                "segment",
            ]
        )

        if group_column:

            return {
                "operation": "group_sum",
                "group_column": group_column,
                "value_column": sales_column,
            }

    # --------------------------------------------------------
    # SALES / REVENUE OVER TIME
    # --------------------------------------------------------

    if sales_column:

        temporal_phrases = [
            "sales over time", "sales over date", "sales over order date",
            "sales by date", "sales by order date", "sales by month",
            "sales by year", "sales by day", "sales by week", "sales by quarter",
            "monthly sales", "daily sales", "weekly sales", "yearly sales",
            "annual sales", "quarterly sales", "sales trend", "sales trends",
            "sales over the months", "sales over the years", "sales over the days",
            "sales over the weeks", "sales over the quarters",
            "sales month wise", "sales year wise", "sales day wise",
            "revenue over time", "revenue over date", "revenue over order date",
            "revenue by date", "revenue by order date", "revenue by month",
            "revenue by year", "revenue by day", "revenue by week", "revenue by quarter",
            "monthly revenue", "daily revenue", "weekly revenue", "yearly revenue",
            "annual revenue", "quarterly revenue", "revenue trend", "revenue trends",
            "revenue over the months", "revenue over the years", "revenue over the days",
            "revenue over the weeks", "revenue over the quarters",
            "revenue month wise", "revenue year wise", "revenue day wise",
        ]

        if any(phrase in q for phrase in temporal_phrases):

            # Determine the requested granularity first, then
            # deterministically select the matching time dimension.
            # This prevents "yearly sales" from accidentally using
            # MONTH_ID.
            if any(phrase in q for phrase in [
                "daily", "by day", "by date", "over the days",
                "day wise", "day-wise", "daywise",
            ]):
                time_granularity = "day"

            elif any(phrase in q for phrase in [
                "weekly", "by week", "over the weeks",
                "week wise", "week-wise", "weekwise",
            ]):
                time_granularity = "week"

            elif any(phrase in q for phrase in [
                "monthly", "by month", "over the months",
                "month wise", "month-wise", "monthwise",
            ]):
                time_granularity = "month"

            elif any(phrase in q for phrase in [
                "quarterly", "by quarter", "over the quarters",
                "quarter wise", "quarter-wise", "quarterwise",
            ]):
                time_granularity = "quarter"

            elif any(phrase in q for phrase in [
                "yearly", "annual", "by year", "over the years",
                "year wise", "year-wise", "yearwise",
            ]):
                time_granularity = "year"

            else:
                time_granularity = "month"

            temporal_column = _find_time_group_column(
                profile,
                time_granularity
            )

            if temporal_column:
                return {
                    "operation": "group_sum",
                    "group_column": temporal_column,
                    "value_column": sales_column,
                    "time_granularity": time_granularity,
                }

    # --------------------------------------------------------
    # CORRELATION
    # --------------------------------------------------------

    if sales_column and quantity_column and any(
        phrase in q
        for phrase in [
            "related to sales",
            "correlated with sales",
            "relationship between",
            "relation between",
        ]
    ):

        if (
            "quantity" in q
            or "qty" in q
            or "units" in q
            or "quantityordered" in q
        ):

            return {
                "operation": "correlation",
                "column1": quantity_column,
                "column2": sales_column,
            }

    # --------------------------------------------------------
    # No simple rule matched
    # --------------------------------------------------------

    return None


# ============================================================
# QUESTION PLANNER
# ============================================================

def plan_question(question, profile):
    """
    Convert a natural-language question into a structured
    analysis plan using the local Ollama LLM when necessary.
    """

    fast_plan = fast_plan_question(
        question,
        profile
    )

    if fast_plan:

        return validate_plan(
            fast_plan,
            profile
        )

    # --------------------------------------------------------
    # Prepare compact dataset information
    # --------------------------------------------------------

    columns = profile.get(
        "column_details",
        {}
    )

    print(
        "\n========== DEBUG PROFILE COLUMNS =========="
    )

    print(
        "Profile keys:",
        profile.keys()
    )

    print(
        "Column details:",
        list(columns.keys())
    )

    print(
        "===========================================\n"
    )

    compact_columns = {}

    for name, details in columns.items():

        compact_columns[name] = {
            "category": details.get("category"),
            "data_type": details.get("data_type"),
        }

    # --------------------------------------------------------
    # Planner prompt
    # --------------------------------------------------------

    prompt = f"""
You are an AI Data Analyst planner.

Your job is to understand a user's natural-language
question and convert it into ONE structured JSON
analysis plan.

You are NOT calculating the answer.

You are ONLY deciding what Python/Pandas operation
is required.

DATASET COLUMNS:

{json.dumps(compact_columns, indent=2)}


SUPPORTED OPERATIONS:

total
- Use when the user asks for a total, sum, overall amount,
  overall revenue, or how much was generated in total.

average
- Use for average, mean, typical, or usual value.

minimum
- Use for minimum, smallest, lowest, or least value
  of ONE numerical column.

maximum
- Use for maximum, largest, highest, or greatest value
  of ONE numerical column.

count
- Use when asking for the number of rows, records,
  entries, or observations in the dataset.

unique_count
- Use for unique, distinct, or different values
  in one column.

missing_count
- Use for missing, null, blank, or empty values
  in one column.

group_sum
- Use when asking for totals/sums by category.
- Also use when asking which category/region/market
  performed best when "performance" refers to total
  sales or revenue.

group_average
- Use when asking for averages by category.

group_count
- Use when asking how many records/orders/items
  belong to each category.

group_max
- Use when asking for the highest/largest value
  WITHIN EACH category.

group_min
- Use when asking for the lowest/smallest value
  WITHIN EACH category.

top_n
- Use for "top N", "best N", "highest N", or
  "leading N" categories.
- Also use when asking which category has the
  highest total sales/revenue.
- For a single highest category, use n = 1.

bottom_n
- Use for "bottom N", "worst N", "lowest N", or
  "weakest N" categories.
- Also use when asking which category has the
  lowest total sales/revenue.
- For a single lowest category, use n = 1.

correlation
- Use when asking whether two numerical columns
  are related, correlated, or associated.

describe
- Use for statistics, statistical summary,
  descriptive statistics, summary statistics,
  distribution summary, or "describe this column".

group_percentage
- Use for percentage contribution, percentage share,
  percentage of total, or contribution by category.

unsupported
- Use only when the dataset cannot answer the question.


IMPORTANT SEMANTIC RULES:

1. "largest sales value"
   -> maximum

2. "highest sales value"
   -> maximum

3. "smallest sales value"
   -> minimum

4. "lowest sales value"
   -> minimum

5. "statistics for sales"
   -> describe

6. "statistical summary of sales"
   -> describe

7. "which region performed the best?"
   -> group_sum
   IF the dataset contains a sales/revenue numerical
   column and a categorical region/market column.

8. "which region has the highest sales?"
   -> top_n with n = 1
   -> group_column = Region
   -> value_column = Sales

9. "which region has the lowest sales?"
   -> bottom_n with n = 1
   -> group_column = Region
   -> value_column = Sales

10. "top 3 regions by sales"
    -> top_n with n = 3

11. "bottom 2 regions by sales"
    -> bottom_n with n = 2

12. "percentage of sales from each region"
    -> group_percentage

13. "how many orders came from each region?"
    -> group_count

14. "how many different regions?"
    -> unique_count

15. "how much money did we make overall?"
    -> total

16. "show sales over order date"
    -> group_sum
    -> group_column = the dataset's date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "month" by default

17. "show sales by month"
    -> group_sum
    -> group_column = MONTH_ID when that time ID exists;
       otherwise use the real date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "month"

18. "show sales by day"
    -> group_sum
    -> group_column = the dataset's date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "day"

19. "show sales by week"
    -> group_sum
    -> group_column = the dataset's date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "week"

20. "show sales by quarter"
    -> group_sum
    -> group_column = QTR_ID when that time ID exists;
       otherwise use the real date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "quarter"

21. "show sales by year"
    -> group_sum
    -> group_column = YEAR_ID when that time ID exists;
       otherwise use the real date/order-date column
    -> value_column = the dataset's sales/revenue column
    -> time_granularity = "year"


COLUMN RULES:

- Use ONLY columns that exist in DATASET COLUMNS.
- Use the EXACT column names.
- Never invent column names.
- Numerical operations require numerical columns.
- A group column should normally be categorical,
  temporal, or geographic.
- Temporal/date columns are valid group columns.
- If the user asks for a numerical value over time,
  use the temporal column as group_column and the
  numerical column as value_column.
- Questions containing phrases such as "over time",
  "over date", "by date", "by month", "by year",
  "by day", "by week", "by quarter", "monthly", "daily",
  "weekly", "quarterly", or "yearly" should normally
  use a group operation with the temporal column.
- For temporal questions, include a "time_granularity" field.
- Valid time_granularity values are "day", "week", "month",
  "quarter", and "year".
- When the dataset contains derived time ID columns, use the
  matching one:
      year    -> YEAR_ID
      quarter -> QTR_ID
      month   -> MONTH_ID
- YEAR_ID, QTR_ID, and MONTH_ID are valid time dimensions even
  if the dataset profiler classifies them as numerical.
- Do NOT use MONTH_ID for a yearly question.
- Do NOT use YEAR_ID for a monthly question.
- Do NOT use QTR_ID for a yearly or monthly question.
- For day/week, prefer the real date/order-date column.
- When the dataset contains derived time ID columns, use the
  matching one:
      year    -> YEAR_ID
      quarter -> QTR_ID
      month   -> MONTH_ID
- YEAR_ID, QTR_ID, and MONTH_ID are valid time dimensions even
  if the dataset profiler classifies them as numerical.
- Do NOT use MONTH_ID for a yearly question.
- Do NOT use YEAR_ID for a monthly question.
- Do NOT use QTR_ID for a yearly or monthly question.
- For day/week, prefer the real date/order-date column.
- "daily" means "day".
- "weekly" means "week".
- "monthly" means "month".
- "quarterly" means "quarter".
- "yearly" or "annual" means "year".
- If the user says "over time" or "over date" without a
  specific granularity, use "month" by default.
- For example:

  "Show sales over date."

  -> group_sum with group_column = Date
     and value_column = Sales.

- Never use the group column as the value column
  unless it is actually numerical.
- If the question asks for statistics about one
  numerical column, use describe.
- If a question asks for a maximum/minimum of ONE
  numerical column, do NOT use group_max/group_min.
- group_max/group_min require BOTH group_column
  and value_column.
- If a question asks which category has the highest
  total sales/revenue, use top_n with n = 1.
- If a question asks which category has the lowest
  total sales/revenue, use bottom_n with n = 1.


OUTPUT RULES:

- Return ONLY valid JSON.
- Do NOT use Markdown.
- Do NOT use code fences.
- Do NOT explain the answer.
- Do NOT calculate the answer.
- Do NOT include extra fields.
- The operation must be one of:

{json.dumps(SUPPORTED_OPERATIONS)}


VALID EXAMPLES:

Question:
What is the total sales?

JSON:
{{"operation":"total","column":"Sales"}}


Question:
What is the largest sales value?

JSON:
{{"operation":"maximum","column":"Sales"}}


Question:
What is the smallest sales value?

JSON:
{{"operation":"minimum","column":"Sales"}}


Question:
Give me statistics for sales.

JSON:
{{"operation":"describe","column":"Sales"}}


Question:
How many different regions do we have?

JSON:
{{"operation":"unique_count","column":"Region"}}


Question:
How many orders came from each region?

JSON:
{{"operation":"group_count","group_column":"Region"}}


Question:
Show sales by region.

JSON:
{{"operation":"group_sum","group_column":"Region","value_column":"Sales"}}


Question:
Which region has the highest sales?

JSON:
{{"operation":"top_n","group_column":"Region","value_column":"Sales","n":1}}


Question:
Which region has the lowest sales?

JSON:
{{"operation":"bottom_n","group_column":"Region","value_column":"Sales","n":1}}


Question:
Show me the top 3 regions by sales.

JSON:
{{"operation":"top_n","group_column":"Region","value_column":"Sales","n":3}}


Question:
Show me the bottom 2 regions by sales.

JSON:
{{"operation":"bottom_n","group_column":"Region","value_column":"Sales","n":2}}


Question:
What percentage of sales comes from each region?

JSON:
{{"operation":"group_percentage","group_column":"Region","value_column":"Sales"}}


Question:
Is quantity related to sales?

JSON:
{{"operation":"correlation","column1":"Quantity","column2":"Sales"}}


Question:
How much money did we make overall?

JSON:
{{"operation":"total","column":"Sales"}}


Question:
Which market performed the best?

JSON:
{{"operation":"group_sum","group_column":"Market","value_column":"Sales"}}


Question:
Show sales over date.

JSON:
{{"operation":"group_sum","group_column":"MONTH_ID","value_column":"Sales","time_granularity":"month"}}


Question:
Show sales by month.

JSON:
{{"operation":"group_sum","group_column":"Date","value_column":"Sales","time_granularity":"month"}}


Question:
Show sales by day.

JSON:
{{"operation":"group_sum","group_column":"ORDERDATE","value_column":"Sales","time_granularity":"day"}}


Question:
Show sales by week.

JSON:
{{"operation":"group_sum","group_column":"ORDERDATE","value_column":"Sales","time_granularity":"week"}}


Question:
Show sales by quarter.

JSON:
{{"operation":"group_sum","group_column":"QTR_ID","value_column":"Sales","time_granularity":"quarter"}}


Question:
Show sales by year.

JSON:
{{"operation":"group_sum","group_column":"YEAR_ID","value_column":"Sales","time_granularity":"year"}}


Question:
Show sales over order date.

JSON:
{{"operation":"group_sum","group_column":"ORDERDATE","value_column":"SALES","time_granularity":"month"}}


USER QUESTION:

{question}
"""

    # --------------------------------------------------------
    # Call Ollama
    # --------------------------------------------------------

    try:

        response = generate_response(
            prompt
        )

        cleaned = clean_response(
            response
        )

        plan = json.loads(
            cleaned
        )

        return validate_plan(
            plan,
            profile
        )

    except json.JSONDecodeError:

        return {
            "operation": "unsupported",
            "reason": (
                "The local LLM returned invalid JSON."
            )
        }

    except TimeoutError:

        return {
            "operation": "unsupported",
            "reason": (
                "Ollama took too long to respond."
            )
        }

    except Exception as error:

        return {
            "operation": "unsupported",
            "reason": str(error)
        }