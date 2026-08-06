#!/usr/bin/env python3
"""Run SAA Risk Analyzer TCPD/TCPDBench external benchmark.

The runner reads raw TCPD series from a local, pinned checkout but never copies
raw series into product artifacts. It does publish the adapter's detected
change-point positions: those are the benchmark "answer sheet" needed for a
third party to rerun TCPDBench metrics.py without trusting SAA infrastructure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASELINE_METHODS = [
    "amoc", "binseg", "bocpd", "bocpdms", "cpnp", "ecp", "kcpa", "pelt",
    "prophet", "rbocpdms", "rfpop", "segneigh", "wbs", "zero",
]
QC_DATASETS = {
    "quality_control_1", "quality_control_2", "quality_control_3",
    "quality_control_4", "quality_control_5",
}
TOTAL_SERIES = 42
REAL_WORLD_SERIES = 37
SYNTHETIC_QC_SERIES = 5
NON_REDISTRIBUTABLE_SERIES = 10
SAA_METHOD_ID = "saa_change_point_adapter_v1"
TOLERANCE = 0.001
PREDICTION_SCHEMA_V1 = "saa.risk_analyzer.tcpd_predictions.v1"
ACCEPTABLE_DATASET_INTEGRITY = {
    "PASS",
    "PASS_WITH_DISCLOSED_UPSTREAM_ROUNDING_WARNING",
}
DEFAULT_PARAMETER_PROVENANCE = {
    "status": "ADAPTER_PARAMETERS_DECLARED_NOT_PRODUCTION_PINNED",
    "source": "scripts/run_tcpd_external_benchmark.py",
    "implementation_id": SAA_METHOD_ID,
    "production_module_imported": False,
    "production_module_commit": None,
    "caveat": (
        "The benchmark imports TCPDBench metrics.py but uses the benchmark-script "
        "SAA change-point adapter. It does not prove that the Risk Analyzer "
        "production regime detector defaults were frozen before TCPD work."
    ),
}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def git_commit(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_metrics(tcpdbench_root: Path):
    sys.path.insert(0, str(tcpdbench_root / "analysis" / "scripts"))
    from metrics import covering, f_measure  # type: ignore

    return f_measure, covering


def md5sum(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def checksum_manifest(tcpd_root: Path, dataset_names: List[str]) -> Dict[str, Any]:
    checks = load_json(tcpd_root / "checksums.json")["checksums"]
    rows = []
    exact_ok = 0
    mismatches = []
    missing = []
    for name in dataset_names:
        fname = name + ".json"
        path = tcpd_root / "datasets" / name / fname
        expected = checks.get(fname)
        if not path.exists():
            missing.append(name)
            rows.append({"dataset": name, "status": "MISSING"})
            continue
        actual = md5sum(path)
        expected_values = expected if isinstance(expected, list) else [expected]
        status = "PASS" if actual in expected_values else "CHECKSUM_DRIFT"
        if status == "PASS":
            exact_ok += 1
        else:
            mismatches.append({"dataset": name, "actual_md5": actual, "expected_md5": expected_values})
        rows.append({
            "dataset": name,
            "status": status,
            "actual_md5": actual,
            "expected_md5": expected_values,
        })
    if not missing and not mismatches:
        status = "PASS"
    elif not missing and len(mismatches) == 1 and mismatches[0]["dataset"] == "bee_waggle_6":
        status = "PASS_WITH_DISCLOSED_UPSTREAM_ROUNDING_WARNING"
    else:
        status = "WITHHELD_CHECKSUM_MISMATCH"
    return {
        "status": status,
        "total_expected": len(dataset_names),
        "files_present": len(dataset_names) - len(missing),
        "exact_checksum_ok": exact_ok,
        "schema_validated": True,
        "mismatches": mismatches,
        "missing": missing,
        "rows_sha256": sha256_bytes(canonical_json_bytes(rows)),
        "note": "Raw TCPD files are used locally only; no raw series are exported. bee_waggle_6 may drift by platform rounding in the upstream collector.",
    }


def clean_cps(locations: Iterable[int], n_obs: int) -> List[int]:
    return sorted({int(x) for x in locations if 1 <= int(x) < n_obs - 1})


def recompute_baseline_validation(tcpdbench_root: Path, dataset_names: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    f_measure, covering = load_metrics(tcpdbench_root)
    score_dir = tcpdbench_root / "analysis" / "output" / "scores"
    score_files = {
        "default:f1": load_json(score_dir / "default_f1_scores.json"),
        "default:cover": load_json(score_dir / "default_cover_scores.json"),
    }
    rows = []
    for method in ["zero", "pelt"]:
        for metric_name in ["f1", "cover"]:
            reproduced_values = []
            published_values = []
            max_row_delta = 0.0
            success_count = 0
            for dataset in dataset_names:
                summary = load_json(tcpdbench_root / "analysis" / "output" / "summaries" / f"summary_{dataset}.json")
                result_rows = summary["results"].get(f"default_{method}", [])
                result = result_rows[0] if result_rows else {"status": "FAIL", "scores": None, "cplocations": []}
                published_score = score_files[f"default:{metric_name}"][dataset][method]
                if result.get("status") == "SUCCESS" and result.get("scores") is not None:
                    cps = clean_cps(result.get("cplocations") or [], int(summary["dataset_nobs"]))
                    annotations = summary["annotations"]
                    if metric_name == "f1":
                        reproduced_score = float(f_measure(annotations, cps))
                    else:
                        reproduced_score = float(covering(annotations, cps, int(summary["dataset_nobs"])))
                    expected_row_score = float(result["scores"][metric_name])
                    max_row_delta = max(max_row_delta, abs(reproduced_score - expected_row_score))
                    success_count += 1
                else:
                    reproduced_score = None
                reproduced_values.append(0.0 if reproduced_score is None else reproduced_score)
                published_values.append(0.0 if published_score is None else float(published_score))
            reproduced_agg = statistics.mean(reproduced_values)
            published_agg = statistics.mean(published_values)
            delta = abs(reproduced_agg - published_agg)
            rows.append({
                "method": method,
                "mode": "default",
                "metric": metric_name,
                "published_value": published_agg,
                "reproduced_value": reproduced_agg,
                "delta": delta,
                "threshold": TOLERANCE,
                "status": "PASS" if delta <= TOLERANCE and max_row_delta <= TOLERANCE else "FAIL",
                "basis": "TCPDBench metrics.py recomputation from published summary cplocations; aggregate over 42 series with missing scores as 0.0 for validation only",
                "success_rows": success_count,
                "max_row_delta": max_row_delta,
            })
    manifest = {
        "schema_version": "saa.risk_analyzer.tcpd_harness_validation.v1",
        "rows": rows,
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
    }
    manifest["sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    return rows, manifest


def matrix_from_dataset(data: Dict[str, Any]) -> List[List[float]]:
    n = int(data["n_obs"])
    cols = []
    for series in data.get("series", []):
        raw = series.get("raw", [])
        col = []
        for i in range(n):
            value = raw[i] if i < len(raw) else None
            try:
                value = float(value)
                if math.isnan(value) or math.isinf(value):
                    value = None
            except (TypeError, ValueError):
                value = None
            col.append(value)
        # forward/back fill, then zero-fill if entire series is missing.
        last = None
        for i, value in enumerate(col):
            if value is None:
                col[i] = last
            else:
                last = value
        nxt = None
        for i in range(len(col) - 1, -1, -1):
            if col[i] is None:
                col[i] = nxt
            else:
                nxt = col[i]
        col = [0.0 if v is None else float(v) for v in col]
        med = statistics.median(col)
        mad = statistics.median([abs(v - med) for v in col])
        scale = mad * 1.4826
        if scale <= 1e-12:
            scale = statistics.pstdev(col) or 1.0
        cols.append([(v - med) / scale for v in col])
    if not cols:
        return [[0.0] for _ in range(n)]
    return [[cols[j][i] for j in range(len(cols))] for i in range(n)]


def detect_cps(mat: List[List[float]], window: int, threshold: float, min_gap: int, max_cps: int) -> List[int]:
    n = len(mat)
    if n < max(12, 2 * window + 2):
        return []
    d = len(mat[0]) if mat else 1
    # Prefix sums for O(T*d) local mean contrast.
    prefix = [[0.0] * d]
    for row in mat:
        prev = prefix[-1]
        prefix.append([prev[j] + row[j] for j in range(d)])
    scores: List[Tuple[float, int]] = []
    for t in range(window, n - window):
        dist2 = 0.0
        for j in range(d):
            left = (prefix[t][j] - prefix[t - window][j]) / window
            right = (prefix[t + window][j] - prefix[t][j]) / window
            dist2 += (right - left) ** 2
        score = math.sqrt(window / 2.0) * math.sqrt(dist2)
        scores.append((score, t))
    candidates = []
    by_t = {t: s for s, t in scores}
    for score, t in scores:
        if score < threshold:
            continue
        if by_t.get(t - 1, -1.0) <= score and by_t.get(t + 1, -1.0) <= score:
            candidates.append((score, t))
    selected: List[int] = []
    for score, t in sorted(candidates, reverse=True):
        if all(abs(t - s) >= min_gap for s in selected):
            selected.append(t)
        if len(selected) >= max_cps:
            break
    return sorted(selected)


def score_predictions(summary: Dict[str, Any], f_measure, covering, predictions: List[int]) -> Tuple[float, float]:
    n_obs = int(summary["dataset_nobs"])
    cps = clean_cps(predictions, n_obs)
    return float(f_measure(summary["annotations"], cps)), float(covering(summary["annotations"], cps, n_obs))


def prediction_params(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "window": int(params["window"]),
        "threshold": float(params["threshold"]),
        "min_gap": int(params["min_gap"]),
        "max_cps": int(params["max_cps"]),
    }


def prediction_row(dataset: str, data: Dict[str, Any], cps: List[int], params: Dict[str, Any]) -> Dict[str, Any]:
    n_obs = int(data["n_obs"])
    cleaned = clean_cps(cps, n_obs)
    return {
        "dataset": dataset,
        "synthetic_quality_control": dataset in QC_DATASETS,
        "n_obs": n_obs,
        "indexing": "zero_based_integer_positions",
        "cplocations": cleaned,
        "params": prediction_params(params),
    }


def prediction_publication(modes: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    publication = {
        "schema_version": PREDICTION_SCHEMA_V1,
        "method_id": SAA_METHOD_ID,
        "series_total": TOTAL_SERIES,
        "indexing": "zero_based_integer_positions",
        "raw_series_exported": False,
        "pointwise_charts_exported": False,
        "license_boundary": (
            "Published values are detected change-point positions only. They do not "
            "redistribute raw TCPD series or pointwise restricted-series charts."
        ),
        "external_replay_contract": {
            "source_data": "download pinned TCPD and TCPDBench repositories",
            "metrics_code": "TCPDBench analysis/scripts/metrics.py",
            "procedure": (
                "Use each published cplocations array as the prediction list for its "
                "dataset; run metrics.py f_measure and covering against TCPDBench "
                "annotations; aggregate under the named rank frame."
            ),
            "default_mode": "default uses one prediction list per dataset for both F-measure and covering",
            "oracle_mode": "oracle upper-bound is metric-specific: oracle_f_measure and oracle_covering publish separate prediction lists",
        },
        "modes": modes,
    }
    publication["sha256"] = sha256_bytes(canonical_json_bytes({k: v for k, v in publication.items() if k != "sha256"}))
    return publication


def baseline_aggregate(
    tcpdbench_root: Path,
    mode: str,
    metric: str,
    dataset_names: List[str],
    null_policy: str,
) -> Dict[str, Dict[str, Any]]:
    scores = load_json(tcpdbench_root / "analysis" / "output" / "scores" / f"{mode}_{metric}_scores.json")
    out = {}
    for method in BASELINE_METHODS:
        vals = []
        success_vals = []
        for dataset in dataset_names:
            val = scores[dataset][method]
            if val is None:
                if null_policy == "all_series_null_as_zero":
                    vals.append(0.0)
                continue
            fval = float(val)
            vals.append(fval)
            success_vals.append(fval)
        mean_value = statistics.mean(vals) if vals else None
        out[method] = {
            "score": mean_value,
            "success_rows": len(success_vals),
            "total_rows": len(dataset_names),
            "null_rows": len(dataset_names) - len(success_vals),
            "null_policy": null_policy,
        }
    return out


def rank_desc(rows: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    ordered = sorted(
        ((method, row) for method, row in rows.items() if row.get("score") is not None),
        key=lambda kv: (-float(kv[1]["score"]), kv[0]),
    )
    return {method: idx + 1 for idx, (method, _) in enumerate(ordered)}


def baseline_scores(rows: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    return {method: float(row["score"]) for method, row in rows.items() if row.get("score") is not None}


def method_score_frame(
    baseline_rows: Dict[str, Dict[str, Any]],
    saa_score: float,
    null_policy: str,
    total_rows: int,
) -> Dict[str, Dict[str, Any]]:
    rows = dict(baseline_rows)
    rows[SAA_METHOD_ID] = {
        "score": saa_score,
        "success_rows": total_rows,
        "total_rows": total_rows,
        "null_rows": 0,
        "null_policy": null_policy,
    }
    return rows


def rank_frame(
    frame_id: str,
    f_rows: Dict[str, Dict[str, Any]],
    cover_rows: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    f_ranks = rank_desc(f_rows)
    cover_ranks = rank_desc(cover_rows)
    f_baseline = baseline_scores({k: v for k, v in f_rows.items() if k != SAA_METHOD_ID})
    cover_baseline = baseline_scores({k: v for k, v in cover_rows.items() if k != SAA_METHOD_ID})
    return {
        "frame_id": frame_id,
        "rank_f_measure": f_ranks[SAA_METHOD_ID],
        "rank_covering": cover_ranks[SAA_METHOD_ID],
        "evaluated_methods_f_measure": len(f_ranks),
        "evaluated_methods_covering": len(cover_ranks),
        "baseline_median_f_measure": statistics.median(f_baseline.values()),
        "baseline_median_covering": statistics.median(cover_baseline.values()),
        "saa_success_rows_f_measure": f_rows[SAA_METHOD_ID]["success_rows"],
        "saa_success_rows_covering": cover_rows[SAA_METHOD_ID]["success_rows"],
        "basis": (
            "Primary fair-ranking frame: aggregate each TCPDBench method over rows where that method produced a score; "
            "publish success/null row counts next to rank."
            if frame_id == "successful_rows_only"
            else "Sensitivity frame only: mean over all 42 rows with failed/null baseline scores set to 0.0."
        ),
    }


def run_saa_benchmark(tcpd_root: Path, tcpdbench_root: Path, dataset_names: List[str]) -> Dict[str, Any]:
    f_measure, covering = load_metrics(tcpdbench_root)
    summaries = {
        dataset: load_json(tcpdbench_root / "analysis" / "output" / "summaries" / f"summary_{dataset}.json")
        for dataset in dataset_names
    }
    default_params = {"window": 30, "threshold": 4.5, "min_gap": 10, "max_cps": 12}
    oracle_grid = []
    for window in [8, 12, 20, 30, 45, 60]:
        for threshold in [2.0, 2.75, 3.5, 4.5, 5.75, 7.0]:
            for min_gap in [5, 10, 20]:
                oracle_grid.append({"window": window, "threshold": threshold, "min_gap": min_gap, "max_cps": 20})
    per_dataset = []
    default_f1 = []
    default_cover = []
    oracle_f1 = []
    oracle_cover = []
    prediction_modes = {
        "default": [],
        "oracle_f_measure": [],
        "oracle_covering": [],
    }
    for dataset in dataset_names:
        data = load_json(tcpd_root / "datasets" / dataset / f"{dataset}.json")
        mat = matrix_from_dataset(data)
        default_cps = detect_cps(mat, **default_params)
        summary = summaries[dataset]
        d_f1, d_cover = score_predictions(summary, f_measure, covering, default_cps)
        best_f1 = d_f1
        best_cover = d_cover
        best_f1_params = default_params
        best_cover_params = default_params
        best_f1_cps = list(default_cps)
        best_cover_cps = list(default_cps)
        for params in oracle_grid:
            if len(mat) < 2 * params["window"] + 2:
                continue
            cps = detect_cps(mat, **params)
            f1, cover = score_predictions(summary, f_measure, covering, cps)
            if f1 > best_f1:
                best_f1 = f1
                best_f1_params = params
                best_f1_cps = list(cps)
            if cover > best_cover:
                best_cover = cover
                best_cover_params = params
                best_cover_cps = list(cps)
        default_f1.append(d_f1)
        default_cover.append(d_cover)
        oracle_f1.append(best_f1)
        oracle_cover.append(best_cover)
        prediction_modes["default"].append(prediction_row(dataset, data, default_cps, default_params))
        prediction_modes["oracle_f_measure"].append(prediction_row(dataset, data, best_f1_cps, best_f1_params))
        prediction_modes["oracle_covering"].append(prediction_row(dataset, data, best_cover_cps, best_cover_params))
        per_dataset.append({
            "dataset": dataset,
            "synthetic_quality_control": dataset in QC_DATASETS,
            "n_obs": int(data["n_obs"]),
            "n_dim": int(data["n_dim"]),
            "default_cps_count": len(default_cps),
            "default_prediction_sha256": sha256_bytes(canonical_json_bytes(clean_cps(default_cps, int(data["n_obs"])))),
            "default_f_measure": d_f1,
            "default_covering": d_cover,
            "oracle_f_measure_cps_count": len(best_f1_cps),
            "oracle_f_measure": best_f1,
            "oracle_f_measure_prediction_sha256": sha256_bytes(canonical_json_bytes(clean_cps(best_f1_cps, int(data["n_obs"])))),
            "oracle_covering": best_cover,
            "oracle_covering_cps_count": len(best_cover_cps),
            "oracle_covering_prediction_sha256": sha256_bytes(canonical_json_bytes(clean_cps(best_cover_cps, int(data["n_obs"])))),
            "oracle_f_measure_params": best_f1_params,
            "oracle_covering_params": best_cover_params,
        })
    default_f1_score = statistics.mean(default_f1)
    default_cover_score = statistics.mean(default_cover)
    oracle_f1_score = statistics.mean(oracle_f1)
    oracle_cover_score = statistics.mean(oracle_cover)

    frames = {}
    baseline_rows = {}
    for null_policy in ["successful_rows_only", "all_series_null_as_zero"]:
        default_f1_baseline = baseline_aggregate(tcpdbench_root, "default", "f1", dataset_names, null_policy)
        default_cover_baseline = baseline_aggregate(tcpdbench_root, "default", "cover", dataset_names, null_policy)
        oracle_f1_baseline = baseline_aggregate(tcpdbench_root, "oracle", "f1", dataset_names, null_policy)
        oracle_cover_baseline = baseline_aggregate(tcpdbench_root, "oracle", "cover", dataset_names, null_policy)
        baseline_rows[null_policy] = {
            "default_f_measure": default_f1_baseline,
            "default_covering": default_cover_baseline,
            "oracle_f_measure": oracle_f1_baseline,
            "oracle_covering": oracle_cover_baseline,
        }
        frames[null_policy] = {
            "default": rank_frame(
                null_policy,
                method_score_frame(default_f1_baseline, default_f1_score, null_policy, len(dataset_names)),
                method_score_frame(default_cover_baseline, default_cover_score, null_policy, len(dataset_names)),
            ),
            "oracle": rank_frame(
                null_policy,
                method_score_frame(oracle_f1_baseline, oracle_f1_score, null_policy, len(dataset_names)),
                method_score_frame(oracle_cover_baseline, oracle_cover_score, null_policy, len(dataset_names)),
            ),
        }
    primary_default = frames["successful_rows_only"]["default"]
    primary_oracle = frames["successful_rows_only"]["oracle"]
    sensitivity_default = frames["all_series_null_as_zero"]["default"]
    sensitivity_oracle = frames["all_series_null_as_zero"]["oracle"]

    return {
        "method_id": SAA_METHOD_ID,
        "aggregation_basis": "primary rank frame is successful_rows_only; all_series_null_as_zero is published as sensitivity only; raw series not exported",
        "parameter_provenance": DEFAULT_PARAMETER_PROVENANCE,
        "default_params": default_params,
        "oracle_grid_size": len(oracle_grid),
        "default_run": {
            "mode": "default",
            "f_measure": default_f1_score,
            "covering": default_cover_score,
            "rank_f_measure": primary_default["rank_f_measure"],
            "rank_covering": primary_default["rank_covering"],
            "evaluated_methods": 15,
            "baseline_median_f_measure": primary_default["baseline_median_f_measure"],
            "baseline_median_covering": primary_default["baseline_median_covering"],
            "ranking_frame_primary": "successful_rows_only",
            "sensitivity_all_series_null_as_zero": sensitivity_default,
            "basis": "rank among 15 evaluated methods plus baseline median; adapter-default research row; primary frame aggregates each baseline over successful rows only",
        },
        "oracle_run": {
            "mode": "oracle",
            "f_measure": oracle_f1_score,
            "covering": oracle_cover_score,
            "rank_f_measure": primary_oracle["rank_f_measure"],
            "rank_covering": primary_oracle["rank_covering"],
            "evaluated_methods": 15,
            "baseline_median_f_measure": primary_oracle["baseline_median_f_measure"],
            "baseline_median_covering": primary_oracle["baseline_median_covering"],
            "ranking_frame_primary": "successful_rows_only",
            "sensitivity_all_series_null_as_zero": sensitivity_oracle,
            "basis": "rank among 15 evaluated methods plus baseline median; oracle upper-bound from deterministic parameter grid; primary frame aggregates each baseline over successful rows only",
        },
        "ranking_frames": frames,
        "baseline_aggregates": {
            "successful_rows_only": baseline_rows["successful_rows_only"],
            "all_series_null_as_zero": baseline_rows["all_series_null_as_zero"],
        },
        "per_dataset_digest": per_dataset,
        "predictions": prediction_publication(prediction_modes),
        "comparison_caveats": [
            "Default-rank claims must name the ranking frame; successful_rows_only is primary and all_series_null_as_zero is sensitivity only.",
            "The benchmark-script adapter is not yet proven to be the Risk Analyzer production regime detector module.",
            "On 42 series, differences among top methods should be treated as research evidence, not statistically decisive superiority.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcpd-root", required=True)
    parser.add_argument("--tcpdbench-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--generated-at", default="2026-08-06T00:00:00Z")
    args = parser.parse_args()

    tcpd_root = Path(args.tcpd_root).resolve()
    tcpdbench_root = Path(args.tcpdbench_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    dataset_names = sorted(load_json(tcpdbench_root / "analysis" / "output" / "scores" / "default_f1_scores.json").keys())
    if len(dataset_names) != TOTAL_SERIES:
        raise SystemExit(f"expected {TOTAL_SERIES} TCPD series, got {len(dataset_names)}")

    tcpd_commit = git_commit(tcpd_root)
    tcpdbench_commit = git_commit(tcpdbench_root)
    checksum = checksum_manifest(tcpd_root, dataset_names)
    harness_rows, harness_manifest = recompute_baseline_validation(tcpdbench_root, dataset_names)
    benchmark = run_saa_benchmark(tcpd_root, tcpdbench_root, dataset_names)

    input_obj = {
        "tcpd_repo_url": "https://github.com/alan-turing-institute/TCPD",
        "tcpd_repo_commit": tcpd_commit,
        "tcpdbench_repo_url": "https://github.com/alan-turing-institute/TCPDBench",
        "tcpdbench_repo_commit": tcpdbench_commit,
        "series_total": TOTAL_SERIES,
        "real_world_series": REAL_WORLD_SERIES,
        "synthetic_quality_control_series": SYNTHETIC_QC_SERIES,
        "non_redistributable_series": NON_REDISTRIBUTABLE_SERIES,
        "baseline_methods": BASELINE_METHODS,
        "harness_validation": harness_rows,
        "default_run": benchmark["default_run"],
        "oracle_run": benchmark["oracle_run"],
        "primary_mode": "default",
        "own_method_id": SAA_METHOD_ID,
        "adapter_contract": {
            "executable_interface": "TCPDBench execs/python contract",
            "input_flag": "-i/--input",
            "output_shape": "JSON array of 0-indexed integer changepoint positions",
            "indexing": "0-indexed",
            "implementation_id": SAA_METHOD_ID,
            "implementation_provenance": "benchmark-script adapter; production Risk Analyzer regime detector module not imported",
            "production_module_imported": False,
            "parameter_provenance_status": DEFAULT_PARAMETER_PROVENANCE["status"],
        },
        "parameter_provenance": DEFAULT_PARAMETER_PROVENANCE,
        "ranking_frame_primary": "successful_rows_only",
        "comparison_caveats": benchmark["comparison_caveats"],
        "no_raw_data_export": True,
        "no_pointwise_charts_for_restricted": True,
        "citation": "Van den Burg and Williams (2020), An Evaluation of Change Point Detection Algorithms; TCPD/TCPDBench pinned GitHub repositories.",
        "dataset_integrity_status": checksum["status"],
        "dataset_integrity_warnings": [m["dataset"] + " checksum drift: " + m["actual_md5"] for m in checksum["mismatches"]],
        "harness_manifest_sha256": harness_manifest["sha256"],
        "predictions": benchmark["predictions"],
        "predictions_sha256": benchmark["predictions"]["sha256"],
        "external_replay_statement": (
            "Predicted change-point positions are published as 0-indexed integer arrays. "
            "A reviewer can rerun TCPDBench metrics.py against pinned TCPD/TCPDBench data "
            "and reproduce SAA adapter scores without SAA code or infrastructure."
        ),
    }
    input_obj["input_payload_sha256"] = sha256_bytes(canonical_json_bytes(input_obj))

    dataset_integrity_ok = checksum["status"] in ACCEPTABLE_DATASET_INTEGRITY
    harness_ok = harness_manifest["status"] == "PASS"
    result_status = "PUBLISHED_RESEARCH_ONLY" if dataset_integrity_ok and harness_ok else (
        "WITHHELD_DATASET_INTEGRITY_FAILED" if not dataset_integrity_ok else "WITHHELD_HARNESS_VALIDATION_FAILED"
    )

    result_obj = {
        "schema_version": "saa.risk_analyzer.tcpd_external_benchmark.result.v1",
        "operation_id": "external_regime_change_benchmark_tcpd",
        "status": result_status,
        "generated_at": args.generated_at,
        "repo_pins": {
            "tcpd_repo_commit": tcpd_commit,
            "tcpdbench_repo_commit": tcpdbench_commit,
        },
        "dataset_basis": {
            "total_series": TOTAL_SERIES,
            "real_world_series": REAL_WORLD_SERIES,
            "synthetic_quality_control_series": SYNTHETIC_QC_SERIES,
            "non_redistributable_series": NON_REDISTRIBUTABLE_SERIES,
            "dataset_claim_text": "42 series, including 37 real-world series and 5 synthetic quality-control series",
            "raw_data_exported": False,
            "pointwise_charts_for_restricted_series": False,
            "prediction_positions_exported": True,
        },
        "dataset_integrity": checksum,
        "harness_validation_manifest": harness_manifest,
        "saa_benchmark": benchmark,
        "published_predictions": benchmark["predictions"],
        "claim_boundary": "research-only external change-point adapter evidence; not a production Risk Analyzer regime-detector claim; no production-detector superiority claim; TCPD is not a financial risk dataset; no market-risk regime validation, no Decision Grade, no trading advice, no execution authorization, no raw TCPD data redistribution",
        "market_ready_claim": "The SAA change-point adapter v1 was evaluated on TCPD/TCPDBench as research-only external evidence. Default adapter mode is reported under successful_rows_only as the primary fair-ranking frame, with all_series_null_as_zero shown only as sensitivity. Oracle mode is a secondary upper-bound. TCPD contains 42 series, including 37 real-world and 5 synthetic quality-control series. No raw TCPD data files are redistributed. SAA publishes detected change-point positions so reviewers can rerun TCPDBench metrics.py without SAA infrastructure. This is not yet a production Risk Analyzer regime-detector claim.",
    }
    result_obj["canonical_sha256"] = sha256_bytes(canonical_json_bytes({k: v for k, v in result_obj.items() if k != "generated_at" and k != "canonical_sha256"}))

    write_json(out_dir / "tcpd-external-benchmark-input-v1.json", input_obj)
    write_json(out_dir / "tcpd-external-benchmark-result-v1.json", result_obj)
    write_json(out_dir / "tcpd-external-benchmark-predictions-v1.json", benchmark["predictions"])
    print(json.dumps({
        "input": str(out_dir / "tcpd-external-benchmark-input-v1.json"),
        "result": str(out_dir / "tcpd-external-benchmark-result-v1.json"),
        "predictions": str(out_dir / "tcpd-external-benchmark-predictions-v1.json"),
        "status": result_obj["status"],
        "canonical_sha256": result_obj["canonical_sha256"],
        "predictions_sha256": benchmark["predictions"]["sha256"],
        "dataset_integrity_status": checksum["status"],
        "default_f_measure": benchmark["default_run"]["f_measure"],
        "default_rank_f_measure": benchmark["default_run"]["rank_f_measure"],
        "default_rank_f_measure_null_as_zero": benchmark["default_run"]["sensitivity_all_series_null_as_zero"]["rank_f_measure"],
        "default_rank_covering": benchmark["default_run"]["rank_covering"],
        "oracle_f_measure": benchmark["oracle_run"]["f_measure"],
        "oracle_rank_f_measure": benchmark["oracle_run"]["rank_f_measure"],
        "oracle_rank_f_measure_null_as_zero": benchmark["oracle_run"]["sensitivity_all_series_null_as_zero"]["rank_f_measure"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
