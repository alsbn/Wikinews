
import json
import math
import statistics
import time
from pathlib import Path

import requests

from search_engine import search


API = "https://it.wikinews.org/w/api.php"
CUTOFF = "2025-03-20T23:59:59Z"

QUERIES = [
    "governo Belgio",
    "elezioni Italia",
    "crisi finanziaria",
    "Olimpiadi",
    "calcio italiano",
    "terremoto",
    "cambiamenti climatici",
    "Francia",
    "Africa",
    "internet",
    "economia europea",
    "guerra Ucraina",
    "energia nucleare",
    "Unione Europea",
    "scuola italiana",
    "trasporti",
    "sanità",
    "ambiente",
    "tecnologia",
    "diritti umani"
]


def normalize_title(title):
    return " ".join(
        title.replace("_", " ").casefold().split()
    )


def wikinews_search(query):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 0,
        "srlimit": 50,
        "srprop": "timestamp",
        "format": "json"
    }

    headers = {
        "User-Agent": "WikinewsSearchBenchmark/1.0"
    }

    results = []
    seen = set()

    while len(results) < 10:

        response = requests.get(
            API,
            params=params,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        for item in data["query"]["search"]:

            timestamp = item.get("timestamp", "")

            if not timestamp or timestamp > CUTOFF:
                continue

            title = item["title"]
            normalized = normalize_title(title)

            if normalized in seen:
                continue

            seen.add(normalized)

            results.append({
                "title": title,
                "timestamp": timestamp
            })

            if len(results) == 10:
                break

        continuation = data.get("continue")

        if not continuation:
            break

        params.update(continuation)

    return results[:10]


def calculate_metrics(local, wiki, k=10):

    # Baseline: primi 10 risultati Wikinews.
    wiki = wiki[:k]
    local = local[:k]

    relevant = {
        normalize_title(item["title"]): rank
        for rank, item in enumerate(wiki, start=1)
    }

    local_titles = [
        normalize_title(item["title"])
        for item in local
    ]

    # Rimuove eventuali duplicati.
    local_titles = list(dict.fromkeys(local_titles))

    relevant_count = len(relevant)

    retrieved_relevant = sum(
        1 for title in local_titles
        if title in relevant
    )

    # Precision@10
    precision = retrieved_relevant / k

    # Recall@10
    recall = (
        retrieved_relevant / relevant_count
        if relevant_count > 0 else 0.0
    )

    # DCG@10
    dcg = 0.0

    for rank, title in enumerate(local_titles, start=1):

        rel = 1 if title in relevant else 0

        dcg += rel / math.log2(rank + 1)

    # IDCG@10
    ideal_relevant = min(relevant_count, k)

    idcg = sum(
        1 / math.log2(rank + 1)
        for rank in range(1, ideal_relevant + 1)
    )

    # NDCG@10
    ndcg = (
        dcg / idcg
        if idcg > 0 else 0.0
    )

    # MRR (Reciprocal Rank della singola query)
    reciprocal_rank = 0.0

    for rank, title in enumerate(local_titles, start=1):

        if title in relevant:
            reciprocal_rank = 1 / rank
            break

    # Overlap@10
    overlap = retrieved_relevant / k

    return {
        "precision_at_10": round(precision, 4),
        "recall_at_10": round(recall, 4),
        "ndcg_at_10": round(ndcg, 4),
        "mrr": round(reciprocal_rank, 4),
        "overlap_at_10": round(overlap, 4)
    }


def main():

    reports = []

    for query in QUERIES:

        # Warm-up escluso dalla misurazione.
        search(query, limit=10)

        local_times = []
        local_results = []

        # Misurazione del motore locale.
        for _ in range(5):

            start = time.perf_counter()

            local_results = search(query, limit=10)

            local_times.append(
                time.perf_counter() - start
            )

        # Misurazione Wikinews.
        start = time.perf_counter()

        wiki_results = wikinews_search(query)

        wiki_time = time.perf_counter() - start

        local = [
            {
                "title": item["title"],
                "url": item["url"]
            }
            for item in local_results
        ]

        # Calcolo metriche rispetto alla baseline Wikinews.
        metrics = calculate_metrics(
            local,
            wiki_results,
            k=10
        )

        result = {
            "query": query,

            "local_count": len(local),
            "wiki_count": len(wiki_results),

            "local_median_ms": round(
                statistics.median(local_times) * 1000,
                2
            ),

            "local_p95_ms": round(
                sorted(local_times)[-1] * 1000,
                2
            ),

            "wiki_time_ms": round(
                wiki_time * 1000,
                2
            ),

            "metrics": metrics,

            "local_results": local,
            "wiki_results": wiki_results
        }

        reports.append(result)

        print(
            f"\nQuery: {query}"
            f"\n  Precision@10: {metrics['precision_at_10']}"
            f"\n  Recall@10:    {metrics['recall_at_10']}"
            f"\n  NDCG@10:      {metrics['ndcg_at_10']}"
            f"\n  MRR:          {metrics['mrr']}"
            f"\n  Overlap@10:   {metrics['overlap_at_10']}"
            f"\n  Local:        {result['local_median_ms']} ms"
            f"\n  Wikinews:     {result['wiki_time_ms']} ms"
        )

    # Calcolo medie aggregate (Macro-average).
    metric_names = [
        "precision_at_10",
        "recall_at_10",
        "ndcg_at_10",
        "mrr",
        "overlap_at_10"
    ]

    averages = {}

    for metric in metric_names:

        averages[metric] = round(
            statistics.mean(
                report["metrics"][metric]
                for report in reports
            ),
            4
        )

    # Report finale.
    output = {
        "cutoff": CUTOFF,
        "number_of_queries": len(QUERIES),
        "baseline": "Wikinews",
        "averages": averages,
        "reports": reports
    }

    Path("reports").mkdir(exist_ok=True)

    with open(
        "reports/benchmark.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n========== RISULTATI AGGREGATI ==========")

    for metric, value in averages.items():
        print(f"{metric}: {value}")

    print(
        "\nBenchmark salvato in reports/benchmark.json"
    )


if __name__ == "__main__":
    main()
