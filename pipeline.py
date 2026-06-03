import argparse

from requirements_analyzer import RequirementsAnalyzer, load_input, save_output


def main():
    parser = argparse.ArgumentParser(
        description="Requirements analyzer: classify, detect smells, find duplicates and contradictions in an SRS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, help="Input SRS file (.csv or .txt)")
    parser.add_argument("--output", required=True, help="Output report (.json or .html)")
    parser.add_argument("--models-dir", default="models",
                        help="Directory containing the saved BERT/SBERT models (default: 'models')")
    parser.add_argument("--duplicate-threshold", type=float, default=0.85,
                        help="Cosine similarity threshold for duplicates (default: 0.85)")
    parser.add_argument("--contradiction-sim-min", type=float, default=0.65,
                        help="Lower bound for contradiction candidates (default: 0.65)")
    parser.add_argument("--contradiction-sim-max", type=float, default=0.98,
                        help="Upper bound for contradiction candidates (default: 0.98)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages")
    args = parser.parse_args()

    verbose = not args.quiet

    if verbose:
        print(f"[main] Reading {args.input}")
    df = load_input(args.input)
    if verbose:
        print(f"[main] Loaded {len(df)} requirements across {df['project_id'].nunique()} projects")

    analyzer = RequirementsAnalyzer(args.models_dir, verbose=verbose)
    report = analyzer.analyze(
        df,
        dup_threshold=args.duplicate_threshold,
        contradiction_sim_min=args.contradiction_sim_min,
        contradiction_sim_max=args.contradiction_sim_max,
    )

    save_output(report, args.output)
    if verbose:
        s = report["summary"]
        print(f"\n[done] Report saved: {args.output}")
        print(f"  FR / NFR: {s['classification']['functional']} / {s['classification']['non_functional']}")
        print(f"  With smells: {s['smells']['any_smell']} "
              f"(ambiguity={s['smells']['ambiguity']}, weak_verb={s['smells']['weak_verb']}, incompleteness={s['smells']['incompleteness']})")
        print(f"  Duplicate pairs: {s['duplicates']['count']}")
        print(f"  Contradiction pairs: {s['contradictions']['count']}")


if __name__ == "__main__":
    main()
