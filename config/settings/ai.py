from pathlib import Path

from decouple import AutoConfig

BASE_DIR = Path(__file__).resolve().parent.parent.parent

config = AutoConfig(search_path=BASE_DIR)


GEMINI_API_KEY: str = config("GEMINI_API_KEY", default="")
GEMINI_MODEL: str = config("GEMINI_MODEL", default="gemini-3.8-flash")
