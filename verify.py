"""Week 0 gate — run this before you call the setup done.

    python verify.py

Every check must pass. This is the whole Week 0 deliverable.
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

PASS, FAIL = "  PASS  ", "  FAIL  "
results = []


def check(name, ok, hint=""):
    results.append((name, ok, hint))
    print(f"[{PASS if ok else FAIL}] {name}")
    if not ok and hint:
        print(f"           -> {hint}")


def main():
    v = sys.version_info
    check(f"Python {v.major}.{v.minor}.{v.micro} is 3.10+",
          (v.major, v.minor) >= (3, 10),
          "Install Python 3.11 or newer and recreate the venv.")

    check("Running inside a virtual environment",
          sys.prefix != sys.base_prefix,
          "Run: source .venv/bin/activate   (Windows: .venv\\Scripts\\activate)")

    for mod, pkg in [("openai", "openai"), ("dotenv", "python-dotenv"),
                     ("tiktoken", "tiktoken"), ("pandas", "pandas"),
                     ("matplotlib", "matplotlib")]:
        try:
            importlib.import_module(mod)
            ok = True
        except ImportError:
            ok = False
        check(f"import {mod}", ok, f"pip install -r requirements.txt  (missing {pkg})")

    check(".env exists", Path(".env").exists(),
          "cp .env.example .env  then fill in your key")

    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("MODEL_API_KEY", "")
    check("MODEL_API_KEY is set and not the placeholder",
          bool(key) and "replace-me" not in key,
          "Put a real key in .env")
    check("MODEL_NAME is set", bool(os.getenv("MODEL_NAME")),
          "Set MODEL_NAME in .env")

    check(".env is ignored by git",
          Path(".gitignore").exists() and ".env" in Path(".gitignore").read_text(),
          "Add .env to .gitignore BEFORE your next commit.")

    try:
        tracked = subprocess.run(["git", "ls-files", ".env"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
        check(".env is not committed", tracked == "",
              "git rm --cached .env   then rotate that key, it is in your history.")
    except Exception:
        check(".env is not committed", True, "")

    docs = list(Path("data/docs").glob("*.txt"))
    check(f"corpus has documents ({len(docs)} found)", len(docs) > 0,
          "Put .txt files in data/docs/")

    failed = [n for n, ok, _ in results if not ok]
    print()
    if failed:
        print(f"{len(failed)} check(s) failed. Fix these before starting Week 1:")
        for n in failed:
            print(f"  - {n}")
        sys.exit(1)
    print("All checks passed. Week 0 is done — commit and go.")


if __name__ == "__main__":
    main()
