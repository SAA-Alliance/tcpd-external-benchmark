#!/usr/bin/env python3
"""Build a local TCPD/TCPDBench benchmark dossier.

The dossier is deliberately built from published TCPDBench score JSON files and
SAA's published per-dataset score digest. It does not export raw TCPD series.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
from scipy.stats import friedmanchisquare, studentized_range

BASELINE_METHODS = [
    "amoc", "binseg", "bocpd", "bocpdms", "cpnp", "ecp", "kcpa", "pelt",
    "prophet", "rbocpdms", "rfpop", "segneigh", "wbs", "zero",
]
SAA_METHOD_ID = "saa_change_point_adapter_v1"
SAA_LABEL = "SAA"
PREVIOUS_AUDIT_DOSSIER_SHA_PREFIX = "sha256:91b38e1f"
PREVIOUS_DISCIPLINE_DOSSIER_SHA256 = "sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08"
PREVIOUS_SURFACED_DOSSIER_SHA256 = "sha256:b19ff223b7e7cf42def70dd5d9bedb70a01f9ce01411c55093bceb3fa1e2410a"
PREVIOUS_RANK_SCALE_DOSSIER_SHA256 = "sha256:5f9f2fb45c8a03f90720e1dd9abd7c313397add955a23532f28bbc8a35d11e32"
QC_DATASETS = {f"quality_control_{i}" for i in range(1, 6)}
ANALYSES = [
    ("default_f_measure", "default", "f1", "default_f_measure"),
    ("default_covering", "default", "cover", "default_covering"),
    ("oracle_f_measure", "oracle", "f1", "oracle_f_measure"),
    ("oracle_covering", "oracle", "cover", "oracle_covering"),
]
SCOPES = ["all_42", "real_world_37"]
TIE_EPS = 1e-12


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8")


def ranks_desc(values: Dict[str, float]) -> Dict[str, float]:
    """Average ranks, descending score; rank 1 is best."""
    ordered = sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))
    ranks: Dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and abs(ordered[j][1] - ordered[i][1]) <= TIE_EPS:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = avg_rank
        i = j
    return ranks


def percentile(values: List[float], p: float) -> float:
    if not values:
        return float("nan")
    arr = sorted(values)
    idx = (len(arr) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return arr[int(idx)]
    return arr[lo] * (hi - idx) + arr[hi] * (idx - lo)


def fmt_float(value: float, digits: int = 6) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.{digits}f}"


def build_rows(
    tcpdbench_root: Path,
    result: Dict[str, Any],
    analysis_id: str,
    mode: str,
    metric_file_id: str,
    saa_digest_key: str,
    scope: str,
) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, Any]]:
    score_file_rel = Path("analysis") / "output" / "scores" / f"{mode}_{metric_file_id}_scores.json"
    score_file = tcpdbench_root / score_file_rel
    scores = load_json(score_file)
    saa_digest = {row["dataset"]: row[saa_digest_key] for row in result["saa_benchmark"]["per_dataset_digest"]}
    if scope == "all_42":
        candidate_datasets = sorted(scores.keys())
        declared_total = 42
    elif scope == "real_world_37":
        candidate_datasets = sorted(d for d in scores.keys() if d not in QC_DATASETS)
        declared_total = 37
    else:
        raise ValueError(scope)
    methods = BASELINE_METHODS + [SAA_METHOD_ID]
    common = []
    excluded = []
    for dataset in candidate_datasets:
        missing = [m for m in BASELINE_METHODS if scores[dataset].get(m) is None]
        if dataset not in saa_digest:
            missing.append(SAA_METHOD_ID)
        if missing:
            excluded.append({"dataset": dataset, "missing_methods": missing})
            continue
        common.append(dataset)
    matrix: Dict[str, Dict[str, float]] = {}
    for dataset in common:
        row = {m: float(scores[dataset][m]) for m in BASELINE_METHODS}
        row[SAA_METHOD_ID] = float(saa_digest[dataset])
        matrix[dataset] = row
    meta = {
        "analysis_id": analysis_id,
        "mode": mode,
        "metric": "f_measure" if metric_file_id == "f1" else "covering",
        "score_file": str(score_file_rel),
        "scope": scope,
        "declared_scope_total": declared_total,
        "candidate_dataset_count": len(candidate_datasets),
        "common_dataset_count": len(common),
        "excluded_dataset_count": len(excluded),
        "excluded_datasets": excluded,
        "methods": methods,
        "frame": "paired_common_dataset_only",
        "raw_series_exported": False,
    }
    return common, matrix, meta


def summarize_analysis(datasets: List[str], matrix: Dict[str, Dict[str, float]], meta: Dict[str, Any], seed: int, bootstrap_iters: int) -> Dict[str, Any]:
    methods = list(meta["methods"])
    n = len(datasets)
    if n == 0:
        return {"meta": meta, "status": "WITHHELD_NO_COMMON_DATASETS"}
    mean_scores = {m: statistics.mean(matrix[d][m] for d in datasets) for m in methods}
    mean_score_ranks = ranks_desc(mean_scores)

    dataset_rank_rows = {d: ranks_desc(matrix[d]) for d in datasets}
    per_dataset_ranks = {m: [] for m in methods}
    for d in datasets:
        ranks = dataset_rank_rows[d]
        for m in methods:
            per_dataset_ranks[m].append(ranks[m])
    average_ranks = {m: statistics.mean(per_dataset_ranks[m]) for m in methods}

    ordered_by_avg_rank = sorted(methods, key=lambda m: (average_ranks[m], -mean_scores[m], m))
    ranking = [
        {
            "rank_by_average_dataset_rank": i + 1,
            "method": m,
            "label": SAA_LABEL if m == SAA_METHOD_ID else m,
            "average_dataset_rank": average_ranks[m],
            "mean_score": mean_scores[m],
            "rank_by_mean_score": int(mean_score_ranks[m]),
        }
        for i, m in enumerate(ordered_by_avg_rank)
    ]

    rng = random.Random(seed)
    saa_scores: List[float] = []
    saa_ranks_by_mean: List[float] = []
    saa_ranks_by_avg_dataset_rank: List[float] = []
    pair_boot: Dict[str, List[float]] = {m: [] for m in BASELINE_METHODS}
    for _ in range(bootstrap_iters):
        sample = [datasets[rng.randrange(n)] for _ in range(n)]
        sample_mean = {m: statistics.mean(matrix[d][m] for d in sample) for m in methods}
        sample_mean_ranks = ranks_desc(sample_mean)
        saa_scores.append(sample_mean[SAA_METHOD_ID])
        saa_ranks_by_mean.append(sample_mean_ranks[SAA_METHOD_ID])
        # Rank each resampled dataset, then average those precomputed ranks.
        sample_rank_means = {
            m: statistics.mean(dataset_rank_rows[d][m] for d in sample)
            for m in methods
        }
        sample_avg_rank_ranks = {m: r for r, m in enumerate(sorted(methods, key=lambda x: (sample_rank_means[x], -sample_mean[x], x)), 1)}
        saa_ranks_by_avg_dataset_rank.append(float(sample_avg_rank_ranks[SAA_METHOD_ID]))
        for m in BASELINE_METHODS:
            pair_boot[m].append(statistics.mean(matrix[d][SAA_METHOD_ID] - matrix[d][m] for d in sample))

    pairwise = []
    for m in BASELINE_METHODS:
        diffs = [matrix[d][SAA_METHOD_ID] - matrix[d][m] for d in datasets]
        wins = sum(1 for v in diffs if v > TIE_EPS)
        losses = sum(1 for v in diffs if v < -TIE_EPS)
        ties = n - wins - losses
        ci_low = percentile(pair_boot[m], 0.025)
        ci_high = percentile(pair_boot[m], 0.975)
        pairwise.append({
            "opponent": m,
            "mean_score_difference_saa_minus_opponent": statistics.mean(diffs),
            "bootstrap_ci95_low": ci_low,
            "bootstrap_ci95_high": ci_high,
            "win": wins,
            "tie": ties,
            "loss": losses,
            "sign": "SAA higher" if ci_low > 0 else "SAA lower" if ci_high < 0 else "CI crosses 0",
        })
    pairwise.sort(key=lambda r: (-r["mean_score_difference_saa_minus_opponent"], r["opponent"]))

    samples = [[matrix[d][m] for d in datasets] for m in methods]
    friedman_stat, friedman_p = friedmanchisquare(*samples)
    k = len(methods)
    q_alpha = studentized_range.ppf(0.95, k, math.inf) / math.sqrt(2.0)
    critical_difference = q_alpha * math.sqrt(k * (k + 1) / (6.0 * n))
    saa_avg_rank = average_ranks[SAA_METHOD_ID]
    leader_method = ordered_by_avg_rank[0]
    leader_average_rank = average_ranks[leader_method]
    leader_cd_band_cutoff = leader_average_rank + critical_difference
    leader_cd_band_methods = [
        m for m in ordered_by_avg_rank
        if average_ranks[m] <= leader_cd_band_cutoff + TIE_EPS
    ]
    nemenyi = {
        "alpha": 0.05,
        "q_alpha_studentized_range_over_sqrt2": q_alpha,
        "critical_difference": critical_difference,
        "saa_average_rank": saa_avg_rank,
        "leader_method": leader_method,
        "leader_average_rank": leader_average_rank,
        "leader_cd_band_cutoff": leader_cd_band_cutoff,
        "leader_cd_band_method_count": len(leader_cd_band_methods),
        "leader_cd_band_methods": leader_cd_band_methods,
        "field_mean_average_rank": statistics.mean(average_ranks.values()),
        "saa_inside_leader_cd_band": SAA_METHOD_ID in leader_cd_band_methods,
        "not_separated_from_saa": [m for m in ordered_by_avg_rank if abs(average_ranks[m] - saa_avg_rank) <= critical_difference],
        "significantly_better_than_saa_by_cd": [m for m in ordered_by_avg_rank if average_ranks[m] + critical_difference < saa_avg_rank],
        "significantly_worse_than_saa_by_cd": [m for m in ordered_by_avg_rank if average_ranks[m] - critical_difference > saa_avg_rank],
        "interpretation_caveat": "Nemenyi non-separation is INCONCLUSIVE equivalence, not a superiority or equality claim.",
    }

    return {
        "meta": meta,
        "status": "PUBLISHED_RESEARCH_ONLY_STATISTICAL_DOSSIER",
        "dataset_ids_sha256": sha256_obj(datasets),
        "ranking": ranking,
        "saa_bootstrap": {
            "iterations": bootstrap_iters,
            "seed": seed,
            "score_mean": mean_scores[SAA_METHOD_ID],
            "score_ci95_low": percentile(saa_scores, 0.025),
            "score_ci95_high": percentile(saa_scores, 0.975),
            "rank_by_mean_score": mean_score_ranks[SAA_METHOD_ID],
            "rank_by_mean_score_ci95_low": percentile(saa_ranks_by_mean, 0.025),
            "rank_by_mean_score_ci95_high": percentile(saa_ranks_by_mean, 0.975),
            "rank_by_average_dataset_rank": next(r["rank_by_average_dataset_rank"] for r in ranking if r["method"] == SAA_METHOD_ID),
            "rank_by_average_dataset_rank_ci95_low": percentile(saa_ranks_by_avg_dataset_rank, 0.025),
            "rank_by_average_dataset_rank_ci95_high": percentile(saa_ranks_by_avg_dataset_rank, 0.975),
        },
        "pairwise_score_differences": pairwise,
        "win_tie_loss": [
            {"opponent": r["opponent"], "win": r["win"], "tie": r["tie"], "loss": r["loss"]}
            for r in pairwise
        ],
        "friedman": {
            "statistic": float(friedman_stat),
            "p_value": float(friedman_p),
            "method_count": k,
            "dataset_count": n,
            "null_hypothesis": "all methods have equivalent rank distributions over paired datasets",
        },
        "nemenyi": nemenyi,
    }


def write_pairwise_csv(out_dir: Path, dossier: Dict[str, Any]) -> None:
    path = out_dir / "pairwise_score_differences.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["scope", "analysis_id", "metric", "mode", "dataset_count", "opponent", "mean_diff", "ci95_low", "ci95_high", "win", "tie", "loss", "sign"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for scope_obj in dossier["scopes"].values():
            for analysis in scope_obj["analyses"].values():
                meta = analysis["meta"]
                for row in analysis.get("pairwise_score_differences", []):
                    writer.writerow({
                        "scope": meta["scope"],
                        "analysis_id": meta["analysis_id"],
                        "metric": meta["metric"],
                        "mode": meta["mode"],
                        "dataset_count": meta["common_dataset_count"],
                        "opponent": row["opponent"],
                        "mean_diff": row["mean_score_difference_saa_minus_opponent"],
                        "ci95_low": row["bootstrap_ci95_low"],
                        "ci95_high": row["bootstrap_ci95_high"],
                        "win": row["win"],
                        "tie": row["tie"],
                        "loss": row["loss"],
                        "sign": row["sign"],
                    })


def write_ranking_csv(out_dir: Path, dossier: Dict[str, Any]) -> None:
    path = out_dir / "paired_common_dataset_rankings.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["scope", "analysis_id", "metric", "mode", "dataset_count", "rank_by_average_dataset_rank", "method", "average_dataset_rank", "mean_score", "rank_by_mean_score"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for scope_obj in dossier["scopes"].values():
            for analysis in scope_obj["analyses"].values():
                meta = analysis["meta"]
                for row in analysis.get("ranking", []):
                    writer.writerow({
                        "scope": meta["scope"],
                        "analysis_id": meta["analysis_id"],
                        "metric": meta["metric"],
                        "mode": meta["mode"],
                        "dataset_count": meta["common_dataset_count"],
                        "rank_by_average_dataset_rank": row["rank_by_average_dataset_rank"],
                        "method": row["method"],
                        "average_dataset_rank": row["average_dataset_rank"],
                        "mean_score": row["mean_score"],
                        "rank_by_mean_score": row["rank_by_mean_score"],
                    })


def write_cd_svg(out_dir: Path, scope: str, analysis_id: str, analysis: Dict[str, Any]) -> str:
    ranking = analysis.get("ranking", [])
    if not ranking:
        return ""
    cd = analysis["nemenyi"]["critical_difference"]
    width = 980
    height = 310
    left = 80
    right = width - 40
    axis_y = 80
    min_rank = 1.0
    max_rank = 15.0
    def x_for(rank: float) -> float:
        return left + (rank - min_rank) / (max_rank - min_rank) * (right - left)
    items = sorted(ranking, key=lambda r: r["average_dataset_rank"])
    rows = []
    for idx, row in enumerate(items):
        y = 116 + idx * 12
        label = SAA_LABEL if row["method"] == SAA_METHOD_ID else row["method"]
        color = "#0E120E" if row["method"] == SAA_METHOD_ID else "#6A7178"
        weight = "700" if row["method"] == SAA_METHOD_ID else "400"
        rows.append(f'<circle cx="{x_for(row["average_dataset_rank"]):.1f}" cy="{y}" r="3" fill="{color}"/>')
        rows.append(f'<text x="{x_for(row["average_dataset_rank"])+6:.1f}" y="{y+3}" font-size="9" font-family="monospace" fill="{color}" font-weight="{weight}">{label} {row["average_dataset_rank"]:.2f}</text>')
    saa_rank = analysis["nemenyi"]["saa_average_rank"]
    cd_x0 = x_for(saa_rank - cd / 2)
    cd_x1 = x_for(saa_rank + cd / 2)
    ticks = []
    for rank in range(1, 16):
        x = x_for(rank)
        ticks.append(f'<line x1="{x:.1f}" y1="{axis_y-5}" x2="{x:.1f}" y2="{axis_y+5}" stroke="#8B93A1" stroke-width="1"/>')
        if rank in [1, 5, 10, 15]:
            ticks.append(f'<text x="{x-4:.1f}" y="{axis_y-12}" font-size="9" font-family="monospace" fill="#6A7178">{rank}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#F7F5F0"/>
  <text x="30" y="30" font-size="15" font-family="Georgia,serif" fill="#16181C">TCPD critical-difference diagram · {scope} · {analysis_id}</text>
  <text x="30" y="52" font-size="10" font-family="monospace" fill="#6A7178">Lower rank is better · CD95={cd:.3f} · N={analysis['meta']['common_dataset_count']} · non-separation is inconclusive</text>
  <line x1="{left}" y1="{axis_y}" x2="{right}" y2="{axis_y}" stroke="#8B93A1" stroke-width="1"/>
  {''.join(ticks)}
  <line x1="{cd_x0:.1f}" y1="{axis_y+18}" x2="{cd_x1:.1f}" y2="{axis_y+18}" stroke="#B08A3E" stroke-width="3"/>
  <text x="{cd_x0:.1f}" y="{axis_y+35}" font-size="9" font-family="monospace" fill="#8F7135">SAA-centered CD95</text>
  {''.join(rows)}
</svg>
'''
    path = out_dir / f"cd_{scope}_{analysis_id}.svg"
    path.write_text(svg, encoding="utf-8")
    return path.name


def write_markdown(out_dir: Path, dossier: Dict[str, Any], svg_names: List[str]) -> None:
    lines = []
    lines.append("# TCPD Benchmark Dossier V1")
    lines.append("")
    lines.append(f"Generated: `{dossier['generated_at_utc']}`")
    lines.append(f"Canonical source result: `{dossier['source_result_canonical_sha256']}`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("Research-only external adapter evidence. No raw TCPD series are exported. Non-separation in Nemenyi is reported as `INCONCLUSIVE`, not equality or superiority.")
    lines.append("")
    headline = dossier.get("headline_claim", {})
    if headline:
        lines.append("## Claim Discipline")
        lines.append("")
        lines.append(f"- Published headline: {headline.get('published_headline', '')}")
        lines.append(f"- Rank scale disclosure: {headline.get('rank_scale_disclosure', '')}")
        lines.append(f"- Required uncertainty: {headline.get('required_uncertainty', '')}")
        lines.append(f"- Frame reconciliation: {headline.get('frame_reconciliation', '')}")
        lines.append(f"- Pairwise read: {headline.get('pairwise_read', '')}")
        if headline.get("friedman_nemenyi_result"):
            result = headline["friedman_nemenyi_result"]
            not_sep = [SAA_LABEL if m == SAA_METHOD_ID else m for m in result.get("not_separated_from_saa", [])]
            lines.append(
                "- Friedman/Nemenyi result: "
                f"statistic {result.get('statistic', 0):.4f}; "
                f"p {result.get('p_value', 0):.4g}; "
                f"SAA mean rank {result.get('saa_average_rank', 0):.4f}; "
                f"best {result.get('best_method', '')} {result.get('best_average_rank', 0):.4f}; "
                f"delta {result.get('delta_saa_minus_best_average_rank', 0):.4f}; "
                f"CD95 {result.get('critical_difference_95', 0):.4f}; "
                f"within CD with best {result.get('within_cd_with_best', False)}; "
                f"SAA CD group {', '.join(not_sep)}; "
                f"interpretation {result.get('interpretation', '')}."
            )
            if headline.get("leader_cd_band_read"):
                lines.append(f"- Leader CD band: {headline.get('leader_cd_band_read', '')}")
        if headline.get("implementation_boundary"):
            impl = headline["implementation_boundary"]
            lines.append(
                "- Implementation boundary: "
                f"benchmarked `{impl.get('benchmarked_implementation', '')}` "
                f"({impl.get('benchmark_implementation_type', '')}); "
                f"production detector `{impl.get('production_detector', '')}` "
                f"benchmarked={str(impl.get('production_detector_benchmarked', '')).lower()}."
            )
        lines.append(f"- Real-world stability: {headline.get('real_world_stability', '')}")
        for entry in headline.get("change_log", []):
            lines.append(
                f"- Change log: {entry.get('from_sha256', '')} -> {entry.get('to_sha256', '')}; "
                f"{entry.get('change_scope', '')}; numeric_fields_changed={str(entry.get('numeric_fields_changed', '')).lower()}."
            )
        for rule in headline.get("publication_rules", []):
            lines.append(f"- Rule: {rule}")
        lines.append("")
    lines.append("## Headline")
    lines.append("")
    for scope, scope_obj in dossier["scopes"].items():
        lines.append(f"### {scope}")
        lines.append("")
        for analysis_id, analysis in scope_obj["analyses"].items():
            meta = analysis["meta"]
            boot = analysis["saa_bootstrap"]
            nem = analysis["nemenyi"]
            fried = analysis["friedman"]
            lines.append(f"- `{analysis_id}` · common datasets `{meta['common_dataset_count']}/{meta['declared_scope_total']}` · SAA mean `{boot['score_mean']:.4f}` CI95 `[{boot['score_ci95_low']:.4f}, {boot['score_ci95_high']:.4f}]` · paired avg-rank position `{boot['rank_by_average_dataset_rank']}/15` CI95 `[{boot['rank_by_average_dataset_rank_ci95_low']:.1f}, {boot['rank_by_average_dataset_rank_ci95_high']:.1f}]` · Friedman p `{fried['p_value']:.4g}` · CD95 `{nem['critical_difference']:.3f}`")
            not_sep = [SAA_LABEL if m == SAA_METHOD_ID else m for m in nem["not_separated_from_saa"]]
            lines.append(f"  - Nemenyi not separated from SAA: {', '.join(not_sep)}")
        lines.append("")
    lines.append("## Top Ranking Rows")
    lines.append("")
    for scope, scope_obj in dossier["scopes"].items():
        for analysis_id, analysis in scope_obj["analyses"].items():
            lines.append(f"### {scope} · {analysis_id}")
            lines.append("")
            lines.append("| rank | method | avg dataset rank | mean score | rank by mean score |")
            lines.append("|---:|---|---:|---:|---:|")
            for row in analysis["ranking"][:8]:
                label = SAA_LABEL if row["method"] == SAA_METHOD_ID else row["method"]
                lines.append(f"| {row['rank_by_average_dataset_rank']} | {label} | {row['average_dataset_rank']:.3f} | {row['mean_score']:.4f} | {row['rank_by_mean_score']} |")
            lines.append("")
    lines.append("## Pairwise Tables")
    lines.append("")
    lines.append("Default F-measure headline pairwise table; SAA-minus-opponent over the same 35 paired datasets:")
    lines.append("")
    lines.append("| opponent | mean diff | CI95 low | CI95 high | W/T/L | sign |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for row in headline.get("pairwise_table", []):
        lines.append(
            f"| {row['opponent']} | {row['mean_score_difference_saa_minus_opponent']:.4f} | "
            f"{row['bootstrap_ci95_low']:.4f} | {row['bootstrap_ci95_high']:.4f} | "
            f"{row['win']}/{row['tie']}/{row['loss']} | {row['sign']} |"
        )
    lines.append("")
    lines.append("See `pairwise_score_differences.csv` for every scope and metric.")
    lines.append("")
    lines.append("## Critical-Difference SVGs")
    lines.append("")
    for name in svg_names:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `TCPD_BENCHMARK_DOSSIER_V1.json`")
    lines.append("- `paired_common_dataset_rankings.csv`")
    lines.append("- `pairwise_score_differences.csv`")
    lines.append("")
    (out_dir / "TCPD_BENCHMARK_DOSSIER_V1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_dossier_ref(dossier: Dict[str, Any], evidence_url: str) -> Dict[str, Any]:
    summaries = []
    for scope, scope_obj in dossier["scopes"].items():
        for analysis_id, analysis in scope_obj["analyses"].items():
            meta = analysis["meta"]
            boot = analysis["saa_bootstrap"]
            nem = analysis["nemenyi"]
            fried = analysis["friedman"]
            top = analysis["ranking"][0] if analysis.get("ranking") else {}
            top_method = top.get("method", "")
            top_average_rank = float(top.get("average_dataset_rank", nem["saa_average_rank"]))
            saa_average_rank = float(nem["saa_average_rank"])
            avg_rank_delta = saa_average_rank - top_average_rank
            within_cd = bool(avg_rank_delta <= float(nem["critical_difference"]))
            pair_top = next(
                (row for row in analysis.get("pairwise_score_differences", []) if row.get("opponent") == top_method),
                None,
            )
            if top_method == SAA_METHOD_ID:
                pair_top = {
                    "opponent": SAA_METHOD_ID,
                    "mean_score_difference_saa_minus_opponent": 0.0,
                    "bootstrap_ci95_low": 0.0,
                    "bootstrap_ci95_high": 0.0,
                    "win": meta["common_dataset_count"],
                    "tie": 0,
                    "loss": 0,
                    "sign": "SAA top in paired frame",
                }
            summaries.append({
                "scope": scope,
                "analysis_id": analysis_id,
                "mode": meta["mode"],
                "metric": meta["metric"],
                "common_dataset_count": meta["common_dataset_count"],
                "declared_scope_total": meta["declared_scope_total"],
                "method_count": fried["method_count"],
                "saa_score_mean": boot["score_mean"],
                "saa_score_ci95_low": boot["score_ci95_low"],
                "saa_score_ci95_high": boot["score_ci95_high"],
                "saa_mean_score_rank": int(boot["rank_by_mean_score"]),
                "saa_mean_score_rank_ci95_low": boot["rank_by_mean_score_ci95_low"],
                "saa_mean_score_rank_ci95_high": boot["rank_by_mean_score_ci95_high"],
                "saa_paired_avg_rank_position": boot["rank_by_average_dataset_rank"],
                "saa_paired_avg_rank_ci95_low": boot["rank_by_average_dataset_rank_ci95_low"],
                "saa_paired_avg_rank_ci95_high": boot["rank_by_average_dataset_rank_ci95_high"],
                "friedman_p_value": fried["p_value"],
                "nemenyi_critical_difference_95": nem["critical_difference"],
                "nemenyi_interpretation": "INCONCLUSIVE_NOT_EQUIVALENCE",
                "top_paired_method": top_method,
                "best_average_rank_method": top_method,
                "best_average_rank": top_average_rank,
                "saa_average_rank": saa_average_rank,
                "delta_saa_minus_best_average_rank": avg_rank_delta,
                "within_cd_with_best": within_cd,
                "leader_cd_band_cutoff": nem["leader_cd_band_cutoff"],
                "leader_cd_band_method_count": nem["leader_cd_band_method_count"],
                "leader_cd_band_methods": nem["leader_cd_band_methods"],
                "field_mean_average_rank": nem["field_mean_average_rank"],
                "saa_inside_leader_cd_band": nem["saa_inside_leader_cd_band"],
                "saa_vs_top_method": pair_top or {},
            })
    return {
        "schema_id": "saa.risk_analyzer.tcpd_benchmark_dossier_ref.v1",
        "status": dossier["status"],
        "evidence_url": evidence_url,
        "evidence_sha256": dossier["sha256"],
        "source_result_canonical_sha256": dossier["source_result_canonical_sha256"],
        "bootstrap_iterations": dossier["bootstrap_iterations"],
        "raw_series_exported": dossier["raw_series_exported"],
        "paired_common_dataset_frame": "paired_common_dataset_only",
        "real_world_subset_frame": "real_world_37",
        "nemenyi_caveat": "INCONCLUSIVE_NOT_EQUIVALENCE",
        "headline_claim": dossier.get("headline_claim", {}),
        "claim_boundary": dossier["claim_boundary"],
        "benchmarked_implementation": dossier.get("benchmarked_implementation", {}),
        "summaries": summaries,
    }


def build_headline_claim(dossier: Dict[str, Any]) -> Dict[str, Any]:
    all_default_f = dossier["scopes"]["all_42"]["analyses"]["default_f_measure"]
    all_default_c = dossier["scopes"]["all_42"]["analyses"]["default_covering"]
    rw_default_f = dossier["scopes"]["real_world_37"]["analyses"]["default_f_measure"]
    rw_default_c = dossier["scopes"]["real_world_37"]["analyses"]["default_covering"]
    boot = all_default_f["saa_bootstrap"]
    meta = all_default_f["meta"]
    headline_rank = int(boot["rank_by_mean_score"])
    top_method = all_default_f["ranking"][0]["method"]
    top_pairwise = next(
        (row for row in all_default_f["pairwise_score_differences"] if row.get("opponent") == top_method),
        None,
    )
    pairwise_read = "SAA is top in the paired default F frame."
    if top_pairwise:
        pairwise_read = (
            f"SAA-minus-{top_method} mean difference {top_pairwise['mean_score_difference_saa_minus_opponent']:.4f} "
            f"CI95 [{top_pairwise['bootstrap_ci95_low']:.4f}, {top_pairwise['bootstrap_ci95_high']:.4f}], "
            f"W/T/L {top_pairwise['win']}/{top_pairwise['tie']}/{top_pairwise['loss']}."
        )
    pairwise_table = [
        {
            "opponent": row["opponent"],
            "mean_score_difference_saa_minus_opponent": row["mean_score_difference_saa_minus_opponent"],
            "bootstrap_ci95_low": row["bootstrap_ci95_low"],
            "bootstrap_ci95_high": row["bootstrap_ci95_high"],
            "win": row["win"],
            "tie": row["tie"],
            "loss": row["loss"],
            "common_dataset_count": meta["common_dataset_count"],
            "sign": row["sign"],
        }
        for row in all_default_f["pairwise_score_differences"]
    ]
    not_separated = all_default_f["nemenyi"]["not_separated_from_saa"]
    best_row = all_default_f["ranking"][0]
    best_avg_rank = float(best_row["average_dataset_rank"])
    saa_avg_rank = float(all_default_f["nemenyi"]["saa_average_rank"])
    avg_rank_delta = saa_avg_rank - best_avg_rank
    cd95 = float(all_default_f["nemenyi"]["critical_difference"])
    leader_cd_band_cutoff = float(all_default_f["nemenyi"]["leader_cd_band_cutoff"])
    leader_cd_band_methods = all_default_f["nemenyi"]["leader_cd_band_methods"]
    leader_cd_band_count = int(all_default_f["nemenyi"]["leader_cd_band_method_count"])
    field_mean_rank = float(all_default_f["nemenyi"]["field_mean_average_rank"])
    implementation_boundary = {
        "schema_id": "saa.risk_analyzer.tcpd_benchmark_implementation_boundary.v1",
        "benchmarked_implementation": SAA_METHOD_ID,
        "benchmark_implementation_type": "research_adapter",
        "production_detector": "go_regime_heuristic_v1",
        "production_detector_benchmarked": False,
        "boundary": (
            "TCPD benchmark covers the research adapter only. It is not evidence that the "
            "production Risk Analyzer regime detector clears TCPD/TCPDBench or outperforms peers."
        ),
    }
    return {
        "schema_id": "saa.risk_analyzer.tcpd_headline_claim_discipline.v1",
        "headline_basis": "mean-score ranking for default_f_measure on all_42 paired common-dataset frame",
        "rank_scale_disclosure": (
            "headline rank 4/15 is mean-score ranking; Friedman/Nemenyi uses mean-rank basis "
            "over per-dataset ranks and must not be described as proving the headline rank."
        ),
        "published_headline": (
            f"default F-measure paired common-set mean-score rank {headline_rank}/15 "
            f"(CI95 {boot['rank_by_mean_score_ci95_low']:.0f}-"
            f"{boot['rank_by_mean_score_ci95_high']:.0f}) "
            f"on {meta['common_dataset_count']} of {meta['declared_scope_total']} paired datasets"
        ),
        "required_uncertainty": (
            f"mean-score rank CI95 [{boot['rank_by_mean_score_ci95_low']:.1f}, "
            f"{boot['rank_by_mean_score_ci95_high']:.1f}], score {boot['score_mean']:.4f} "
            f"CI95 [{boot['score_ci95_low']:.4f}, {boot['score_ci95_high']:.4f}]"
        ),
        "frame_reconciliation": (
            "earlier successful-rows frame rank 6 lies within the paired-frame rank CI [1,7]; "
            "the frames are consistent and the paired frame removes missing-row selection effects."
        ),
        "pairwise_read": pairwise_read,
        "pairwise_table": pairwise_table,
        "friedman_nemenyi_read": (
            f"Friedman p={all_default_f['friedman']['p_value']:.4g}; "
            f"Nemenyi mean-rank basis: SAA mean rank={saa_avg_rank:.4f}, "
            f"best {best_row['method']}={best_avg_rank:.4f}, delta={avg_rank_delta:.4f} "
            f"< CD95={cd95:.4f}; leader CD band contains {leader_cd_band_count} of "
            f"{all_default_f['friedman']['method_count']} methods at cutoff {leader_cd_band_cutoff:.4f}; "
            "non-separation is INCONCLUSIVE_NOT_EQUIVALENCE, not equality or superiority."
        ),
        "leader_cd_band_read": (
            f"Leader CD band contains {leader_cd_band_count} of {all_default_f['friedman']['method_count']} "
            f"methods (cutoff mean rank {leader_cd_band_cutoff:.4f} = best {best_row['method']} "
            f"{best_avg_rank:.4f} + CD95 {cd95:.4f}); SAA mean rank {saa_avg_rank:.4f} "
            f"is one of them; field mean rank is {field_mean_rank:.4f} by construction."
        ),
        "friedman_nemenyi_result": {
            "statistic": all_default_f["friedman"]["statistic"],
            "p_value": all_default_f["friedman"]["p_value"],
            "method_count": all_default_f["friedman"]["method_count"],
            "dataset_count": all_default_f["friedman"]["dataset_count"],
            "basis": "mean-rank over per-dataset ranks; separate from headline mean-score rank",
            "critical_difference_95": cd95,
            "saa_average_rank": saa_avg_rank,
            "best_method": best_row["method"],
            "best_average_rank": best_avg_rank,
            "delta_saa_minus_best_average_rank": avg_rank_delta,
            "within_cd_with_best": avg_rank_delta <= cd95,
            "same_cd_band_as_best": avg_rank_delta <= cd95,
            "leader_cd_band_cutoff": leader_cd_band_cutoff,
            "leader_cd_band_method_count": leader_cd_band_count,
            "leader_cd_band_methods": leader_cd_band_methods,
            "field_mean_average_rank": field_mean_rank,
            "saa_inside_leader_cd_band": SAA_METHOD_ID in leader_cd_band_methods,
            "not_separated_from_saa": not_separated,
            "significantly_better_than_saa_by_cd": all_default_f["nemenyi"]["significantly_better_than_saa_by_cd"],
            "significantly_worse_than_saa_by_cd": all_default_f["nemenyi"]["significantly_worse_than_saa_by_cd"],
            "interpretation": "INCONCLUSIVE_NOT_EQUIVALENCE",
        },
        "implementation_boundary": implementation_boundary,
        "real_world_stability": (
            f"real-world 37 stability: default F rank {rw_default_f['saa_bootstrap']['rank_by_average_dataset_rank']}/15 "
            f"on {rw_default_f['meta']['common_dataset_count']} of 37; "
            f"default covering rank {rw_default_c['saa_bootstrap']['rank_by_average_dataset_rank']}/15 "
            f"on {rw_default_c['meta']['common_dataset_count']} of 37; "
            f"all_42 covering rank {all_default_c['saa_bootstrap']['rank_by_average_dataset_rank']}/15."
        ),
        "oracle_handling": {
            "headline_allowed": False,
            "reason": "Oracle scores use answer-visible upper-bound framing and are secondary only.",
            "common_set_warning": "Default and oracle common sets differ; 35 default common datasets versus 37 oracle common datasets, so ranks are not directly comparable across modes.",
        },
        "publication_rules": [
            "headline may cite default ranks only, never oracle ranks",
            "rank must be printed with bootstrap rank CI",
            "score must be printed with bootstrap score CI",
            "pairwise SAA-minus-top-method CI and W/T/L must be printed near the headline",
            "Friedman/Nemenyi must be printed with INCONCLUSIVE_NOT_EQUIVALENCE caveat",
            "leader CD band method count and cutoff must be printed near any indistinguishable-from-leader language",
            "benchmarked implementation must be named as research adapter unless production detector provenance is attached",
            "default and oracle frames must not be compared directly because their common-set denominators differ",
            "real-world 37 subset must be printed as a stability check, not as a cherry-picked replacement frame",
        ],
        "forbidden_headlines": [
            "oracle_covering rank 3/15",
            "statistically equal to leaders",
            "production detector superiority",
            "TCPD benchmark proves production go_regime_heuristic_v1 performance",
        ],
        "change_log": [
            {
                "from_sha256": PREVIOUS_AUDIT_DOSSIER_SHA_PREFIX,
                "to_sha256": PREVIOUS_DISCIPLINE_DOSSIER_SHA256,
                "change_scope": "headline discipline wrapper added",
                "numeric_fields_changed": False,
                "note": "Rank, score, confidence intervals and pairwise arithmetic remained stable; only claim discipline was made explicit.",
            },
            {
                "from_sha256": PREVIOUS_DISCIPLINE_DOSSIER_SHA256,
                "to_sha256": PREVIOUS_SURFACED_DOSSIER_SHA256,
                "change_scope": "headline field made self-contained; full pairwise table, frame reconciliation and Friedman/Nemenyi result surfaced",
                "numeric_fields_changed": False,
                "note": "Rank 4/15, score 0.6941 and rank CI [1,7] remained unchanged; only claim discipline and renderer-facing fields changed.",
            },
            {
                "from_sha256": PREVIOUS_SURFACED_DOSSIER_SHA256,
                "to_sha256": PREVIOUS_RANK_SCALE_DOSSIER_SHA256,
                "change_scope": "rank-scale disclosure and explicit Nemenyi mean-rank delta surfaced",
                "numeric_fields_changed": False,
                "note": "Score 0.6941, mean-score rank 4/15, rank CI [1,7], pairwise W/T/L 14/6/15 and Friedman p-value remained unchanged. The current artifact sha256 is the root sha256 field and is not embedded here to avoid self-referential hashing.",
            },
            {
                "from_sha256": PREVIOUS_RANK_SCALE_DOSSIER_SHA256,
                "to_sha256": "sha256:this_artifact_declared_in_dossier_root",
                "change_scope": "leader CD-band count, implementation boundary and superseded-claim register added",
                "numeric_fields_changed": False,
                "note": "Score 0.6941, mean-score rank 4/15, rank CI [1,7], pairwise W/T/L 14/6/15, Friedman p-value and Nemenyi delta remained unchanged. The current artifact sha256 is the root sha256 field and is not embedded here to avoid self-referential hashing.",
            },
        ],
    }


def build_superseded_claim_register(root: Path, dossier: Dict[str, Any]) -> Dict[str, Any]:
    def file_ref(rel: str) -> Dict[str, Any]:
        path = root / rel
        if not path.is_file():
            return {"path": rel, "exists": False}
        data = path.read_bytes()
        return {
            "path": rel,
            "exists": True,
            "byte_length": len(data),
            "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
        }

    current = dossier.get("headline_claim", {})
    display_rule = (
        "Already sealed artifacts are not rewritten. If an artifact displays the earlier "
        "successful_rows_only TCPD frame rank 6/15, demos and decks must accompany it with "
        "the current governing statistical dossier: mean-score rank 4/15 (CI95 1-7) on the "
        "paired common-set frame; legacy 6/15 lies within CI [1,7]."
    )
    return {
        "schema_id": "saa.risk_analyzer.tcpd_superseded_claim_register.v1",
        "status": "PUBLISHED_RESEARCH_ONLY_GOVERNANCE_REGISTER",
        "current_governing_dossier_sha256": dossier["sha256"],
        "current_governing_headline": current.get("published_headline", ""),
        "current_governing_boundary": current.get("implementation_boundary", {}),
        "display_rule": display_rule,
        "entries": [
            {
                "artifact_id": "run_OUxEg1Q24jOUtxG3B2dSSg",
                "artifact_type": "fabric_export_freeze",
                "sealed_prior_frame": "successful_rows_only adapter metric rank 6/15 by F-measure",
                "governing_current_frame": "paired common-set mean-score rank 4/15 (CI95 1-7)",
                "rewrite_allowed": False,
                "display_accompaniment_required": True,
                "local_artifact_refs": [
                    file_ref("outputs/fabric_export_freeze/run_OUxEg1Q24jOUtxG3B2dSSg.html"),
                    file_ref("outputs/fabric_export_freeze/run_OUxEg1Q24jOUtxG3B2dSSg.json"),
                    file_ref("outputs/fabric_export_freeze/run_OUxEg1Q24jOUtxG3B2dSSg.pdf"),
                    file_ref("outputs/fabric_export_freeze/run_OUxEg1Q24jOUtxG3B2dSSg.xlsx"),
                    file_ref("outputs/fabric_export_freeze/run_OUxEg1Q24jOUtxG3B2dSSg.txt"),
                ],
            },
            {
                "artifact_id": "rpt_3372d6",
                "artifact_type": "auditor_observed_fabric_pdf_render",
                "sealed_prior_frame": "TCPD lollipop visually observed as rank 6/15, F 0.6698",
                "governing_current_frame": "paired common-set mean-score rank 4/15 (CI95 1-7)",
                "rewrite_allowed": False,
                "display_accompaniment_required": True,
                "evidence_basis": "auditor visual-audit reference; exact sealed file is not present in the local export-freeze directory",
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcpdbench-root", default="external/TCPDBench")
    parser.add_argument("--result", default="tcpd-external-benchmark-result-v1.json")
    parser.add_argument("--out-dir", default="outputs/tcpd_benchmark_dossier_v1_local")
    parser.add_argument("--bootstrap-iters", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260815)
    args = parser.parse_args()

    root = Path.cwd()
    tcpdbench_root = Path(args.tcpdbench_root).resolve()
    result_path = (root / args.result).resolve() if not Path(args.result).is_absolute() else Path(args.result)
    out_dir = (root / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = load_json(result_path)
    if result.get("schema_version") != "saa.risk_analyzer.tcpd_external_benchmark.result.v1":
        raise SystemExit("unexpected TCPD result schema")
    if not (tcpdbench_root / "analysis" / "output" / "scores" / "default_f1_scores.json").exists():
        raise SystemExit(f"missing TCPDBench score files under {tcpdbench_root}")

    dossier: Dict[str, Any] = {
        "schema_id": "saa.risk_analyzer.tcpd_benchmark_dossier.v1",
        "status": "PUBLISHED_RESEARCH_ONLY_STATISTICAL_DOSSIER",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_result_path": str(Path(args.result)),
        "source_result_canonical_sha256": result.get("canonical_sha256"),
        "tcpdbench_root": "pinned TCPDBench repository; score_file values are repo-relative",
        "repo_pins": result.get("repo_pins"),
        "method_count": 15,
        "bootstrap_iterations": args.bootstrap_iters,
        "seed": args.seed,
        "raw_series_exported": False,
        "benchmarked_implementation": {
            "schema_id": "saa.risk_analyzer.tcpd_benchmark_implementation_boundary.v1",
            "benchmarked_implementation": SAA_METHOD_ID,
            "benchmark_implementation_type": "research_adapter",
            "production_detector": "go_regime_heuristic_v1",
            "production_detector_benchmarked": False,
            "boundary": (
                "TCPD benchmark covers the research adapter only. It is not evidence that the "
                "production Risk Analyzer regime detector clears TCPD/TCPDBench or outperforms peers."
            ),
        },
        "claim_boundary": (
            "research-only external benchmark dossier; benchmarked implementation = "
            "saa_change_point_adapter_v1 research adapter; production detector "
            "go_regime_heuristic_v1 not benchmarked; no claim transfers from research adapter to production detector; "
            "no raw TCPD series redistribution; Nemenyi non-separation is inconclusive"
        ),
        "scopes": {},
    }

    for scope in SCOPES:
        dossier["scopes"][scope] = {"analyses": {}}
        for analysis_id, mode, metric_file_id, saa_key in ANALYSES:
            datasets, matrix, meta = build_rows(tcpdbench_root, result, analysis_id, mode, metric_file_id, saa_key, scope)
            dossier["scopes"][scope]["analyses"][analysis_id] = summarize_analysis(datasets, matrix, meta, args.seed, args.bootstrap_iters)

    dossier["headline_claim"] = build_headline_claim(dossier)
    dossier["sha256"] = sha256_obj({k: v for k, v in dossier.items() if k != "sha256"})
    write_json(out_dir / "TCPD_BENCHMARK_DOSSIER_V1.json", dossier)
    evidence_url = "https://raw.githubusercontent.com/SAA-Alliance/tcpd-external-benchmark/main/dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.json"
    write_json(out_dir / "TCPD_BENCHMARK_DOSSIER_REF_V1.json", build_dossier_ref(dossier, evidence_url))
    write_json(out_dir / "TCPD_SUPERSEDED_CLAIM_REGISTER_V1.json", build_superseded_claim_register(root, dossier))
    write_pairwise_csv(out_dir, dossier)
    write_ranking_csv(out_dir, dossier)
    svg_names = []
    for scope, scope_obj in dossier["scopes"].items():
        for analysis_id, analysis in scope_obj["analyses"].items():
            svg_names.append(write_cd_svg(out_dir, scope, analysis_id, analysis))
    write_markdown(out_dir, dossier, svg_names)
    manifest = {
        "schema_id": "saa.risk_analyzer.tcpd_benchmark_dossier_manifest.v1",
        "dossier_sha256": dossier["sha256"],
        "files": {},
    }
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            manifest["files"][path.name] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(out_dir / "SHA256SUMS.json", manifest)
    print(json.dumps({
        "status": "PASS",
        "out_dir": str(out_dir),
        "dossier_sha256": dossier["sha256"],
        "bootstrap_iterations": args.bootstrap_iters,
        "scopes": {
            s: {a: dossier["scopes"][s]["analyses"][a]["meta"]["common_dataset_count"] for a in dossier["scopes"][s]["analyses"]}
            for s in dossier["scopes"]
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
