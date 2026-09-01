from pathlib import Path
from uuid import UUID, uuid4

import pandas as pd

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.data_engine.data_loader import load_dataset
from backend.data_engine.data_profiler import profile_dataset
from backend.question_pipeline import process_question


# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Data Analyst",
    description="AI-powered data analysis and visualization API",
    version="1.0.0"
)
# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# UPLOAD DIRECTORY
# ============================================================

UPLOAD_DIR = Path("data/uploads")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# REQUEST MODEL
# ============================================================

class QuestionRequest(BaseModel):
    """
    Request body for asking a question about
    an uploaded dataset.
    """

    dataset_id: str
    question: str


# ============================================================
# HELPER — FIND DATASET
# ============================================================

def find_dataset_file(dataset_id):
    """
    Find an uploaded dataset using its dataset ID.
    """

    # --------------------------------------------------------
    # Validate UUID
    # --------------------------------------------------------

    try:

        UUID(dataset_id)

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid dataset_id."
        )

    # --------------------------------------------------------
    # Search supported extensions
    # --------------------------------------------------------

    supported_extensions = [
        ".csv",
        ".xlsx",
        ".xls"
    ]

    for extension in supported_extensions:

        file_path = (
            UPLOAD_DIR /
            f"{dataset_id}{extension}"
        )

        if file_path.exists():

            return file_path

    # --------------------------------------------------------
    # Dataset not found
    # --------------------------------------------------------

    raise HTTPException(
        status_code=404,
        detail="Dataset not found."
    )


# ============================================================
# HELPER — SERIALIZE RESULT
# ============================================================

def serialize_result(result):
    """
    Convert Pandas results into JSON-compatible data
    for the API response.
    """

    # --------------------------------------------------------
    # Pandas Series
    # --------------------------------------------------------

    if isinstance(result, pd.Series):

        return {
            str(key): value.item()
            if hasattr(value, "item")
            else value
            for key, value in result.to_dict().items()
        }

    # --------------------------------------------------------
    # Pandas DataFrame
    # --------------------------------------------------------

    if isinstance(result, pd.DataFrame):

        return result.to_dict(
            orient="records"
        )

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(result, dict):

        serialized = {}

        for key, value in result.items():

            if hasattr(value, "item"):

                value = value.item()

            serialized[str(key)] = value

        return serialized

    # --------------------------------------------------------
    # NumPy / Pandas scalar
    # --------------------------------------------------------

    if hasattr(result, "item"):

        return result.item()

    # --------------------------------------------------------
    # Normal Python value
    # --------------------------------------------------------

    return result


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    """
    Check whether the API is running.
    """

    return {
        "status": "ok",
        "message": "AI Data Analyst API is running."
    }


# ============================================================
# UPLOAD DATASET
# ============================================================

@app.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...)
):
    """
    Upload a CSV or Excel dataset.

    The dataset is saved with a unique dataset ID
    and automatically profiled.
    """

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file was provided."
        )

    # --------------------------------------------------------
    # Get extension
    # --------------------------------------------------------

    file_extension = (
        Path(file.filename)
        .suffix
        .lower()
    )

    allowed_extensions = {
        ".csv",
        ".xlsx",
        ".xls"
    }

    if file_extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. "
                "Please upload a CSV or Excel file."
            )
        )

    # --------------------------------------------------------
    # Generate dataset ID
    # --------------------------------------------------------

    dataset_id = str(uuid4())

    file_path = (
        UPLOAD_DIR /
        f"{dataset_id}{file_extension}"
    )

    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------

    try:

        contents = await file.read()

        with open(
            file_path,
            "wb"
        ) as destination:

            destination.write(contents)

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not save uploaded file: {error}"
            )
        )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    try:

        dataframe = load_dataset(
            str(file_path)
        )

    except Exception as error:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not load dataset: {error}"
            )
        )

    # --------------------------------------------------------
    # Profile dataset
    # --------------------------------------------------------

    try:

        profile = profile_dataset(
            dataframe
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not profile dataset: {error}"
            )
        )

    # --------------------------------------------------------
    # Return upload information
    # --------------------------------------------------------

    return {
        "status": "success",
        "message": "Dataset uploaded successfully.",
        "dataset_id": dataset_id,
        "filename": file.filename,
        "rows": len(dataframe),
        "columns": len(dataframe.columns),
        "column_names": [
            str(column)
            for column in dataframe.columns
        ],
        "profile": profile
    }


# ============================================================
# ASK QUESTION
# ============================================================

@app.post("/ask")
def ask_question(
    request: QuestionRequest
):
    """
    Ask a natural-language question about
    an uploaded dataset.

    Complete flow:

        Dataset ID
             ↓
        Load Dataset
             ↓
        Profile Dataset
             ↓
        Question Planner
             ↓
        Analysis Executor
             ↓
        Visualization Planner
             ↓
        Visualization Engine
             ↓
        Insight Agent
             ↓
        Final Response
    """

    # --------------------------------------------------------
    # Validate question
    # --------------------------------------------------------

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # --------------------------------------------------------
    # Find uploaded dataset
    # --------------------------------------------------------

    file_path = find_dataset_file(
        request.dataset_id
    )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    try:

        dataframe = load_dataset(
            str(file_path)
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not load dataset: {error}"
            )
        )

    # --------------------------------------------------------
    # Profile dataset
    # --------------------------------------------------------

    try:

        profile = profile_dataset(
            dataframe
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not profile dataset: {error}"
            )
        )

    # --------------------------------------------------------
    # Process question
    # --------------------------------------------------------

    try:

        response = process_question(
            dataframe,
            profile,
            question
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Question processing failed: {error}"
            )
        )

    # --------------------------------------------------------
    # Convert result to JSON-compatible format
    # --------------------------------------------------------

    response["result"] = serialize_result(
        response.get("result")
    )

    # --------------------------------------------------------
    # Return complete response
    # --------------------------------------------------------

    return {
        "status": "success",
        "dataset_id": request.dataset_id,
        "question": response.get("question"),
        "plan": response.get("plan"),
        "result": response.get("result"),
        "answer": response.get("answer"),
        "visualization": response.get(
            "visualization"
        )
    }