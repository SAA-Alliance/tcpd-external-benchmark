# SAA TCPD/TCPDBench External Benchmark Evidence

This repository publishes the SAA change-point adapter v1 benchmark evidence for TCPD/TCPDBench.

The purpose is external replayability: reviewers can download the pinned upstream TCPD/TCPDBench repositories, take the detected change-point positions published here, and rerun the authors' `metrics.py` scoring code without using SAA infrastructure or SAA production code.

## Claim Boundary

This is research-only external benchmark evidence for `saa_change_point_adapter_v1`.

It is not a production Risk Analyzer regime-detector claim. It is not a production-detector superiority claim. TCPD is not a financial risk dataset. This does not provide market-risk regime validation, Decision Grade, trading advice, or execution authority.

No raw TCPD time-series data is redistributed in this repository. Download source data from the pinned upstream repositories.

## Published Artifacts

| File | Purpose |
|---|---|
| `tcpd-external-benchmark-result-v1.json` | Service-owned benchmark result, claim boundary, scores, rank frames, repository pins, harness validation, and canonical result hash. |
| `tcpd-external-benchmark-predictions-v1.json` | Public answer sheet: 0-indexed detected change-point positions for all 42 TCPD series. |
| `run_tcpd_external_benchmark.py` | Research adapter runner used to generate the artifact. This is adapter v1, not the production Risk Analyzer detector. |
| `SHA256SUMS` | Byte-level hashes for repository artifacts. |
| `artifact-manifest.json` | Human-readable artifact inventory with canonical and byte hashes. |

## Result Summary

Primary fair-ranking frame: `successful_rows_only`.

| Mode | F-measure | F rank | Covering | Covering rank | Basis |
|---|---:|---:|---:|---:|---|
| default | 0.6698418264688435 | 6 / 15 | 0.6223783853774185 | 6 / 15 | Adapter default research row. |
| oracle | 0.8644621329403449 | 6 / 15 | 0.7764204479263613 | 7 / 15 | Secondary upper-bound from deterministic parameter grid. |

Sensitivity frame: `all_series_null_as_zero` is published only as sensitivity. It must not be used as the headline result.

## Dataset Wording

TCPD contains 42 series in this run: 37 real-world series plus 5 synthetic quality-control series.

The repository does not include raw TCPD files and does not include pointwise charts for restricted series. Published values are detected change-point positions only.

## Pinned Upstream Inputs

| Repository | Commit |
|---|---|
| TCPD | `e8f19a3635e3b7f1a8aff59ce7f4d9bea17525c0` |
| TCPDBench | `167210005c09d2c44f9b2083b95f989a64be4b6b` |

## Canonical Hashes

| Object | SHA256 |
|---|---|
| Result canonical hash | `sha256:74a3cb1c150ed3a0c06177f1dec2fef69f9385d0c95b7c9345dcd78c85934222` |
| Predictions canonical hash | `sha256:10d8a913c9bcfc5a0a00a82fbc736013d712c066ceecbba4e39ea9318a7658b2` |

`SHA256SUMS` records byte-level file hashes. Canonical hashes are hashes of normalized objects declared inside the artifacts.

## External Replay Procedure

1. Clone the pinned upstream TCPD and TCPDBench repositories.
2. Read `tcpd-external-benchmark-predictions-v1.json`.
3. For each dataset, use the relevant `cplocations` array as the predicted change-point list.
4. Use TCPDBench `analysis/scripts/metrics.py` to compute F-measure and covering against the TCPDBench annotations.
5. Aggregate under the `successful_rows_only` ranking frame and compare against the result artifact.

Modes:

- `default`: one prediction list per dataset for both F-measure and covering.
- `oracle_f_measure`: oracle upper-bound list for F-measure.
- `oracle_covering`: oracle upper-bound list for covering.

## License

Repository contents are MIT licensed. Upstream TCPD/TCPDBench data and code are not redistributed here and remain under their own licenses.
