"""Evaluate retrieved evidence and preserve per-query traces."""
import re
from typing import Any


def clean_str(s: str) -> str:
    """Normalize string for robust substring matching."""
    return re.sub(r"\s+", " ", s.lower()).strip()


def is_chunk_hit(gold_question: dict[str, Any], chunk: dict[str, Any]) -> bool:
    """A hit occurs when the chunk belongs to the gold page and contains the gold evidence quote."""
    chunk_page = chunk.get("page")
    gold_page = gold_question.get("gold_page")
    if chunk_page != gold_page:
        return False

    chunk_text_norm = clean_str(chunk.get("text", ""))
    evidence_norm = clean_str(gold_question.get("evidence_quote", ""))

    # Direct match or partial match on significant slice of evidence
    if evidence_norm in chunk_text_norm:
        return True

    # If evidence was split or slightly sliced, test first 60 chars of evidence
    short_evidence = evidence_norm[:min(len(evidence_norm), 60)].strip()
    return short_evidence in chunk_text_norm


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and gold evidence; keep hit@1 and hit@3 trace."""
    hit_ranks: list[int] = []

    for rank, h in enumerate(hits, start=1):
        if is_chunk_hit(question, h):
            hit_ranks.append(rank)

    hit_at_1 = (1 in hit_ranks)
    hit_at_3 = (len(hit_ranks) > 0)

    # Check filter compliance if filter was specified
    filter_complied = True
    flt = question.get("filter")
    if flt:
        for h in hits:
            meta = h.get("metadata", {})
            for k, v in flt.items():
                if meta.get(k) != v:
                    filter_complied = False
                    break

    return {
        "question_id": question.get("id"),
        "split": question.get("split"),
        "question": question.get("question"),
        "gold_page": question.get("gold_page"),
        "evidence_quote": question.get("evidence_quote"),
        "filter": flt,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_ranks": hit_ranks,
        "filter_complied": filter_complied,
        "top_3_hits": [
            {
                "rank": idx + 1,
                "chunk_id": h.get("chunk_id"),
                "page": h.get("page"),
                "score": h.get("score"),
                "text_snippet": (h.get("text", "")[:200] + "...") if len(h.get("text", "")) > 200 else h.get("text", ""),
                "section": h.get("metadata", {}).get("section")
            }
            for idx, h in enumerate(hits)
        ]
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    splits = ["all", "dev", "test"]
    summary: dict[str, Any] = {}

    for s in splits:
        subset = traces if s == "all" else [t for t in traces if t.get("split") == s]
        total = len(subset)
        if total == 0:
            continue

        hit1_count = sum(1 for t in subset if t["hit_at_1"])
        hit3_count = sum(1 for t in subset if t["hit_at_3"])

        # Filter compliance
        filtered_subset = [t for t in subset if t.get("filter")]
        if filtered_subset:
            filter_ok = sum(1 for t in filtered_subset if t["filter_complied"])
            filter_ratio = f"{filter_ok}/{len(filtered_subset)}"
        else:
            filter_ratio = "N/A"

        summary[s] = {
            "total_questions": total,
            "hit_at_1": f"{hit1_count}/{total}",
            "hit_at_1_pct": round(hit1_count / total * 100, 2),
            "hit_at_3": f"{hit3_count}/{total}",
            "hit_at_3_pct": round(hit3_count / total * 100, 2),
            "filter_compliance": filter_ratio
        }

    return summary
