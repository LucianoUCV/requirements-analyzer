from .analyzer import CLASS_LONG_NAMES, CLASS_NAMES_12
from .rules import AMB_REGEX, INC_REGEX, WV_REGEX


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Requirements Analysis Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
h1 {{ border-bottom: 3px solid #2E86AB; padding-bottom: .3rem; }}
h2 {{ color: #2E86AB; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: .2rem; }}
.metadata {{ background: #f4f8fb; padding: 1rem; border-radius: 6px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }}
.summary-card {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 1rem; }}
.summary-card h3 {{ margin: 0 0 .5rem; color: #A23B72; }}
.summary-card .big {{ font-size: 2rem; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ text-align: left; padding: .5rem .8rem; border-bottom: 1px solid #eee; }}
th {{ background: #f4f8fb; font-weight: 600; }}
tr:hover {{ background: #fafcfd; }}
.smell-tag {{ display: inline-block; padding: .15rem .5rem; margin-right: .3rem; border-radius: 3px; font-size: .85rem; }}
.smell-amb {{ background: #fdebd0; color: #8b6914; }}
.smell-wv {{ background: #d6eaf8; color: #1b4f72; }}
.smell-inc {{ background: #fadbd8; color: #922b21; }}
.req-text {{ color: #333; }}
.confidence {{ color: #888; font-size: .85rem; }}
.fr {{ color: #2E86AB; font-weight: 600; }}
.nfr {{ color: #A23B72; font-weight: 600; }}
.pair {{ background: #fafafa; padding: .8rem; margin: .5rem 0; border-left: 3px solid #06A77D; border-radius: 0 3px 3px 0; }}
.pair.contradiction {{ border-left-color: #c0392b; }}
.pair-meta {{ color: #888; font-size: .85rem; margin-bottom: .3rem; }}
.verify-status {{ display: inline-block; padding: .1rem .45rem; border-radius: 3px; font-size: .75rem; font-weight: 600; }}
.verify-verified {{ background: #d4efdf; color: #186a3b; }}
.verify-overridden {{ background: #fdebd0; color: #7d6608; }}
.verify-review {{ background: #fadbd8; color: #922b21; }}
.verify-kept {{ background: #ebedef; color: #566573; }}
.verify-auto {{ background: #eaf2f8; color: #1b4f72; }}
.review-row {{ background: #fcf5f4; padding: .8rem; margin: .5rem 0; border-left: 3px solid #c0392b; border-radius: 0 3px 3px 0; }}
.quality-card {{ grid-column: span 2; border-left: 6px solid #888; }}
.quality-excellent {{ border-left-color: #1e8449; }}
.quality-good {{ border-left-color: #28a745; }}
.quality-fair {{ border-left-color: #e0a800; }}
.quality-needs-work {{ border-left-color: #d35400; }}
.quality-poor {{ border-left-color: #c0392b; }}
.hl-amb {{ background: #ffe9b8; color: #5d4108; border-radius: 3px; padding: 0 .15rem; }}
.hl-wv  {{ background: #cee5ff; color: #1a3766; border-radius: 3px; padding: 0 .15rem; }}
.hl-inc {{ background: #ffd1d1; color: #5e0707; border-radius: 3px; padding: 0 .15rem; font-weight: 600; }}
.was-label {{ color: #888; font-style: italic; font-weight: 400; }}
.advice-section {{ margin: 1.5rem 0; }}
.advice-group {{ background: #fdfdfd; border: 1px solid #e3e3e3; border-left: 4px solid #888; padding: .8rem 1rem; margin: .6rem 0; border-radius: 0 4px 4px 0; }}
.advice-group.warn {{ border-left-color: #d35400; background: #fff7f0; }}
.advice-group.info {{ border-left-color: #2E86AB; background: #f4f8fb; }}
.advice-group.danger {{ border-left-color: #c0392b; background: #fcf5f4; }}
.advice-group h4 {{ margin: 0 0 .3rem; color: #333; }}
.advice-group .affected {{ color: #555; font-size: .85rem; margin: .2rem 0; }}
.advice-group .reco {{ margin-top: .3rem; }}
</style>
</head>
<body>
<h1>Requirements Analysis Report</h1>

<div class="metadata">
<p><strong>Generated:</strong> {generated_at} &nbsp;|&nbsp; <strong>Requirements:</strong> {n_requirements} &nbsp;|&nbsp; <strong>Projects:</strong> {n_projects}</p>
<p><strong>Thresholds:</strong> duplicate ≥ {dup_threshold}, contradiction sim ∈ [{cont_min}, {cont_max}]</p>
</div>

<h2>Summary</h2>
<div class="summary">
<div class="summary-card quality-card {quality_band_class}"><h3>Quality score</h3><div class="big">{quality_score}</div><div class="confidence">{quality_band} &middot; penalties: smells -{p_smell}, dup -{p_dup}, contra -{p_con}, override -{p_ov}</div></div>
<div class="summary-card"><h3>Functional</h3><div class="big">{n_fr}</div><div class="confidence">{pct_fr}% of total</div></div>
<div class="summary-card"><h3>Non-functional</h3><div class="big">{n_nfr}</div><div class="confidence">{pct_nfr}% of total</div></div>
<div class="summary-card"><h3>With smells</h3><div class="big">{any_smell}</div><div class="confidence">{pct_smell}% of total</div></div>
<div class="summary-card"><h3>Duplicate pairs</h3><div class="big">{n_dup}</div></div>
<div class="summary-card"><h3>Contradiction pairs</h3><div class="big">{n_con}</div></div>
</div>

{verify_block}

<h3>By NFR sub-class</h3>
<table>
<tr><th>Class</th><th>Name</th><th>Count</th></tr>
{class_rows}
</table>

<h3>Smells breakdown</h3>
<table>
<tr><th>Smell</th><th>Count</th><th>%</th></tr>
<tr><td>Ambiguity</td><td>{n_amb}</td><td>{pct_amb}%</td></tr>
<tr><td>Weak verb</td><td>{n_wv}</td><td>{pct_wv}%</td></tr>
<tr><td>Incompleteness</td><td>{n_inc}</td><td>{pct_inc}%</td></tr>
</table>

{review_block}

<h2>Requirements ({n_requirements})</h2>
<table>
<tr><th>ID</th><th>Project</th><th>Type</th><th>Status</th><th>Smells</th><th>Text</th></tr>
{req_rows}
</table>

{advice_section}

<h2>Duplicate pairs ({n_dup})</h2>
{dup_html}

<h2>Contradiction pairs ({n_con})</h2>
{con_html}

</body>
</html>"""


STATUS_TO_BADGE = {
    "verified":            ("verify-verified",   "✓ verified"),
    "overridden_by_bert":  ("verify-overridden", "↻ overridden"),
    "review_suggested":    ("verify-review",     "⚠ review"),
    "kept_low_confidence": ("verify-kept",       "· kept"),
    "auto_classified":     ("verify-auto",       "auto"),
}

ADVICE_SPECS = [
    ("ambiguity", "Ambiguity", "warn",
     "Replace ambiguous qualifiers (user-friendly, easily, quickly, fast, intuitive, simple) "
     "with measurable criteria, e.g. 'within 2 seconds' or 'completable in 3 clicks'."),
    ("weak_verb", "Weak verbs", "warn",
     "Replace permissive/vague verbs (allow, may, can, support, handle, manage, ensure) with "
     "binding ones (shall, must) and specify the action explicitly."),
    ("incompleteness", "Incompleteness", "danger",
     "Resolve placeholder content (TBD, TODO, <…>, ellipses, [INSERT_…]) before finalising "
     "the SRS - incomplete requirements cannot be implemented or tested."),
    ("overridden", "Overridden classifications", "info",
     "These requirements were re-classified by the model with high confidence (≥70%). "
     "The Type column shows the new class with '(was X)' indicating the original. "
     "Review the new labels to confirm the reassignment matches your intent."),
    ("review", "Review-suggested classifications", "warn",
     "The model was moderately uncertain (60–70% confidence) about your provided class. "
     "It kept your label, but a human re-read is worthwhile to confirm - especially for "
     "edge cases between L/SE (compliance vs. security) or A/MN (availability vs. maintainability)."),
]


def _escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _highlight_smells(text, smell_record):
    if not text:
        return ""
    intervals = []
    if smell_record.get("ambiguity"):
        for m in AMB_REGEX.finditer(text):
            intervals.append((m.start(), m.end(), "hl-amb"))
    if smell_record.get("weak_verb"):
        for m in WV_REGEX.finditer(text):
            intervals.append((m.start(), m.end(), "hl-wv"))
    if smell_record.get("incompleteness"):
        for m in INC_REGEX.finditer(text):
            intervals.append((m.start(), m.end(), "hl-inc"))
    if not intervals:
        return _escape(text)
    intervals.sort()
    merged = []
    for s, e, c in intervals:
        if merged and s < merged[-1][1]:
            continue
        merged.append((s, e, c))
    out, last = [], 0
    for s, e, c in merged:
        out.append(_escape(text[last:s]))
        out.append(f'<span class="{c}">{_escape(text[s:e])}</span>')
        last = e
    out.append(_escape(text[last:]))
    return "".join(out)


def _render_req_row(r):
    smells = []
    if r["smells"]["ambiguity"]:
        smells.append('<span class="smell-tag smell-amb">ambiguity</span>')
    if r["smells"]["weak_verb"]:
        smells.append('<span class="smell-tag smell-wv">weak verb</span>')
    if r["smells"]["incompleteness"]:
        smells.append('<span class="smell-tag smell-inc">incompleteness</span>')
    cls_label = (
        '<span class="fr">FR</span>' if r["classification"]["is_functional"]
        else f'<span class="nfr">NFR ({r["classification"]["nfr_class"]})</span>'
    )
    v = r["classification"].get("verification", {})
    status = v.get("status", "auto_classified")
    if status == "overridden_by_bert":
        cls_label += f' <small class="was-label">(was {_escape(v.get("human_label", "?"))})</small>'
    cls_class, badge_text = STATUS_TO_BADGE.get(status, ("verify-auto", status))
    status_html = f'<span class="verify-status {cls_class}">{badge_text}</span>'
    text_html = _highlight_smells(r["text"], r["smells"])
    return (
        f"<tr><td>{_escape(r['id'])}</td>"
        f"<td>{_escape(r['project_id'])}</td>"
        f"<td>{cls_label}</td>"
        f"<td>{status_html}</td>"
        f"<td>{' '.join(smells)}</td>"
        f"<td class='req-text'>{text_html}</td></tr>"
    )


def _render_pairs(pairs, reqs, kind):
    out = []
    for p in pairs[:200]:
        try:
            row_i, row_j = reqs[p["i"]], reqs[p["j"]]
            t_i, t_j = row_i["text"], row_j["text"]
            id_i, id_j = row_i["id"], row_j["id"]
        except (IndexError, TypeError):
            t_i = t_j = "[?]"
            id_i, id_j = p["i"], p["j"]
        extra = ""
        if "conflicts" in p:
            extra = " | conflicts: " + ", ".join(p["conflicts"])
        cls = "pair contradiction" if kind == "con" else "pair"
        out.append(
            f"<div class='{cls}'>"
            f"<div class='pair-meta'>sim={p['similarity']:.3f} | project {_escape(p.get('project_id','?'))}{extra}</div>"
            f"<div><strong>[{_escape(id_i)}]</strong> {_escape(t_i)}</div>"
            f"<div><strong>[{_escape(id_j)}]</strong> {_escape(t_j)}</div>"
            f"</div>"
        )
    if len(pairs) > 200:
        out.append(f"<p><em>...and {len(pairs) - 200} more pairs (see JSON output for full list).</em></p>")
    return "\n".join(out) if out else "<p><em>None detected.</em></p>"


def _render_advice_section(reqs, report):
    ids_with = {
        "ambiguity":      [r["id"] for r in reqs if r["smells"].get("ambiguity")],
        "weak_verb":      [r["id"] for r in reqs if r["smells"].get("weak_verb")],
        "incompleteness": [r["id"] for r in reqs if r["smells"].get("incompleteness")],
        "overridden":     [r["id"] for r in reqs
                           if r["classification"].get("verification", {}).get("status") == "overridden_by_bert"],
        "review":         [r["id"] for r in reqs
                           if r["classification"].get("verification", {}).get("status") == "review_suggested"],
    }

    dup_pair_labels = []
    for d in report.get("duplicates", []):
        try:
            dup_pair_labels.append(f'{reqs[d["i"]]["id"]} ↔ {reqs[d["j"]]["id"]}')
        except (IndexError, TypeError):
            dup_pair_labels.append(f'{d["i"]} ↔ {d["j"]}')
    con_pair_labels = []
    for c in report.get("contradictions", []):
        conf = ", ".join(c.get("conflicts", [])) or "?"
        try:
            con_pair_labels.append(f'{reqs[c["i"]]["id"]} ↔ {reqs[c["j"]]["id"]} ({conf})')
        except (IndexError, TypeError):
            con_pair_labels.append(f'{c["i"]} ↔ {c["j"]} ({conf})')

    parts = []
    for key, label, color, reco in ADVICE_SPECS:
        if ids_with[key]:
            affected = ", ".join(_escape(i) for i in ids_with[key])
            parts.append(
                f'<div class="advice-group {color}">'
                f'<h4>{label} ({len(ids_with[key])})</h4>'
                f'<div class="affected">Affected: {affected}</div>'
                f'<div class="reco">{_escape(reco)}</div>'
                f'</div>'
            )
    if dup_pair_labels:
        parts.append(
            '<div class="advice-group info">'
            f'<h4>Duplicate pairs ({len(dup_pair_labels)})</h4>'
            f'<div class="affected">Pairs: {", ".join(_escape(p) for p in dup_pair_labels)}</div>'
            f'<div class="reco">{_escape("Merge or remove one requirement from each pair to reduce redundancy.")}</div>'
            '</div>'
        )
    if con_pair_labels:
        parts.append(
            '<div class="advice-group danger">'
            f'<h4>Contradiction pairs ({len(con_pair_labels)})</h4>'
            f'<div class="affected">Pairs: {", ".join(_escape(p) for p in con_pair_labels)}</div>'
            f'<div class="reco">{_escape("Resolve the disagreement (numerical mismatch or negation flip) before delivery - both requirements cannot be satisfied simultaneously.")}</div>'
            '</div>'
        )

    if parts:
        return '<h2>Advice &amp; recommendations</h2><div class="advice-section">' + "".join(parts) + '</div>'
    return '<h2>Advice &amp; recommendations</h2><p class="confidence">No issues detected - this SRS looks clean.</p>'


def _render_verify_blocks(meta, summ, report):
    if not meta.get("verify_mode"):
        return "", ""
    v_counts = summ["classification"]["verification"]["counts"]
    def card(k, label):
        return f'<div class="summary-card"><h3>{label}</h3><div class="big">{v_counts.get(k, 0)}</div></div>'
    verify_block = (
        "<h3>Verification (input had a class column)</h3>"
        f'<p class="confidence">Override threshold: {meta["verify_override_threshold"]}'
        f' · Warn threshold: {meta["verify_warn_threshold"]}</p>'
        '<div class="summary">'
        + card("verified",            "Verified")
        + card("overridden_by_bert",  "Overridden")
        + card("review_suggested",    "Review")
        + card("kept_low_confidence", "Kept (low conf)")
        + card("auto_classified",     "Auto (no label)")
        + "</div>"
    )

    review_block = ""
    if report.get("review_suggested"):
        rows = []
        for rs in report["review_suggested"]:
            rows.append(
                f'<div class="review-row">'
                f'<div class="pair-meta">REQ <strong>{_escape(rs["id"])}</strong> '
                f'(project {_escape(rs["project_id"])}) · '
                f'provided: <strong>{_escape(rs["human_label"])}</strong> · '
                f'BERT suggests: <strong>{_escape(rs["bert_label"])}</strong> '
                f'(conf {rs["bert_confidence"]:.2f})</div>'
                f'<div>{_escape(rs["text"])}</div>'
                f'</div>'
            )
        review_block = (
            f'<h3>Review suggested ({len(report["review_suggested"])})</h3>'
            + "\n".join(rows)
        )
    return verify_block, review_block


def render_html(report):
    meta = report["metadata"]
    summ = report["summary"]
    reqs = report["requirements"]
    n = meta["n_requirements"]

    def pct(x):
        return f"{(x / n * 100) if n else 0:.1f}"

    quality = summ.get("quality", {})
    quality_band = quality.get("band", "-")
    quality_band_class = "quality-" + quality_band.lower().replace(" ", "-")
    penalties = quality.get("penalties", {})

    class_rows = "\n".join(
        f"<tr><td><strong>{c}</strong></td><td>{CLASS_LONG_NAMES.get(c, c)}</td><td>{summ['classification']['by_class'].get(c, 0)}</td></tr>"
        for c in CLASS_NAMES_12
    )
    req_rows = "\n".join(_render_req_row(r) for r in reqs)
    advice_section = _render_advice_section(reqs, report)
    verify_block, review_block = _render_verify_blocks(meta, summ, report)

    return HTML_TEMPLATE.format(
        generated_at=meta["generated_at"],
        n_requirements=n,
        n_projects=meta["n_projects"],
        dup_threshold=meta["duplicate_threshold"],
        cont_min=meta["contradiction_sim_min"],
        cont_max=meta["contradiction_sim_max"],
        n_fr=summ["classification"]["functional"],
        n_nfr=summ["classification"]["non_functional"],
        pct_fr=pct(summ["classification"]["functional"]),
        pct_nfr=pct(summ["classification"]["non_functional"]),
        any_smell=summ["smells"]["any_smell"],
        pct_smell=pct(summ["smells"]["any_smell"]),
        n_dup=summ["duplicates"]["count"],
        n_con=summ["contradictions"]["count"],
        class_rows=class_rows,
        req_rows=req_rows,
        n_amb=summ["smells"]["ambiguity"],
        n_wv=summ["smells"]["weak_verb"],
        n_inc=summ["smells"]["incompleteness"],
        pct_amb=pct(summ["smells"]["ambiguity"]),
        pct_wv=pct(summ["smells"]["weak_verb"]),
        pct_inc=pct(summ["smells"]["incompleteness"]),
        dup_html=_render_pairs(report["duplicates"], reqs, "dup"),
        con_html=_render_pairs(report["contradictions"], reqs, "con"),
        verify_block=verify_block,
        review_block=review_block,
        quality_score=quality.get("score", 0),
        quality_band=quality_band,
        quality_band_class=quality_band_class,
        p_smell=penalties.get("smells", 0),
        p_dup=penalties.get("duplicates", 0),
        p_con=penalties.get("contradictions", 0),
        p_ov=penalties.get("overrides", 0),
        advice_section=advice_section,
    )
