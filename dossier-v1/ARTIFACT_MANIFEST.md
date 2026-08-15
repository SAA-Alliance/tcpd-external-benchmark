# Artifact Manifest

The files below are the GitHub publication package for `saa.risk_analyzer.tcpd_benchmark_dossier.v1`.

Primary dossier:

- `dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.json`
- `dossier-v1/TCPD_BENCHMARK_DOSSIER_REF_V1.json`
- `dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.md`
- `dossier-v1/TCPD_SUPERSEDED_CLAIM_REGISTER_V1.json`

Tables and diagrams:

- `dossier-v1/paired_common_dataset_rankings.csv`
- `dossier-v1/pairwise_score_differences.csv`
- `dossier-v1/cd_all_42_default_f_measure.svg`
- `dossier-v1/cd_all_42_default_covering.svg`
- `dossier-v1/cd_all_42_oracle_f_measure.svg`
- `dossier-v1/cd_all_42_oracle_covering.svg`
- `dossier-v1/cd_real_world_37_default_f_measure.svg`
- `dossier-v1/cd_real_world_37_default_covering.svg`
- `dossier-v1/cd_real_world_37_oracle_f_measure.svg`
- `dossier-v1/cd_real_world_37_oracle_covering.svg`

Checksums:

- `dossier-v1/SHA256SUMS.json`

Publication boundary:

- raw TCPD time series are not included;
- Nemenyi non-separation is marked `INCONCLUSIVE_NOT_EQUIVALENCE`;
- this package is research-only and does not publish production-detector performance evidence;
- benchmarked implementation is `saa_change_point_adapter_v1` research adapter; production detector `go_regime_heuristic_v1` benchmarked=`false`;
- default headline rank `4/15` is a mean-score ranking and is valid only with rank CI, score CI, pairwise W/T/L and explicit separation from Friedman/Nemenyi's mean-rank basis;
- Friedman/Nemenyi mean-rank result for the headline frame: SAA `5.6143`, best `binseg` `4.5000`, delta `1.1143 < CD95 3.6254`, interpretation `INCONCLUSIVE_NOT_EQUIVALENCE`;
- leader CD band contains `9 of 15` methods at cutoff `8.1254`;
- already sealed Fabric artifacts carrying the old `6/15` successful_rows_only frame are governed by `TCPD_SUPERSEDED_CLAIM_REGISTER_V1.json` and are not rewritten;
- oracle ranks are secondary only; `oracle_covering rank 3/15` is forbidden as a headline.
