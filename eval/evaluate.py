#!/usr/bin/env python3
"""
RAG Evaluation Script
=====================
Runs benchmark questions against the live API and reports:
- Answer relevance (keyword hit rate)
- Source retrieval rate
- Latency (avg, p95)
- Cost per query
- LLM-as-judge faithfulness score

Usage:
    python evaluate.py --api-url http://localhost:8000 --tenant-id demo

"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx
from openai import OpenAI

BENCHMARK_PATH = Path(__file__).parent / "benchmark.json"
JUDGE_PROMPT = """You are evaluating a RAG chatbot response.

Question: {question}
Answer: {answer}

Rate the answer on two dimensions (1-5 scale):
1. Relevance: Does the answer address the question?
2. Groundedness: Does the answer appear factual and grounded (not hallucinated)?

Respond ONLY with a JSON object:
{{"relevance": <1-5>, "groundedness": <1-5>, "reason": "<one sentence>"}}
"""


def keyword_hit_rate(answer: str, keywords: list[str]) -> float:
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return round(hits / len(keywords), 2) if keywords else 0.0


def llm_judge(client: OpenAI, question: str, answer: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer)}],
            temperature=0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"relevance": 0, "groundedness": 0, "reason": f"Judge error: {e}"}


def run_evaluation(api_url: str, tenant_id: str, use_judge: bool = False, api_key: str | None = None) -> None:
    benchmark = json.loads(BENCHMARK_PATH.read_text())
    samples = benchmark["samples"]

    print(f"\n{'=' * 60}")
    print(f"RAG Evaluation — tenant: {tenant_id}")
    print(f"Benchmark: {len(samples)} questions")
    print(f"API: {api_url}")
    print(f"{'=' * 60}\n")

    client = OpenAI(api_key=api_key) if use_judge and api_key else None
    results = []

    with httpx.Client(timeout=30) as http:
        for sample in samples:
            start = time.perf_counter()
            try:
                res = http.post(
                    f"{api_url}/chat",
                    json={"tenant_id": tenant_id, "question": sample["question"]},
                )
                elapsed = (time.perf_counter() - start) * 1000

                if res.status_code != 200:
                    print(f"  ❌ [{sample['id']}] HTTP {res.status_code}: {res.json().get('detail')}")
                    results.append({"id": sample["id"], "error": True})
                    continue

                data = res.json()
                answer = data["answer"]
                sources = data.get("sources", [])
                khr = keyword_hit_rate(answer, sample["expected_keywords"])

                judge_scores = {}
                if client:
                    judge_scores = llm_judge(client, sample["question"], answer)

                result = {
                    "id": sample["id"],
                    "category": sample["category"],
                    "question": sample["question"],
                    "answer": answer[:120] + "..." if len(answer) > 120 else answer,
                    "keyword_hit_rate": khr,
                    "has_sources": len(sources) > 0,
                    "latency_ms": round(elapsed),
                    "api_latency_ms": data.get("latency_ms"),
                    "cost_usd": data.get("cost_usd", 0),
                    **judge_scores,
                }
                results.append(result)

                judge_str = f"  judge: {judge_scores.get('relevance', '–')}/5" if judge_scores else ""
                print(
                    f"  ✅ [{sample['id']}] {sample['category']:<12} "
                    f"khr={khr:.0%}  sources={'yes' if result['has_sources'] else 'no'}  "
                    f"latency={result['latency_ms']}ms{judge_str}"
                )

            except Exception as e:
                print(f"  ❌ [{sample['id']}] Error: {e}")
                results.append({"id": sample["id"], "error": True})

    # ── Summary ───────────────────────────────────────────────────────────────
    successful = [r for r in results if not r.get("error")]
    if not successful:
        print("\nNo successful results to summarize.")
        return

    avg_khr = statistics.mean(r["keyword_hit_rate"] for r in successful)
    source_rate = statistics.mean(1 if r["has_sources"] else 0 for r in successful)
    latencies = [r["latency_ms"] for r in successful]
    avg_latency = statistics.mean(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    total_cost = sum(r.get("cost_usd", 0) for r in successful)

    print(f"\n{'─' * 60}")
    print("SUMMARY")
    print(f"{'─' * 60}")
    print(f"  Questions answered   : {len(successful)}/{len(samples)}")
    print(f"  Avg keyword hit rate : {avg_khr:.0%}")
    print(f"  Source retrieval rate: {source_rate:.0%}")
    print(f"  Avg latency          : {avg_latency:.0f}ms")
    print(f"  P95 latency          : {p95_latency:.0f}ms")
    print(f"  Total cost           : ${total_cost:.5f}")
    print(f"  Cost per query       : ${total_cost/len(successful):.6f}")

    if use_judge and any("relevance" in r for r in successful):
        avg_rel = statistics.mean(r.get("relevance", 0) for r in successful if "relevance" in r)
        avg_gnd = statistics.mean(r.get("groundedness", 0) for r in successful if "groundedness" in r)
        print(f"  LLM judge relevance  : {avg_rel:.1f}/5")
        print(f"  LLM judge grounded   : {avg_gnd:.1f}/5")

    # Save results
    output_path = Path(__file__).parent / "results_latest.json"
    output_path.write_text(json.dumps({"summary": {
        "avg_keyword_hit_rate": round(avg_khr, 3),
        "source_retrieval_rate": round(source_rate, 3),
        "avg_latency_ms": round(avg_latency),
        "p95_latency_ms": p95_latency,
        "total_cost_usd": round(total_cost, 6),
        "cost_per_query_usd": round(total_cost / len(successful), 7),
    }, "results": successful}, indent=2))
    print(f"\n  Results saved → {output_path}")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Support system")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--tenant-id", default="demo")
    parser.add_argument("--judge", action="store_true", help="Use LLM-as-judge (requires OPENAI_API_KEY)")
    parser.add_argument("--openai-api-key", default=None)
    args = parser.parse_args()

    import os
    api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    run_evaluation(args.api_url, args.tenant_id, use_judge=args.judge, api_key=api_key)
