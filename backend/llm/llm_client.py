import requests


OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL_NAME = "gemma2:2b"


def generate_response(prompt):
    """
    Generate a response from the local Ollama LLM.
    """

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Could not connect to Ollama. "
            "Make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Ollama took too long to respond."
        )

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            f"Ollama request failed: {error}"
        )

    data = response.json()

    generated_text = data.get("response", "")

    if not generated_text:

        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return generated_text.strip()