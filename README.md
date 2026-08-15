# SAA Risk Analyzer TCPD Benchmark Dossier V1

This repository publishes the hash-bound statistical dossier for the SAA Risk Analyzer TCPD external benchmark adapter.

## Status

`PUBLISHED_RESEARCH_ONLY_STATISTICAL_DOSSIER`

This is a research-only benchmark dossier. It is not a production detector superiority claim, not investment advice, and not an execution or allocation instruction.

## What Is Included

- Paired common-dataset rankings.
- Bootstrap confidence intervals with 10,000 resamples.
- Pairwise score differences and win/tie/loss tables.
- Friedman/Nemenyi multi-method comparison.
- Separate all-series and real-world-only TCPD scopes.
- Critical-difference SVG diagrams.
- Hash-bound JSON and CSV evidence artifacts.

## Canonical Evidence

Prod evidence URL:

https://analyzer.saa-alliance.com/tcpd-benchmark-dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.json

Dossier SHA-256:

`sha256:5f9f2fb45c8a03f90720e1dd9abd7c313397add955a23532f28bbc8a35d11e32`

Source result canonical SHA-256:

`sha256:74a3cb1c150ed3a0c06177f1dec2fef69f9385d0c95b7c9345dcd78c85934222`

## Boundaries

- No raw TCPD time series are redistributed here.
- No claim is made that non-separation under Nemenyi means equality or superiority.
- `INCONCLUSIVE_NOT_EQUIVALENCE` is the required interpretation of non-separated groups.
- The dossier is an evidence artifact for audit and reproducibility, not a live trading signal.

## Headline Claim Discipline

The only permitted headline is:

`default F-measure paired common-set mean-score rank 4/15 (CI95 1-7) on 35 of 42 paired datasets`

That headline must be printed with:

- score `0.6941 CI95 [0.6310, 0.7542]`;
- rank-scale disclosure: headline rank `4/15` is a mean-score ranking; Friedman/Nemenyi is a separate mean-rank basis over per-dataset ranks and must not be described as proving the headline rank;
- earlier successful-rows frame rank `6/15` lies inside the paired-frame rank CI `[1,7]`, so the frames are consistent;
- pairwise SAA-minus-binseg difference `-0.0503 CI95 [-0.1264, 0.0210]`, W/T/L `14/6/15`;
- full pairwise table covers all 14 opponents;
- Friedman/Nemenyi result on mean-rank basis: SAA mean rank `5.6143`, best `binseg` mean rank `4.5000`, delta `1.1143 < CD95 3.6254`, interpretation `INCONCLUSIVE_NOT_EQUIVALENCE`;
- real-world 37 stability check: default F rank `4/15` on `30 of 37`, default covering rank `5/15` on `30 of 37`;
- oracle ranks as secondary only. `oracle_covering rank 3/15` is explicitly forbidden as a headline.

## Dossier Change Log

- `sha256:91b38e1f` -> `sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08`: headline discipline wrapper added; numeric fields unchanged.
- `sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08` -> `sha256:b19ff223b7e7cf42def70dd5d9bedb70a01f9ce01411c55093bceb3fa1e2410a`: self-contained headline, pairwise table, frame reconciliation and Friedman/Nemenyi result surfaced; score `0.6941`, rank `4/15` and rank CI `[1,7]` unchanged.
- `sha256:b19ff223b7e7cf42def70dd5d9bedb70a01f9ce01411c55093bceb3fa1e2410a` -> `sha256:5f9f2fb45c8a03f90720e1dd9abd7c313397add955a23532f28bbc8a35d11e32`: rank-scale disclosure and explicit Nemenyi mean-rank delta surfaced; score `0.6941`, mean-score rank `4/15`, rank CI `[1,7]`, W/T/L `14/6/15` and Friedman p-value unchanged.

## Source Pins

The dossier was generated from pinned upstream sources recorded inside the JSON artifact:

- TCPDBench commit: `167210005c09d2c44f9b2083b95f989a64be4b6b`
- TCPD commit: `e8f19a3635e3b7f1a8aff59ce7f4d9bea17525c0`

## Main Files

- `artifacts/TCPD_BENCHMARK_DOSSIER_V1.json` - canonical statistical dossier object.
- `artifacts/TCPD_BENCHMARK_DOSSIER_REF_V1.json` - compact reference embedded by Risk Analyzer/Fabric.
- `artifacts/TCPD_BENCHMARK_DOSSIER_V1.md` - human-readable dossier.
- `artifacts/paired_common_dataset_rankings.csv` - method rankings by scope/metric.
- `artifacts/pairwise_score_differences.csv` - pairwise deltas and W/T/L rows.
- `artifacts/cd_*.svg` - critical-difference diagrams.
- `artifacts/SHA256SUMS.json` - artifact checksums.
- `scripts/build_tcpd_benchmark_dossier.py` - generator used to produce the dossier.
