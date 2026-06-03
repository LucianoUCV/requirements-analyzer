import json
from pathlib import Path

import pandas as pd

from .report import render_html


def load_input(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if p.suffix.lower() == ".csv":
        df = pd.read_csv(p)
        if "text" not in df.columns:
            raise ValueError(f"CSV must have a 'text' column; got columns: {list(df.columns)}")
        if "id" not in df.columns:
            df["id"] = range(len(df))
        if "project_id" not in df.columns:
            df["project_id"] = "default"
    elif p.suffix.lower() in (".txt", ""):
        lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        df = pd.DataFrame({"id": list(range(len(lines))), "text": lines, "project_id": "default"})
    else:
        raise ValueError(f"Unsupported input extension: {p.suffix}. Use .csv or .txt")

    return df


def save_output(report, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".json":
        p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    elif p.suffix.lower() == ".html":
        p.write_text(render_html(report), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output extension: {p.suffix}. Use .json or .html")
