import re

import pandas as pd


# =========================================================
# CONSTANTS
# =========================================================

IDENTIFIER_KEYWORDS = [
    "id",
    "identifier",
    "uuid",
    "code",
]

GEOGRAPHIC_KEYWORDS = [
    "country",
    "state",
    "province",
    "city",
    "district",
    "location",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
    "zip",
    "zipcode",
    "postal",
    "pincode",
]

TEMPORAL_KEYWORDS = [
    "date",
    "time",
    "timestamp",
    "datetime",
    "year",
    "month",
    "day",
    "week",
    "quarter",
]

FINANCIAL_KEYWORDS = [
    "sales",
    "sale",
    "revenue",
    "income",
    "profit",
    "price",
    "amount",
    "cost",
    "expense",
    "salary",
    "wage",
    "turnover",
    "earnings",
    "payment",
    "value",
    "total",
    "subtotal",
    "discount",
    "tax",
    "margin",
]

PERCENTAGE_KEYWORDS = [
    "percent",
    "percentage",
    "pct",
    "rate",
    "ratio",
    "margin",
    "growth",
    "share",
]

MEASURE_KEYWORDS = [
    "sales",
    "revenue",
    "profit",
    "income",
    "price",
    "amount",
    "cost",
    "expense",
    "quantity",
    "count",
    "total",
    "value",
    "score",
    "rating",
    "salary",
    "wage",
    "balance",
    "payment",
    "discount",
    "tax",
]

DIMENSION_KEYWORDS = [
    "category",
    "type",
    "class",
    "segment",
    "department",
    "product",
    "customer",
    "country",
    "state",
    "city",
    "region",
    "territory",
    "status",
    "gender",
    "channel",
    "brand",
    "category",
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _normalized_name(column_name):
    """
    Normalize a column name for semantic detection.
    """

    name = str(column_name).strip().lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "_",
        name
    )

    name = re.sub(
        r"_+",
        "_",
        name
    )

    return name.strip("_")


def _contains_keyword(column_name, keywords):
    """
    Check whether a column name contains a semantic keyword.

    Matching is performed on word boundaries so that:

        order_date -> date
        customer_id -> id

    but unrelated strings are not accidentally matched.
    """

    name = _normalized_name(column_name)

    if not name:
        return False

    parts = set(name.split("_"))

    for keyword in keywords:

        keyword_normalized = _normalized_name(keyword)

        if keyword_normalized in parts:
            return True

    return False


def _safe_unique_ratio(series):
    """
    Calculate the percentage of unique non-null values.
    """

    non_null = series.dropna()

    if len(non_null) == 0:
        return 0.0

    return float(
        non_null.nunique() / len(non_null)
    )


def _safe_missing_ratio(series):
    """
    Calculate percentage of missing values.
    """

    if len(series) == 0:
        return 0.0

    return float(
        series.isna().mean()
    )


# =========================================================
# IDENTIFIER DETECTION
# =========================================================

def is_likely_identifier(column_name, series):
    """
    Determine whether a column is likely to be an identifier.

    Examples:

        customer_id
        order_id
        product_code
        transaction_number
        uuid
    """

    name = _normalized_name(column_name)

    # -----------------------------------------------------
    # Strong identifier keywords
    # -----------------------------------------------------

    if _contains_keyword(
        name,
        IDENTIFIER_KEYWORDS
    ):
        return True

    # -----------------------------------------------------
    # Common identifier suffixes
    # -----------------------------------------------------

    identifier_suffixes = [
        "_no",
        "_number",
        "_num",
        "_key",
        "_ref",
        "_reference",
    ]

    for suffix in identifier_suffixes:

        if name.endswith(suffix):
            return True

    # -----------------------------------------------------
    # Common exact names
    # -----------------------------------------------------

    if name in [
        "no",
        "number",
        "key",
        "reference",
        "ref",
        "uuid",
    ]:
        return True

    # -----------------------------------------------------
    # Very high uniqueness can indicate an ID
    #
    # But do not classify every high-cardinality numerical
    # column as an identifier.
    # -----------------------------------------------------

    unique_ratio = _safe_unique_ratio(series)

    if (
        unique_ratio >= 0.98
        and len(series) >= 20
        and not pd.api.types.is_bool_dtype(series)
    ):

        # Strings with almost completely unique values
        # are especially likely to be identifiers.
        if pd.api.types.is_object_dtype(series):
            return True

    return False


# =========================================================
# GEOGRAPHIC DETECTION
# =========================================================

def is_likely_geographic(column_name, series):
    """
    Determine whether a column is likely geographic.

    Examples:

        country
        state
        city
        region
        latitude
        longitude
        postal_code
    """

    name = _normalized_name(column_name)

    if _contains_keyword(
        name,
        GEOGRAPHIC_KEYWORDS
    ):
        return True

    return False


# =========================================================
# TEMPORAL DETECTION
# =========================================================

def is_likely_temporal(series, column_name):
    """
    Determine whether a column contains date/time information.
    """

    name = _normalized_name(column_name)

    # -----------------------------------------------------
    # Strong temporal column names
    # -----------------------------------------------------

    if _contains_keyword(
        name,
        TEMPORAL_KEYWORDS
    ):
        return True

    # -----------------------------------------------------
    # Already datetime
    # -----------------------------------------------------

    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    # -----------------------------------------------------
    # Numeric year detection
    # -----------------------------------------------------

    if pd.api.types.is_numeric_dtype(series):

        non_null = series.dropna()

        if len(non_null) > 0:

            # A column containing values such as
            # 2020, 2021, 2022 is likely a year.
            if (
                non_null.between(
                    1900,
                    2100
                ).mean() >= 0.95
                and (
                    name == "year"
                    or "year" in name.split("_")
                )
            ):
                return True

    # -----------------------------------------------------
    # Object/string date detection
    # -----------------------------------------------------

    if (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):

        non_empty = series.dropna()

        if len(non_empty) == 0:
            return False

        # Do not attempt extremely large columns completely.
        sample = non_empty.head(1000)

        try:

            converted = pd.to_datetime(
                sample,
                errors="coerce",
                format="mixed"
            )

            valid_ratio = converted.notna().mean()

            if valid_ratio >= 0.80:
                return True

        except Exception:
            return False

    return False


# =========================================================
# BOOLEAN DETECTION
# =========================================================

def is_likely_boolean(series):
    """
    Detect boolean columns, including common textual
    representations such as yes/no and true/false.
    """

    if pd.api.types.is_bool_dtype(series):
        return True

    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return False

    non_null = series.dropna()

    if len(non_null) == 0:
        return False

    unique_values = set(
        str(value).strip().lower()
        for value in non_null.unique()
    )

    boolean_sets = [
        {"true", "false"},
        {"yes", "no"},
        {"y", "n"},
        {"1", "0"},
    ]

    return any(
        unique_values.issubset(values)
        for values in boolean_sets
    )


# =========================================================
# PERCENTAGE DETECTION
# =========================================================

def is_likely_percentage(series, column_name):
    """
    Determine whether a numerical column likely represents
    a percentage/rate.
    """

    if not pd.api.types.is_numeric_dtype(series):
        return False

    name = _normalized_name(column_name)

    if _contains_keyword(
        name,
        PERCENTAGE_KEYWORDS
    ):
        return True

    non_null = series.dropna()

    if len(non_null) == 0:
        return False

    # Values between 0 and 1 can represent ratios.
    ratio_like = (
        non_null.between(0, 1).mean()
    )

    # Values between 0 and 100 can represent percentages.
    percentage_like = (
        non_null.between(0, 100).mean()
    )

    if ratio_like >= 0.95:
        return True

    if percentage_like >= 0.95 and (
        "rate" in name
        or "percent" in name
        or "pct" in name
    ):
        return True

    return False


# =========================================================
# FINANCIAL DETECTION
# =========================================================

def is_likely_financial(column_name):
    """
    Determine whether a column name suggests a financial
    or monetary measure.
    """

    return _contains_keyword(
        column_name,
        FINANCIAL_KEYWORDS
    )


# =========================================================
# MEASURE DETECTION
# =========================================================

def is_likely_measure(series, column_name, category):
    """
    Determine whether a column is likely to be an analytical
    measure that can be aggregated using sum/mean/min/max.
    """

    if category != "numerical":
        return False

    if is_likely_identifier(
        column_name,
        series
    ):
        return False

    name = _normalized_name(column_name)

    if _contains_keyword(
        name,
        MEASURE_KEYWORDS
    ):
        return True

    # Generic numerical columns are potential measures.
    return True


# =========================================================
# DIMENSION DETECTION
# =========================================================

def is_likely_dimension(series, column_name, category):
    """
    Determine whether a column is likely to be a dimension
    used for grouping/filtering.
    """

    if category in [
        "categorical",
        "geographic",
        "temporal",
        "boolean",
    ]:
        return True

    name = _normalized_name(column_name)

    if _contains_keyword(
        name,
        DIMENSION_KEYWORDS
    ):
        return True

    return False


# =========================================================
# COLUMN CATEGORY
# =========================================================

def detect_column_category(series, column_name):
    """
    Dynamically classify a column into a broad data category.
    """

    # -----------------------------------------------------
    # Temporal first
    # -----------------------------------------------------

    if is_likely_temporal(
        series,
        column_name
    ):
        return "temporal"

    # -----------------------------------------------------
    # Geographic
    # -----------------------------------------------------

    if is_likely_geographic(
        column_name,
        series
    ):
        return "geographic"

    # -----------------------------------------------------
    # Identifier
    # -----------------------------------------------------

    if is_likely_identifier(
        column_name,
        series
    ):
        return "identifier"

    # -----------------------------------------------------
    # Boolean
    # -----------------------------------------------------

    if is_likely_boolean(series):
        return "boolean"

    # -----------------------------------------------------
    # Numerical
    # -----------------------------------------------------

    if pd.api.types.is_numeric_dtype(series):
        return "numerical"

    # -----------------------------------------------------
    # Categorical
    # -----------------------------------------------------

    return "categorical"


# =========================================================
# COLUMN PROFILE
# =========================================================

def profile_column(series, column_name):
    """
    Create detailed metadata for a single column.
    """

    category = detect_column_category(
        series,
        column_name
    )

    missing_values = int(
        series.isna().sum()
    )

    unique_values = int(
        series.nunique(dropna=True)
    )

    unique_ratio = _safe_unique_ratio(
        series
    )

    missing_ratio = _safe_missing_ratio(
        series
    )

    percentage = is_likely_percentage(
        series,
        column_name
    )

    financial = is_likely_financial(
        column_name
    )

    measure = is_likely_measure(
        series,
        column_name,
        category
    )

    dimension = is_likely_dimension(
        series,
        column_name,
        category
    )

    # -----------------------------------------------------
    # Cardinality
    # -----------------------------------------------------

    if unique_ratio >= 0.95:
        cardinality = "high"

    elif unique_ratio <= 0.20:
        cardinality = "low"

    else:
        cardinality = "medium"

    # -----------------------------------------------------
    # Semantic type
    # -----------------------------------------------------

    if percentage:
        semantic_type = "percentage"

    elif financial and measure:
        semantic_type = "financial_measure"

    elif category == "temporal":
        semantic_type = "datetime"

    elif category == "geographic":
        semantic_type = "geographic"

    elif category == "identifier":
        semantic_type = "identifier"

    elif category == "numerical":
        semantic_type = "numeric_measure"

    elif category == "boolean":
        semantic_type = "boolean"

    else:
        semantic_type = "categorical_dimension"

    return {
        "data_type": str(series.dtype),

        "category": category,

        "semantic_type": semantic_type,

        "role": (
            "measure"
            if measure
            else "dimension"
            if dimension
            else "identifier"
        ),

        "is_numeric": bool(
            pd.api.types.is_numeric_dtype(series)
        ),

        "is_datetime": bool(
            is_likely_temporal(
                series,
                column_name
            )
        ),

        "is_identifier": bool(
            category == "identifier"
        ),

        "is_geographic": bool(
            category == "geographic"
        ),

        "is_percentage": bool(
            percentage
        ),

        "is_financial": bool(
            financial
        ),

        "is_measure": bool(
            measure
        ),

        "is_dimension": bool(
            dimension
        ),

        "missing_values": missing_values,

        "missing_percentage": round(
            missing_ratio * 100,
            2
        ),

        "unique_values": unique_values,

        "unique_percentage": round(
            unique_ratio * 100,
            2
        ),

        "cardinality": cardinality,
    }


# =========================================================
# DATASET PROFILER
# =========================================================

def profile_dataset(df):
    """
    Create a comprehensive dynamic profile of a Pandas
    DataFrame.

    The profiler does not assume any fixed dataset schema.
    """

    if not isinstance(
        df,
        pd.DataFrame
    ):
        raise TypeError(
            "profile_dataset expects a pandas DataFrame."
        )

    # -----------------------------------------------------
    # Basic dataset information
    # -----------------------------------------------------

    profile = {
        "rows": int(len(df)),

        # IMPORTANT:
        # Keep this as an integer because existing parts
        # of the application may depend on it.
        "columns": int(len(df.columns)),

        # Explicit column names for downstream systems.
        "column_names": [
            str(column)
            for column in df.columns
        ],

        "column_details": {},

        "column_roles": {
            "measures": [],
            "dimensions": [],
            "temporal": [],
            "geographic": [],
            "identifiers": [],
            "categorical": [],
            "numerical": [],
            "boolean": [],
        },
    }

    # =====================================================
    # PROFILE EACH COLUMN
    # =====================================================

    for column in df.columns:

        column_data = df[column]

        details = profile_column(
            column_data,
            column
        )

        profile["column_details"][
            column
        ] = details

        category = details["category"]

        # -------------------------------------------------
        # Store column by category
        # -------------------------------------------------

        if category in profile["column_roles"]:
            profile["column_roles"][
                category
            ].append(column)

        # -------------------------------------------------
        # Store measures
        # -------------------------------------------------

        if details["is_measure"]:

            profile["column_roles"][
                "measures"
            ].append(column)

        # -------------------------------------------------
        # Store dimensions
        # -------------------------------------------------

        if details["is_dimension"]:

            profile["column_roles"][
                "dimensions"
            ].append(column)

    # =====================================================
    # DATASET-LEVEL SUMMARY
    # =====================================================

    profile["summary"] = {

        "total_rows": int(
            len(df)
        ),

        "total_columns": int(
            len(df.columns)
        ),

        "numeric_columns": len(
            profile["column_roles"][
                "numerical"
            ]
        ),

        "categorical_columns": len(
            profile["column_roles"][
                "categorical"
            ]
        ),

        "temporal_columns": len(
            profile["column_roles"][
                "temporal"
            ]
        ),

        "geographic_columns": len(
            profile["column_roles"][
                "geographic"
            ]
        ),

        "identifier_columns": len(
            profile["column_roles"][
                "identifiers"
            ]
        ),

        "measure_columns": len(
            profile["column_roles"][
                "measures"
            ]
        ),

        "dimension_columns": len(
            profile["column_roles"][
                "dimensions"
            ]
        ),

        "boolean_columns": len(
            profile["column_roles"][
                "boolean"
            ]
        ),
    }

    return profile