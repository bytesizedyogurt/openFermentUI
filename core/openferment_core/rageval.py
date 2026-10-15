"""Every lane scored on the same questions, and a rule that picks the default
(OF-BLD-014 §4.3).

THREE QUESTION SETS.

- K, known items. Built by code, free, and it grows with the corpus. For
  every record or anchored candidate whose quote sits verbatim (after
  `normalize_text`) in a fetched passage, a question is made from the
  field's name, the organism and the carbon source where it has them.
  Records sharing a field and an organism make one question. A passage is
  relevant when it holds an anchored quote for that field and organism.
- S, written questions. `pnpm rag:questions --n 200` samples passages,
  seeded and spread across papers and kinds, and asks the `index` role for
  one question each that the passage answers, without its numbers or rare
  strings. A question sharing five consecutive words with its passage, or
  copying one of its numbers, is discarded and counted. The sampled passage
  is the relevant one. Kept in `core/data/rageval/questions.jsonl`.
- F, the flows. For each authored flow that cites records, the relevant
  passages are those holding an anchored quote of a record it expects. A
  flow none of whose records anchor is left out, and the report says how
  many flows F covers.

METRICS per lane and set: recall@5, @10, @20, MRR@10, nDCG@10 (binary
relevance), median seconds, model cost per question.

THE RULE, `choose_lane`: a lane's score is the mean of its nDCG@10 on K and
S (those present). `bm25` holds the choice until a lane scores higher; a lane
that spends a model call on every question must lead the best free lane by
`PAID_MARGIN` or more. An unavailable lane is skipped.

    pnpm rag:questions --n 200    writes S (needs the key)
    pnpm rag:eval                 scores every available lane, writes
                                  core/data/rageval/report.json and the choice
                                  into core/data/index/config.json
"""
from __future__ import annotations

import json
import math
import random
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from . import atomic, intake, llm, passages, retrieve
from .models import RagLaneReport, RagMetrics, RagReport, RagSetInfo, Usage
from .validate import normalize_text

PAID_MARGIN = 0.02
FREE = ("bm25", "hybrid")
RULE = (
    "A lane's score is the mean of its nDCG@10 on K and on S. bm25 holds the choice until a lane "
    "scores higher; a lane that spends a model call on every question must lead the best free lane "
    f"by {PAID_MARGIN} or more. An unavailable lane is skipped."
)
QUESTION_PROMPT = "questions-1"
# Passages per helper call when S is written, and the seed of the sample:
# conventions (E.1).
BATCH = 10
SEED = 14
OVERLAP_WORDS = 5


def rageval_dir() -> Path:
    return intake.DATA_DIR / "rageval"


@dataclass
class Question:
    id: str
    set: str
    text: str
    relevant: list[str]
    source: dict[str, Any] = field(default_factory=dict)


# ── anchoring an item to passages ──────────────────────────────────────


def _by_paper(cuts: list[passages.Cut]) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for c in cuts:
        out.setdefault(c.passage.paperId, []).append((c.passage.id, normalize_text(c.passage.text)))
    return out


def anchored_passages(item: dict[str, Any], by_paper: dict[str, list[tuple[str, str]]]) -> list[str]:
    """The passages of the item's paper whose text holds its quote verbatim."""
    quote = normalize_text(str(item.get("quote") or ""))
    if len(quote) < 12:  # too short to locate anything; a convention
        return []
    return [pid for pid, text in by_paper.get(str(item.get("paperId")), []) if quote in text]


def _organism_labels(aliases: dict[str, str]) -> dict[str, str]:
    """A strain id's longest alias, as the words a question uses."""
    out: dict[str, str] = {}
    for alias, sid in aliases.items():
        if len(alias) > len(out.get(sid, "")):
            out[sid] = alias
    return out


def _corpus_extras() -> tuple[dict[str, str], dict[str, str]]:
    """Field names and strain labels from corpus.json."""
    from . import units
    from .corpus import DATA

    fields = {fid: f.get("name", fid) for fid, f in units.tables()["ontology"].items()}
    try:
        aliases = json.loads(DATA.read_text(encoding="utf-8")).get("strainAliases") or {}
    except (FileNotFoundError, ValueError):
        aliases = {}
    return fields, _organism_labels(aliases)


# ── K ──────────────────────────────────────────────────────────────────


def build_k(items: Iterable[dict[str, Any]], cuts: list[passages.Cut], field_names: dict[str, str], organisms: dict[str, str]) -> tuple[list[Question], dict[str, int]]:
    """One question per (field, organism) group of items whose quote anchors.
    Returns the questions and how many records and candidates they hold."""
    by_paper = _by_paper(cuts)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    counts = {"records": 0, "candidates": 0}
    for item in items:
        found = anchored_passages(item, by_paper)
        if not found:
            continue
        counts["candidates" if item.get("source") == "candidate" else "records"] += 1
        fid = str(item.get("field"))
        sid = item.get("strainId") or ""
        organism = organisms.get(sid) or (sid.replace("-", " ") if sid else (item.get("organismText") or ""))
        g = groups.setdefault((fid, organism), {"relevant": [], "carbon": set(), "items": []})
        g["relevant"] += [p for p in found if p not in g["relevant"]]
        if item.get("carbonSource"):
            g["carbon"].add(str(item["carbonSource"]))
        g["items"].append(item["id"])
    questions = []
    for n, ((fid, organism), g) in enumerate(sorted(groups.items())):
        words = field_names.get(fid, fid).split(" (")[0]
        text = words + (f" of {organism}" if organism else "")
        if len(g["carbon"]) == 1:
            text += f" grown on {next(iter(g['carbon']))}"
        questions.append(Question(id=f"K{n + 1}", set="K", text=text, relevant=g["relevant"], source={"field": fid, "items": g["items"]}))
    return questions, counts


# ── F ──────────────────────────────────────────────────────────────────


def build_f(flows: list[dict[str, Any]], records_by_id: dict[str, dict[str, Any]], cuts: list[passages.Cut]) -> tuple[list[Question], int]:
    by_paper = _by_paper(cuts)
    questions = []
    gradable = [f for f in flows if f.get("recordIds")]
    for f in gradable:
        relevant: list[str] = []
        for rid in f["recordIds"]:
            rec = records_by_id.get(rid)
            if rec:
                relevant += [p for p in anchored_passages(rec, by_paper) if p not in relevant]
        if relevant:
            questions.append(Question(id=f"F-{f['id']}", set="F", text=f["question"], relevant=relevant, source={"flow": f["id"]}))
    return questions, len(gradable)


# ── S ──────────────────────────────────────────────────────────────────

SYSTEM_S = (
    "You write evaluation questions for a search over research papers. For each passage, write one question "
    "a bioprocess engineer would ask that this passage answers. Use your own words: copy no number from the "
    "passage, no strain designation, accession, gene name or other rare string, and no run of words from it. "
    "Return one question per passage, by its id."
)
SCHEMA_S = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"passageId": {"type": "string"}, "question": {"type": "string"}},
                "required": ["passageId", "question"],
            },
        }
    },
    "required": ["questions"],
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def copies_passage(question: str, passage_text: str) -> str | None:
    """Why a written question is discarded, or None."""
    q = _words(question)
    p = _words(passage_text)
    grams = {tuple(p[i : i + OVERLAP_WORDS]) for i in range(len(p) - OVERLAP_WORDS + 1)}
    if any(tuple(q[i : i + OVERLAP_WORDS]) in grams for i in range(len(q) - OVERLAP_WORDS + 1)):
        return "five words in a row from the passage"
    numbers_p = set(re.findall(r"\d+(?:\.\d+)?", passage_text))
    if set(re.findall(r"\d+(?:\.\d+)?", question)) & numbers_p:
        return "a number from the passage"
    return None


def sample(cuts: list[passages.Cut], n: int, seed: int = SEED) -> list[passages.Cut]:
    """`n` passages spread across papers and kinds: papers in a seeded
    order, each giving one passage of the kind it has given least, round
    after round."""
    rng = random.Random(seed)
    by_paper: dict[str, dict[str, list[passages.Cut]]] = {}
    for c in cuts:
        if len(c.passage.text) < 200:  # too little to ask about; a convention
            continue
        by_paper.setdefault(c.passage.paperId, {}).setdefault(c.passage.kind, []).append(c)
    for kinds in by_paper.values():
        for pool in kinds.values():
            rng.shuffle(pool)
    papers = sorted(by_paper)
    rng.shuffle(papers)
    taken: list[passages.Cut] = []
    kind_count: dict[str, int] = {}
    while len(taken) < n and any(any(k.values()) for k in by_paper.values()):
        for pid in papers:
            kinds = {k: v for k, v in by_paper[pid].items() if v}
            if not kinds or len(taken) >= n:
                continue
            kind = min(kinds, key=lambda k: (kind_count.get(k, 0), k))
            taken.append(kinds[kind].pop())
            kind_count[kind] = kind_count.get(kind, 0) + 1
    return taken


def write_questions(n: int, *, ask: Callable[..., llm.Result] | None = None, seed: int = SEED) -> dict[str, Any]:
    cuts = passages.read_index()
    chosen = sample(cuts, n, seed)
    kept: list[Question] = []
    discarded: dict[str, int] = {}
    usage = Usage()
    for start in range(0, len(chosen), BATCH):
        batch = chosen[start : start + BATCH]
        by_id = {c.passage.id: c for c in batch}
        user = "Passages:\n\n" + "\n\n".join(f"[{c.passage.id}] ({c.context})\n{c.passage.text}" for c in batch)
        result = (ask or llm.call)(system=SYSTEM_S, user=user, schema=SCHEMA_S, max_tokens=4000, label="rag:questions: ", role="index")
        usage = llm.add(usage, result.usage)
        seen: set[str] = set()
        for q in (result.data or {}).get("questions", []):
            pid = str(q.get("passageId", "")) if isinstance(q, dict) else ""
            text = str(q.get("question", "")).strip() if isinstance(q, dict) else ""
            if pid not in by_id or pid in seen or not text:
                discarded["no usable question"] = discarded.get("no usable question", 0) + 1
                continue
            seen.add(pid)
            why = copies_passage(text, by_id[pid].passage.text)
            if why:
                discarded[why] = discarded.get(why, 0) + 1
                continue
            kept.append(Question(id=f"S{len(kept) + 1}", set="S", text=text, relevant=[pid], source={"passage": pid, "kind": by_id[pid].passage.kind}))
        missing = len(batch) - len(seen)
        if missing > 0:
            discarded["no question returned"] = discarded.get("no question returned", 0) + missing
    lines = [json.dumps(q.__dict__, ensure_ascii=False) for q in kept]
    atomic.write_text(rageval_dir() / "questions.jsonl", "\n".join(lines) + ("\n" if lines else ""))
    meta = {"asked": len(chosen), "kept": len(kept), "discarded": discarded, "seed": seed, "costUsd": usage.costUsd, "manifestHash": passages.manifest_hash()}
    atomic.write_text(rageval_dir() / "questions.json", json.dumps(meta, indent=2) + "\n")
    return meta


def read_s() -> tuple[list[Question], dict[str, Any]]:
    path = rageval_dir() / "questions.jsonl"
    if not path.exists():
        return [], {}
    qs = [Question(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        meta = json.loads((rageval_dir() / "questions.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        meta = {}
    return qs, meta


# ── metrics ────────────────────────────────────────────────────────────


def recall_at(ranked: list[str], relevant: Iterable[str], k: int) -> float:
    rel = set(relevant)
    return len(rel & set(ranked[:k])) / len(rel) if rel else 0.0


def mrr_at(ranked: list[str], relevant: Iterable[str], k: int = 10) -> float:
    rel = set(relevant)
    for i, pid in enumerate(ranked[:k], start=1):
        if pid in rel:
            return 1.0 / i
    return 0.0


def ndcg_at(ranked: list[str], relevant: Iterable[str], k: int = 10) -> float:
    rel = set(relevant)
    dcg = sum(1.0 / math.log2(i + 1) for i, pid in enumerate(ranked[:k], start=1) if pid in rel)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(rel), k) + 1))
    return dcg / ideal if ideal else 0.0


def score_set(runs: list[tuple[list[str], list[str], float, float]]) -> RagMetrics:
    """`runs` holds, per question, (ranked ids, relevant ids, seconds, cost)."""
    n = len(runs)
    mean = lambda xs: round(sum(xs) / n, 4) if n else 0.0  # noqa: E731
    return RagMetrics(
        questions=n,
        recall5=mean([recall_at(r, rel, 5) for r, rel, _, _ in runs]),
        recall10=mean([recall_at(r, rel, 10) for r, rel, _, _ in runs]),
        recall20=mean([recall_at(r, rel, 20) for r, rel, _, _ in runs]),
        mrr10=mean([mrr_at(r, rel) for r, rel, _, _ in runs]),
        ndcg10=mean([ndcg_at(r, rel) for r, rel, _, _ in runs]),
        medianSeconds=round(statistics.median([s for _, _, s, _ in runs]), 4) if n else 0.0,
        costPerQuestion=round(sum(c for _, _, _, c in runs) / n, 6) if n else 0.0,
    )


# ── the rule ───────────────────────────────────────────────────────────


def lane_score(lane: RagLaneReport) -> float | None:
    present = [lane.sets[s].ndcg10 for s in ("K", "S") if s in lane.sets and lane.sets[s].questions > 0]
    return round(sum(present) / len(present), 4) if present else None


def choose_lane(report: RagReport) -> str:
    runs = {l.lane: l for l in report.lanes if l.available and l.score is not None}
    chosen = "bm25"
    best = runs["bm25"].score if "bm25" in runs else float("-inf")
    for name in FREE:
        if name in runs and runs[name].score is not None and runs[name].score > best:
            chosen, best = name, runs[name].score
    best_free = best
    for name, lane in runs.items():
        if name in FREE or lane.score is None:
            continue
        if lane.score >= best_free + PAID_MARGIN - 1e-9 and lane.score > best:
            chosen, best = name, lane.score
    return chosen


# ── the run ────────────────────────────────────────────────────────────


def build_sets() -> tuple[dict[str, list[Question]], list[RagSetInfo]]:
    from .corpus import load_corpus
    from .evidence_pool import load as load_pool

    cuts = passages.read_index()
    field_names, organisms = _corpus_extras()
    pool = load_pool()
    k_questions, k_counts = build_k(pool.records, cuts, field_names, organisms)
    flows_path = Path(__file__).parent.parent / "tests" / "fixtures" / "flows.json"
    flows = json.loads(flows_path.read_text(encoding="utf-8")) if flows_path.exists() else []
    f_questions, f_total = build_f(flows, load_corpus().records_by_id, cuts)
    s_questions, s_meta = read_s()
    discarded = sum((s_meta.get("discarded") or {}).values())
    infos = [
        RagSetInfo(name="K", questions=len(k_questions), note=f"known items: {k_counts['records']} records and {k_counts['candidates']} anchored candidates whose quote sits in a passage"),
        RagSetInfo(
            name="S",
            questions=len(s_questions),
            note=(f"written questions: {len(s_questions)} kept of {s_meta.get('asked', 0)} asked, {discarded} discarded" if s_meta else "written questions: none yet (pnpm rag:questions needs the key)"),
        ),
        RagSetInfo(name="F", questions=len(f_questions), note=f"flows: {len(f_questions)} of the {f_total} flows that cite records have a record that anchors"),
    ]
    return {"K": k_questions, "S": s_questions, "F": f_questions}, infos


def evaluate(
    *,
    ask: Callable[..., llm.Result] | None = None,
    embedder=None,
    lanes: Iterable[str] = retrieve.LANES,
    sets: dict[str, list[Question]] | None = None,
    infos: list[RagSetInfo] | None = None,
) -> RagReport:
    if sets is None:
        sets, infos = build_sets()
    infos = infos or []
    status = passages.status()
    reports: list[RagLaneReport] = []
    total = 0.0
    for lane in lanes:
        why = retrieve.why_unavailable(lane, embedder=embedder)
        rep = RagLaneReport(lane=lane, available=why is None, why=why, paid=lane in retrieve.PAID)
        if why is None:
            for name, questions in sets.items():
                if not questions:
                    continue
                runs = []
                for q in questions:
                    started = time.perf_counter()
                    detail = retrieve.search_detail(q.text, k=20, lane=lane, ask=ask, embedder=embedder)
                    runs.append(([h.passage.id for h in detail.hits], q.relevant, time.perf_counter() - started, detail.usage.costUsd))
                    total += detail.usage.costUsd
                rep.sets[name] = score_set(runs)
            rep.score = lane_score(rep)
        reports.append(rep)
    report = RagReport(
        date=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        manifestHash=passages.manifest_hash(),
        papersIndexed=status.papersIndexed,
        passages=status.passages,
        sets=infos,
        lanes=reports,
        chosenLane="bm25",
        rule=RULE,
        totalCostUsd=round(total, 6),
    )
    report.chosenLane = choose_lane(report)
    return report


def save(report: RagReport) -> None:
    atomic.write_text(rageval_dir() / "report.json", report.model_dump_json(indent=2) + "\n")
    table = {l.lane: l.score for l in report.lanes}
    atomic.write_text(
        passages.index_dir() / "config.json",
        json.dumps({"lane": report.chosenLane, "chosenAt": report.date, "scores": table, "rule": report.rule}, indent=2) + "\n",
    )


def read_report() -> RagReport | None:
    try:
        return RagReport.model_validate_json((rageval_dir() / "report.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def _print(report: RagReport) -> None:
    print(f"index: {report.papersIndexed} papers, {report.passages} passages · {report.date}")
    for s in report.sets:
        print(f"  {s.name}: {s.note}")
    print(f"{'lane':<15}{'set':>4}{'n':>5}{'R@5':>7}{'R@10':>7}{'R@20':>7}{'MRR':>7}{'nDCG':>7}{'sec':>8}{'$/q':>9}")
    for l in report.lanes:
        if not l.available:
            print(f"{l.lane:<15} unavailable: {l.why}")
            continue
        for name, m in l.sets.items():
            print(f"{l.lane:<15}{name:>4}{m.questions:>5}{m.recall5:>7.3f}{m.recall10:>7.3f}{m.recall20:>7.3f}{m.mrr10:>7.3f}{m.ndcg10:>7.3f}{m.medianSeconds:>8.3f}{m.costPerQuestion:>9.4f}")
    print(f"chosen: {report.chosenLane} · total cost ${report.totalCostUsd:.4f}")


def main(argv: list[str]) -> int:
    if argv[:1] == ["questions"]:
        n = 200
        if "--n" in argv:
            n = int(argv[argv.index("--n") + 1])
        meta = write_questions(n)
        print(f"questions: {meta['kept']} kept of {meta['asked']} asked; discarded {meta['discarded']}; ${meta['costUsd']:.4f}")
        return 0
    if argv[:1] == ["eval"]:
        report = evaluate()
        save(report)
        _print(report)
        return 0
    print("usage: python -m openferment_core.rageval questions [--n 200] | eval")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
