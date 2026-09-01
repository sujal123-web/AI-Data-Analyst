import pandas as pd
from pathlib import Path


def load_dataset(file_path):
    """
    Load a CSV or Excel dataset.

    Parameters:
        file_path (str): Path to the dataset.

    Returns:
        pandas.DataFrame: Loaded dataset.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        try:
         df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
         df = pd.read_csv(file_path, encoding="latin1")

    elif file_path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)

    else:
        raise ValueError(
            "Unsupported file format. Please use CSV or Excel."
        )

    return df