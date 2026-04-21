"""Standalone Dash UI for the research pipeline (no FastAPI required).

Usage:
  pip install dash dash-bootstrap-components pydantic scipy statsmodels
  python run_research.py

Full stack (FastAPI + Dash mounted at /dash):
  pip install fastapi uvicorn
  uvicorn api.main:app --reload --port 8000
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> None:
    from dash_app.app import create_dash_app

    app = create_dash_app(route_prefix="/")
    app.run(debug=False, port=8050)


if __name__ == "__main__":
    main()
