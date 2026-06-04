from pathlib import Path

from requirements_analyzer import RequirementsAnalyzer, load_input, save_output


def ask(question, default=None):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        try:
            raw = input(f"{question}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(0)
        value = raw or default
        if value:
            return value
        print("  (required)")


def ask_choice(question, choices, default):
    label = "/".join(c.upper() if c == default else c for c in choices)
    while True:
        value = ask(f"{question} ({label})", default=default).lower()
        if value in choices:
            return value
        print(f"  pick one of: {', '.join(choices)}")


def ask_path(question, default=None, must_exist=True):
    while True:
        value = ask(question, default=default)
        path = Path(value).expanduser()
        if must_exist and not path.exists():
            print(f"  not found: {path}")
            continue
        return path


def main():
    print("Requirements analyzer\n")

    input_path = ask_path("Input SRS path (.csv or .txt)")
    fmt = ask_choice("Output format", ("html", "json", "both"), default="html")
    output_dir = Path(ask("Output folder", default="output")).expanduser()

    extensions = ("html", "json") if fmt == "both" else (fmt,)
    output_paths = [output_dir / f"{input_path.stem}.{ext}" for ext in extensions]

    print()
    df = load_input(str(input_path))
    print(f"Loaded {len(df)} requirements across {df['project_id'].nunique()} projects")

    analyzer = RequirementsAnalyzer("models", verbose=True)
    report = analyzer.analyze(df)
    for path in output_paths:
        save_output(report, str(path))

    s = report["summary"]
    print()
    for path in output_paths:
        print(f"Report saved: {path}")
    print(f"  FR / NFR: {s['classification']['functional']} / {s['classification']['non_functional']}")
    print(f"  With smells: {s['smells']['any_smell']} "
          f"(ambiguity={s['smells']['ambiguity']}, weak_verb={s['smells']['weak_verb']}, incompleteness={s['smells']['incompleteness']})")
    print(f"  Duplicate pairs: {s['duplicates']['count']}")
    print(f"  Contradiction pairs: {s['contradictions']['count']}")


if __name__ == "__main__":
    main()
