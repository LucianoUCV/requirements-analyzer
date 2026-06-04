from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .rules import detect_conflicts, rule_incompleteness


CLASS_NAMES_12 = ["A", "F", "FT", "L", "LF", "MN", "O", "PE", "PO", "SC", "SE", "US"]
CLASS_LONG_NAMES = {
    "F":  "Functional",
    "A":  "Availability",
    "FT": "Fault Tolerance",
    "L":  "Legal",
    "LF": "Look & Feel",
    "MN": "Maintainability",
    "O":  "Operational",
    "PE": "Performance",
    "PO": "Portability",
    "SC": "Scalability",
    "SE": "Security",
    "US": "Usability",
}
SMELL_LABELS = ["ambiguity", "weak_verb"]
SMELL_KEYS = ("ambiguity", "weak_verb", "incompleteness")


def generate_advice(req, dup_partners, con_partners):
    advice = []
    sm = req.get("smells", {})
    if sm.get("incompleteness"):
        advice.append("Resolve placeholder content (TBD, TODO, <...>, ellipses) before finalising the SRS.")
    if sm.get("ambiguity"):
        advice.append("Replace ambiguous qualifiers with measurable criteria (e.g. 'within 2 seconds' instead of 'quickly').")
    if sm.get("weak_verb"):
        advice.append("Replace permissive or vague verbs (allow, may, can, handle, support) with binding ones (shall, must) and specify the action explicitly.")
    v = req.get("classification", {}).get("verification", {})
    status = v.get("status")
    if status == "overridden_by_bert":
        advice.append(
            f"Class re-assigned: provided '{v['human_label']}' → model says '{v['bert_label']}' "
            f"(conf {v['bert_confidence']:.2f}). Confirm the new label matches the intent."
        )
    elif status == "review_suggested":
        advice.append(
            f"Model uncertain ({v['bert_confidence']:.2f}): it suggests '{v['bert_label']}' but kept your '{v['human_label']}'. "
            "Worth a human re-read."
        )
    if dup_partners:
        advice.append("Near-duplicate of " + ", ".join(str(p) for p in dup_partners) + ". Consider merging or removing one.")
    if con_partners:
        details = "; ".join(f"{p_id} ({', '.join(conf)})" for p_id, conf in con_partners)
        advice.append(f"Contradicts {details}. Resolve before delivery.")
    return advice


def _summarize_smells(records):
    counts = {s: sum(1 for r in records if r["smells"][s]) for s in SMELL_KEYS}
    any_smell = sum(1 for r in records if any(r["smells"][s] for s in SMELL_KEYS))
    return counts, any_smell


def _summarize_verification(records):
    status_counts = {}
    n_overridden = 0
    n_labelled = 0
    review_list = []
    for r in records:
        status = r["classification"].get("verification", {}).get("status", "auto_classified")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status != "auto_classified":
            n_labelled += 1
        if status == "overridden_by_bert":
            n_overridden += 1
        if status == "review_suggested":
            v = r["classification"]["verification"]
            review_list.append({
                "id": r["id"],
                "project_id": r["project_id"],
                "text": r["text"],
                "human_label": v["human_label"],
                "bert_label": v["bert_label"],
                "bert_confidence": v["bert_confidence"],
            })
    return status_counts, n_overridden, n_labelled, review_list


def _compute_quality_score(any_smell, n, n_duplicates, n_contradictions, n_overridden, n_labelled):
    n_safe = max(n, 1)
    smell_density = any_smell / n_safe
    dup_density = min(2 * n_duplicates / n_safe, 1.0)
    con_density = min(2 * n_contradictions / n_safe, 1.0)
    override_density = (n_overridden / n_labelled) if n_labelled > 0 else 0.0
    penalties = {
        "smells":         round(60 * smell_density, 1),
        "duplicates":     round(15 * dup_density, 1),
        "contradictions": round(50 * con_density, 1),
        "overrides":      round(30 * override_density, 1),
    }
    score = max(0, round(100 - sum(penalties.values()), 1))
    if score >= 90:
        band = "Excellent"
    elif score >= 80:
        band = "Good"
    elif score >= 65:
        band = "Fair"
    elif score >= 50:
        band = "Needs work"
    else:
        band = "Poor"
    return score, band, penalties


def _summarize_per_project(records, duplicates, contradictions):
    by_pid = {}
    for r in records:
        by_pid.setdefault(r["project_id"], []).append(r)

    dup_count = {}
    for d in duplicates:
        dup_count[d["project_id"]] = dup_count.get(d["project_id"], 0) + 1
    con_count = {}
    for c in contradictions:
        con_count[c["project_id"]] = con_count.get(c["project_id"], 0) + 1

    out = {}
    for pid, recs in by_pid.items():
        n = len(recs)
        n_fr = sum(1 for r in recs if r["classification"]["is_functional"])
        any_smell = sum(1 for r in recs if any(r["smells"][s] for s in SMELL_KEYS))
        n_overridden = sum(
            1 for r in recs
            if r["classification"].get("verification", {}).get("status") == "overridden_by_bert"
        )
        n_labelled = sum(
            1 for r in recs
            if r["classification"].get("verification", {}).get("status") != "auto_classified"
        )
        score, band, _ = _compute_quality_score(
            any_smell, n, dup_count.get(pid, 0), con_count.get(pid, 0), n_overridden, n_labelled
        )
        out[pid] = {
            "n_requirements": n,
            "n_fr": n_fr,
            "n_nfr": n - n_fr,
            "n_smells": any_smell,
            "n_duplicates": dup_count.get(pid, 0),
            "n_contradictions": con_count.get(pid, 0),
            "quality_score": score,
            "quality_band": band,
        }
    return out


class RequirementsAnalyzer:
    def __init__(self, models_dir, sbert_model_name="sentence-transformers/all-MiniLM-L6-v2", verbose=True):
        self.models_dir = Path(models_dir)
        self.verbose = verbose
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        if self.verbose:
            print(f"[init] Device: {self.device}")

        # Multi-class classifier
        multi_dir = self.models_dir / "bert_multiclass"
        if self.verbose:
            print(f"[init] Loading multi-class classifier from {multi_dir}")
        self.tokenizer_cls = AutoTokenizer.from_pretrained(str(multi_dir), use_fast=True)
        self.model_multi = AutoModelForSequenceClassification.from_pretrained(str(multi_dir)).to(self.device).eval()

        # Binary classifier
        binary_dir = self.models_dir / "bert_binary"
        if self.verbose:
            print(f"[init] Loading binary classifier from {binary_dir}")
        self.model_binary = AutoModelForSequenceClassification.from_pretrained(str(binary_dir)).to(self.device).eval()

        # Smell detection
        smell_dir = self.models_dir / "bert_smell"
        if self.verbose:
            print(f"[init] Loading smell detection from {smell_dir}")
        self.tokenizer_smell = AutoTokenizer.from_pretrained(str(smell_dir), use_fast=True)
        self.model_smell = AutoModelForSequenceClassification.from_pretrained(str(smell_dir)).to(self.device).eval()

        # SBERT for duplicates and contradictions
        if self.verbose:
            print(f"[init] Loading SBERT: {sbert_model_name}")
        self.sbert = SentenceTransformer(sbert_model_name, device=self.device)

        self.class_names = sorted(CLASS_NAMES_12)

        if self.verbose:
            print(f"[init] Ready.")

    @torch.no_grad()
    def classify(self, texts, batch_size=32):
        results = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            enc = self.tokenizer_cls(list(batch), truncation=True, padding="max_length",
                                     max_length=128, return_tensors="pt").to(self.device)
            multi_logits = self.model_multi(**enc).logits
            multi_probs = torch.softmax(multi_logits, dim=-1).cpu().numpy()
            multi_pred = multi_probs.argmax(axis=-1)

            binary_logits = self.model_binary(**enc).logits
            binary_probs = torch.softmax(binary_logits, dim=-1).cpu().numpy()
            binary_pred = binary_probs.argmax(axis=-1)

            for i in range(len(batch)):
                cls_idx = int(multi_pred[i])
                cls_name = self.class_names[cls_idx]
                is_functional = bool(binary_pred[i] == 0) or cls_name == "F"
                results.append({
                    "nfr_class": cls_name,
                    "nfr_class_long": CLASS_LONG_NAMES.get(cls_name, cls_name),
                    "nfr_confidence": float(multi_probs[i, cls_idx]),
                    "is_functional": is_functional,
                    "fr_confidence": float(binary_probs[i, 0]),
                })
        return results

    @torch.no_grad()
    def detect_smells(self, texts, batch_size=32):
        rule_inc = [rule_incompleteness(t) for t in texts]

        bert_amb, bert_wv, bert_amb_conf, bert_wv_conf = [], [], [], []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            enc = self.tokenizer_smell(list(batch), truncation=True, padding="max_length",
                                       max_length=128, return_tensors="pt").to(self.device)
            logits = self.model_smell(**enc).logits
            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs > 0.5).astype(int)
            for p, pr in zip(preds, probs):
                bert_amb.append(int(p[0]))
                bert_wv.append(int(p[1]))
                bert_amb_conf.append(float(pr[0]))
                bert_wv_conf.append(float(pr[1]))

        return [
            {
                "ambiguity": bool(bert_amb[k]),
                "ambiguity_bert_confidence": bert_amb_conf[k],
                "weak_verb": bool(bert_wv[k]),
                "weak_verb_bert_confidence": bert_wv_conf[k],
                "incompleteness": bool(rule_inc[k]),
            }
            for k in range(len(texts))
        ]

    def find_duplicates(self, texts, project_ids, threshold=0.85, embeddings=None):
        if embeddings is None:
            embeddings = self._encode(texts)
        pairs = []
        project_ids = np.asarray(project_ids)
        for pid in np.unique(project_ids):
            idx = np.where(project_ids == pid)[0]
            if len(idx) < 2:
                continue
            sim = cosine_similarity(embeddings[idx])
            n = len(idx)
            for i in range(n):
                for j in range(i + 1, n):
                    if sim[i, j] >= threshold:
                        pairs.append({
                            "i": int(idx[i]),
                            "j": int(idx[j]),
                            "similarity": float(sim[i, j]),
                            "project_id": str(pid),
                        })
        pairs.sort(key=lambda p: -p["similarity"])
        return pairs, embeddings

    def find_contradictions(self, texts, project_ids, sim_min=0.65, sim_max=0.985, embeddings=None):
        if embeddings is None:
            embeddings = self._encode(texts)
        pairs = []
        project_ids = np.asarray(project_ids)
        texts_arr = list(texts)
        for pid in np.unique(project_ids):
            idx = np.where(project_ids == pid)[0]
            if len(idx) < 2:
                continue
            sim = cosine_similarity(embeddings[idx])
            n = len(idx)
            for i in range(n):
                for j in range(i + 1, n):
                    s = sim[i, j]
                    if not (sim_min <= s <= sim_max):
                        continue
                    conflicts = detect_conflicts(texts_arr[idx[i]], texts_arr[idx[j]])
                    if conflicts:
                        pairs.append({
                            "i": int(idx[i]),
                            "j": int(idx[j]),
                            "similarity": float(s),
                            "conflicts": conflicts,
                            "project_id": str(pid),
                        })
        pairs.sort(key=lambda p: -p["similarity"])
        return pairs, embeddings

    def _encode(self, texts):
        return self.sbert.encode(
            list(texts), batch_size=64, show_progress_bar=False,
            convert_to_numpy=True, normalize_embeddings=True,
        )

    def _reconcile_classifications(self, bert_results, human_labels,
                                   override_threshold=0.75, warn_threshold=0.60):
        out = []
        for bert, raw_human in zip(bert_results, human_labels):
            bert_class = bert["nfr_class"]
            bert_conf = bert["nfr_confidence"]

            human_provided = (
                raw_human is not None
                and str(raw_human).strip() != ""
                and str(raw_human).strip().lower() != "nan"
            )
            if not human_provided:
                result = dict(bert)
                result["verification"] = {"status": "auto_classified"}
                out.append(result)
                continue

            human = str(raw_human).strip().upper()
            if human not in CLASS_NAMES_12:
                result = dict(bert)
                result["verification"] = {
                    "status": "auto_classified",
                    "note": f"provided class '{raw_human}' is not a recognised NFR class; ignored",
                }
                out.append(result)
                continue

            if bert_class == human:
                result = dict(bert)
                result["verification"] = {
                    "status": "verified",
                    "human_label": human,
                    "bert_label": bert_class,
                    "bert_confidence": bert_conf,
                }
            elif bert_conf >= override_threshold:
                result = dict(bert)
                result["verification"] = {
                    "status": "overridden_by_bert",
                    "human_label": human,
                    "bert_label": bert_class,
                    "bert_confidence": bert_conf,
                    "note": f"Provided class '{human}' overridden to '{bert_class}' (BERT conf {bert_conf:.2f}).",
                }
            elif bert_conf >= warn_threshold:
                result = dict(bert)
                result["nfr_class"] = human
                result["nfr_class_long"] = CLASS_LONG_NAMES.get(human, human)
                result["is_functional"] = (human == "F")
                result["verification"] = {
                    "status": "review_suggested",
                    "human_label": human,
                    "bert_label": bert_class,
                    "bert_confidence": bert_conf,
                    "note": f"BERT suggests '{bert_class}' (conf {bert_conf:.2f}); kept provided label '{human}'.",
                }
            else:
                result = dict(bert)
                result["nfr_class"] = human
                result["nfr_class_long"] = CLASS_LONG_NAMES.get(human, human)
                result["is_functional"] = (human == "F")
                result["verification"] = {
                    "status": "kept_low_confidence",
                    "human_label": human,
                    "bert_label": bert_class,
                    "bert_confidence": bert_conf,
                }
            out.append(result)
        return out

    def analyze(self, df, dup_threshold=0.85, contradiction_sim_min=0.65, contradiction_sim_max=0.985,
                verify_override_threshold=0.75, verify_warn_threshold=0.55):
        texts = df["text"].tolist()
        project_ids = df["project_id"].astype(str).tolist()
        ids = df["id"].tolist() if "id" in df.columns else list(range(len(df)))

        has_human_labels = "class" in df.columns
        human_labels = df["class"].tolist() if has_human_labels else None

        # Classification (+verification if labels provided)
        if self.verbose:
            mode = "verify (with human labels)" if has_human_labels else "auto-classify"
            print(f"[analyze] Classifying {len(texts)} requirements [{mode}]...")
        bert_classifications = self.classify(texts)
        if has_human_labels:
            classifications = self._reconcile_classifications(
                bert_classifications, human_labels,
                override_threshold=verify_override_threshold,
                warn_threshold=verify_warn_threshold,
            )
        else:
            classifications = [
                {**c, "verification": {"status": "auto_classified"}}
                for c in bert_classifications
            ]

        if self.verbose:
            print(f"[analyze] Detecting smells...")
        smells = self.detect_smells(texts)

        if self.verbose:
            print(f"[analyze] Encoding for SBERT...")
        embeddings = self._encode(texts)

        if self.verbose:
            print(f"[analyze] Finding duplicates (threshold {dup_threshold})...")
        duplicates, _ = self.find_duplicates(texts, project_ids, dup_threshold, embeddings=embeddings)

        if self.verbose:
            print(f"[analyze] Finding contradictions (sim ∈ [{contradiction_sim_min}, {contradiction_sim_max}])...")
        contradictions, _ = self.find_contradictions(
            texts, project_ids, contradiction_sim_min, contradiction_sim_max, embeddings=embeddings
        )

        contradiction_keys = {tuple(sorted((c["i"], c["j"]))) for c in contradictions}
        duplicates = [
            d for d in duplicates
            if tuple(sorted((d["i"], d["j"]))) not in contradiction_keys
        ]

        records = []
        for text, pid, rid, cls, sm in zip(texts, project_ids, ids, classifications, smells):
            records.append({
                "id": rid,
                "project_id": pid,
                "text": text,
                "classification": cls,
                "smells": sm,
            })

        dup_partners = {}
        for d in duplicates:
            id_i, id_j = ids[d["i"]], ids[d["j"]]
            dup_partners.setdefault(id_i, []).append(id_j)
            dup_partners.setdefault(id_j, []).append(id_i)
        con_partners = {}
        for c in contradictions:
            id_i, id_j = ids[c["i"]], ids[c["j"]]
            conflicts = c.get("conflicts", [])
            con_partners.setdefault(id_i, []).append((id_j, conflicts))
            con_partners.setdefault(id_j, []).append((id_i, conflicts))
        for r in records:
            r["advice"] = generate_advice(
                r,
                dup_partners.get(r["id"], []),
                con_partners.get(r["id"], []),
            )

        n = len(records)
        n_fr = sum(1 for r in records if r["classification"]["is_functional"])
        n_nfr = n - n_fr
        by_class = {}
        for r in records:
            c = r["classification"]["nfr_class"]
            by_class[c] = by_class.get(c, 0) + 1
        smelly_counts, any_smell = _summarize_smells(records)
        status_counts, n_overridden, n_labelled, review_list = _summarize_verification(records)
        quality_score, band, penalties = _compute_quality_score(
            any_smell, n, len(duplicates), len(contradictions), n_overridden, n_labelled
        )

        per_project = _summarize_per_project(records, duplicates, contradictions)

        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "n_requirements": n,
                "n_projects": len(set(project_ids)),
                "duplicate_threshold": dup_threshold,
                "contradiction_sim_min": contradiction_sim_min,
                "contradiction_sim_max": contradiction_sim_max,
                "verify_mode": bool(has_human_labels),
                "verify_override_threshold": verify_override_threshold if has_human_labels else None,
                "verify_warn_threshold": verify_warn_threshold if has_human_labels else None,
            },
            "summary": {
                "quality": {"score": quality_score, "band": band, "penalties": penalties},
                "classification": {
                    "functional": n_fr,
                    "non_functional": n_nfr,
                    "by_class": by_class,
                    "verification": {
                        "mode": "verify" if has_human_labels else "auto_classify",
                        "counts": status_counts,
                    },
                },
                "smells": {
                    **smelly_counts,
                    "any_smell": any_smell,
                    "clean": n - any_smell,
                },
                "duplicates": {"count": len(duplicates)},
                "contradictions": {"count": len(contradictions)},
                "per_project": per_project,
            },
            "review_suggested": review_list,
            "requirements": records,
            "duplicates": duplicates,
            "contradictions": contradictions,
        }
