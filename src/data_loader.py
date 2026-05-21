import re
from pathlib import Path
import pandas as pd
import ftfy

VALID_CLASSES = {"F", "A", "L", "LF", "MN", "O",
                 "PE", "SC", "SE", "US", "FT", "PO"}

ROW_PATTERN = re.compile(
    r"^(\d+)\s*,\s*'(.*)'\s*,?\s*(F|A|L|LF|MN|O|PE|SC|SE|US|FT|PO)\s*$"
)


def clean_text(raw: str) -> str:
    text = raw.replace("\\92", "'").replace("\\93", '"').replace("\\94", '"')
    text = ftfy.fix_text(text)
    text = " ".join(text.split())
    return text


def parse_arff(arff_path: Path) -> pd.DataFrame:
    rows = []
    skipped = []
    in_data_section = False

    with open(arff_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()

            if not line or line.startswith("%"):
                continue

            if not in_data_section:
                if line.upper().startswith("@DATA"):
                    in_data_section = True
                continue

            match = ROW_PATTERN.match(line)
            if not match:
                skipped.append((line_num, line[:80]))
                continue

            project_id, raw_text, label = match.groups()

            if label not in VALID_CLASSES:
                skipped.append((line_num, line[:80]))
                continue

            rows.append({
                "project_id": int(project_id),
                "text": clean_text(raw_text),
                "class": label,
            })

    df = pd.DataFrame(rows)

    print(f"Successfully parsed: {len(df)} requirements")
    print(f"Skipped (invalid format): {len(skipped)}")
    if skipped:
        print("\nFirst 5 skipped lines:")
        for ln, snippet in skipped[:5]:
            print(f"  Line {ln}: {snippet}")

    return df


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    arff_path = project_root / "data" / "raw" / "Promise+.arff"
    output_path = project_root / "data" / "processed" / "promise_clean.csv"

    df = parse_arff(arff_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\nSaved in: {output_path}")
    print(f"\nClass distribution:")
    print(df["class"].value_counts())
    print(f"\nUnique projects: {df['project_id'].nunique()}")