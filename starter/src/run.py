"""Pipeline orchestration for Day 06 Data Ingestion Engineering."""
import json
import time
from pathlib import Path
from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .store import QdrantVectorStore
from .evaluation import evaluate_query, summarize


def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent.parent
    data_pdf = root_dir / "data" / "chapter1_workplace_skills.pdf"
    benchmark_file = root_dir / "benchmark" / "questions.json"
    results_dir = root_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("DAY 06 · DATA INGESTION ENGINEERING BENCHMARK")
    print("==================================================")

    # 1. Load Corpus
    print("\n[Step 1] Loading and normalizing PDF corpus...")
    start_ingest = time.time()
    pages = load_pdf(data_pdf, document_id="openstax-workplace-skills-ch01", source="data/chapter1_workplace_skills.pdf")
    ingest_time = time.time() - start_ingest
    print(f"Loaded {len(pages)} content pages in {ingest_time:.2f}s")

    # 2. Load Benchmark Questions
    print("\n[Step 2] Loading benchmark questions...")
    with open(benchmark_file, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} verified questions (dev: {sum(1 for q in questions if q['split'] == 'dev')}, test: {sum(1 for q in questions if q['split'] == 'test')})")

    # 3. Initialize Embedder and Vector Store
    print("\n[Step 3] Initializing Embedder and Vector Store...")
    embedder = MyEmbedder(model_name="gemini-embedding-001")
    store = QdrantVectorStore(storage_path=str(root_dir / "starter" / "qdrant_db"), dimensions=embedder.dimensions)

    strategies_summary = {}
    all_traces = {}

    # ========================================================
    # STRATEGY A: Fixed-size Chunking (size=500, overlap=50)
    # ========================================================
    print("\n--------------------------------------------------")
    print("Executing STRATEGY A: Fixed-size (500 chars, 50 overlap)")
    print("--------------------------------------------------")
    t0 = time.time()
    chunks_a = []
    for p in pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    print(f"Generated {len(chunks_a)} chunks for Strategy A")

    texts_a = [c.text for c in chunks_a]
    print(f"Embedding {len(texts_a)} chunks via Gemini API...")
    vectors_a = embedder.embed_documents(texts_a)
    store.upsert("strategy_a", chunks_a, vectors_a)
    build_time_a = time.time() - t0

    # Retrieve & evaluate Strategy A
    traces_a = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        hits = store.search("strategy_a", query_vector=q_vec, top_k=3, filters=None)
        tr = evaluate_query(q, hits)
        traces_a.append(tr)

    summary_a = summarize(traces_a)
    strategies_summary["strategy_a"] = {
        "chunk_count": len(chunks_a),
        "build_time_s": round(build_time_a, 2),
        "summary": summary_a
    }
    all_traces["strategy_a"] = traces_a

    # ========================================================
    # STRATEGY B: Structure-aware Chunking (by_paragraph, max 800)
    # ========================================================
    print("\n--------------------------------------------------")
    print("Executing STRATEGY B: Structure-aware (by paragraph, max 800)")
    print("--------------------------------------------------")
    t0 = time.time()
    chunks_b = []
    for p in pages:
        chunks_b.extend(by_paragraph(p, max_size=800))
    print(f"Generated {len(chunks_b)} chunks for Strategy B")

    texts_b = [c.text for c in chunks_b]
    print(f"Embedding {len(texts_b)} chunks via Gemini API...")
    vectors_b = embedder.embed_documents(texts_b)
    store.upsert("strategy_b", chunks_b, vectors_b)
    build_time_b = time.time() - t0

    # Retrieve & evaluate Strategy B (no filter)
    traces_b = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        hits = store.search("strategy_b", query_vector=q_vec, top_k=3, filters=None)
        tr = evaluate_query(q, hits)
        traces_b.append(tr)

    summary_b = summarize(traces_b)
    strategies_summary["strategy_b"] = {
        "chunk_count": len(chunks_b),
        "build_time_s": round(build_time_b, 2),
        "summary": summary_b
    }
    all_traces["strategy_b"] = traces_b

    # ========================================================
    # STRATEGY C: Structure-aware + Metadata Filter
    # ========================================================
    print("\n--------------------------------------------------")
    print("Executing STRATEGY C: Structure-aware + Metadata Filter")
    print("--------------------------------------------------")
    t0 = time.time()
    # Strategy C reuses the exact same chunks and collection as B
    traces_c = []
    for q in questions:
        q_vec = embedder.embed_query(q["question"])
        flt = q.get("filter")
        hits = store.search("strategy_b", query_vector=q_vec, top_k=3, filters=flt)
        tr = evaluate_query(q, hits)
        traces_c.append(tr)

    build_time_c = time.time() - t0
    summary_c = summarize(traces_c)
    strategies_summary["strategy_c"] = {
        "chunk_count": len(chunks_b),
        "build_time_s": round(build_time_c, 2),
        "summary": summary_c
    }
    all_traces["strategy_c"] = traces_c

    # Save outputs
    traces_path = results_dir / "traces.json"
    with open(traces_path, "w", encoding="utf-8") as f:
        json.dump(all_traces, f, ensure_ascii=False, indent=2)

    summary_path = results_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(strategies_summary, f, ensure_ascii=False, indent=2)

    print("\n==================================================")
    print("BENCHMARK EXECUTION COMPLETE!")
    print(f"Results saved to: {traces_path.resolve()}")
    print("==================================================")

    # Print summary table
    print("\n--- RESULTS OVERVIEW ---")
    for strat, name in [("strategy_a", "A (Fixed-size)"), ("strategy_b", "B (Paragraph)"), ("strategy_c", "C (Para + Filter)")]:
        s = strategies_summary[strat]["summary"]
        cnt = strategies_summary[strat]["chunk_count"]
        print(f"\n[{name}] - Chunks: {cnt}")
        print(f"  Dev  (15): Hit@1 = {s['dev']['hit_at_1']} ({s['dev']['hit_at_1_pct']}%), Hit@3 = {s['dev']['hit_at_3']} ({s['dev']['hit_at_3_pct']}%)")
        print(f"  Test  (5): Hit@1 = {s['test']['hit_at_1']} ({s['test']['hit_at_1_pct']}%), Hit@3 = {s['test']['hit_at_3']} ({s['test']['hit_at_3_pct']}%)")
        print(f"  All  (20): Hit@1 = {s['all']['hit_at_1']} ({s['all']['hit_at_1_pct']}%), Hit@3 = {s['all']['hit_at_3']} ({s['all']['hit_at_3_pct']}%), Filter Compliance = {s['all']['filter_compliance']}")


if __name__ == "__main__":
    main()
