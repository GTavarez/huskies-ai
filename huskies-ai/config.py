"""Single source of truth for model configuration.

Every script that touches a model imports from here, and every result file
records CONFIG. A baseline produced under an unrecorded configuration cannot
be compared with anything later — that is the whole reason this file exists.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "base_url": os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1"),
    "model": os.getenv("MODEL_NAME", "gpt-4o-mini"),
    "temperature": 0.0,
    "seed": 7,
    "max_tokens": 400,
}


def client():
    """An OpenAI-compatible client. Works with hosted providers, Ollama, LM Studio."""
    from openai import OpenAI
    key = os.getenv("MODEL_API_KEY")
    if not key:
        raise SystemExit(
            "MODEL_API_KEY is not set.\n"
            "  1. cp .env.example .env\n"
            "  2. put your key in .env\n"
            "  3. run again"
        )
    return OpenAI(base_url=CONFIG["base_url"], api_key=key)


def stamp():
    """Drop this into every result file you save."""
    return {k: v for k, v in CONFIG.items() if k != "seed"} | {"seed": CONFIG["seed"]}
