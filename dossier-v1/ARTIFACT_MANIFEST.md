# Artifact Manifest

The files below are the GitHub publication package for `saa.risk_analyzer.tcpd_benchmark_dossier.v1`.

Primary dossier:

- `artifacts/TCPD_BENCHMARK_DOSSIER_V1.json`
- `artifacts/TCPD_BENCHMARK_DOSSIER_REF_V1.json`
- `artifacts/TCPD_BENCHMARK_DOSSIER_V1.md`

Tables and diagrams:

- `artifacts/paired_common_dataset_rankings.csv`
- `artifacts/pairwise_score_differences.csv`
- `artifacts/cd_all_42_default_f_measure.svg`
- `artifacts/cd_all_42_default_covering.svg`
- `artifacts/cd_all_42_oracle_f_measure.svg`
- `artifacts/cd_all_42_oracle_covering.svg`
- `artifacts/cd_real_world_37_default_f_measure.svg`
- `artifacts/cd_real_world_37_default_covering.svg`
- `artifacts/cd_real_world_37_oracle_f_measure.svg`
- `artifacts/cd_real_world_37_oracle_covering.svg`

Checksums:

- `artifacts/SHA256SUMS.json`

Publication boundary:

- raw TCPD time series are not included;
- Nemenyi non-separation is marked `INCONCLUSIVE_NOT_EQUIVALENCE`;
- this package is research-only and does not publish a production detector superiority claim.
- default headline rank `4/15` is valid only with rank CI, score CI, pairwise W/T/L and Friedman/Nemenyi caveat;
- oracle ranks are secondary only; `oracle_covering rank 3/15` is forbidden as a headline.
