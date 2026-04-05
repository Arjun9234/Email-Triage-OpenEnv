"""Compatibility wrapper for local server folder execution.

Preferred entrypoint is project-root inference.py.
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    runpy.run_path(str(project_root / "inference.py"), run_name="__main__")
