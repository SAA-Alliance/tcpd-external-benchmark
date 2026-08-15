# Reproducibility Notes

Run the generator against a pinned local checkout of TCPDBench:

```bash
python3 scripts/build_tcpd_benchmark_dossier.py \
  --tcpdbench-root /path/to/TCPDBench \
  --bootstrap-iters 10000
```

The canonical published artifact is the GitHub package object; the command below reads the raw GitHub artifact, not the Analyzer service host:

```bash
curl -sS https://raw.githubusercontent.com/SAA-Alliance/tcpd-external-benchmark/main/dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.json \
  | jq '{schema_id,status,sha256,raw_series_exported,bootstrap_iterations,headline:.headline_claim.published_headline,rank_ci:.headline_claim.required_uncertainty,pairwise:.headline_claim.pairwise_read,leader:.headline_claim.leader_cd_band_read,implementation:.benchmarked_implementation,oracle_allowed:.headline_claim.oracle_handling.headline_allowed}'
```

Expected dossier SHA-256:

`sha256:222a1ba33ae20214efaa407de98d824031cf04b980d25c43cbdd76008bc9d43b`

Expected headline discipline:

- `headline`: `default F-measure paired common-set mean-score rank 4/15 (CI95 1-7) on 35 of 42 paired datasets`
- `scale`: headline rank `4/15` is mean-score ranking; Friedman/Nemenyi uses mean-rank basis and is a separate statistical context.
- `rank_ci`: `mean-score rank CI95 [1.0, 7.0], score 0.6941 CI95 [0.6310, 0.7542]`
- `pairwise`: `SAA-minus-binseg mean difference -0.0503 CI95 [-0.1264, 0.0210], W/T/L 14/6/15.`
- `Friedman/Nemenyi`: SAA mean rank `5.6143`, best `binseg` mean rank `4.5000`, delta `1.1143 < CD95 3.6254`, interpretation `INCONCLUSIVE_NOT_EQUIVALENCE`.
- `leader CD band`: `9 of 15` methods inside the leader band, cutoff `8.1254`.
- `implementation`: benchmarked implementation is `saa_change_point_adapter_v1` research adapter; production detector `go_regime_heuristic_v1` benchmarked=`false`.
- `oracle_allowed`: `false`

Expected change-log discipline:

- `91b38e1f -> bdf16c21 -> b19ff223 -> 5f9f2fb -> 222a1ba`.
- Score `0.6941`, mean-score rank `4/15`, rank CI `[1,7]`, W/T/L `14/6/15`, Friedman p-value and Nemenyi delta did not change across the wrapper updates.
