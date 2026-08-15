# Reproducibility Notes

Run the generator against a pinned local checkout of TCPDBench:

```bash
python3 scripts/build_tcpd_benchmark_dossier.py \
  --tcpdbench-root /path/to/TCPDBench \
  --bootstrap-iters 10000
```

The canonical published artifact is available on the SAA Analyzer prod host:

```bash
curl -sS https://analyzer.saa-alliance.com/tcpd-benchmark-dossier-v1/TCPD_BENCHMARK_DOSSIER_V1.json \
  | jq '{schema_id,status,sha256,raw_series_exported,bootstrap_iterations,headline:.headline_claim.published_headline,rank_ci:.headline_claim.required_uncertainty,pairwise:.headline_claim.pairwise_read,oracle_allowed:.headline_claim.oracle_handling.headline_allowed}'
```

Expected dossier SHA-256:

`sha256:5f9f2fb45c8a03f90720e1dd9abd7c313397add955a23532f28bbc8a35d11e32`

Expected headline discipline:

- `headline`: `default F-measure paired common-set mean-score rank 4/15 (CI95 1-7) on 35 of 42 paired datasets`
- `scale`: headline rank `4/15` is mean-score ranking; Friedman/Nemenyi uses mean-rank basis and is a separate statistical context.
- `rank_ci`: `mean-score rank CI95 [1.0, 7.0], score 0.6941 CI95 [0.6310, 0.7542]`
- `pairwise`: `SAA-minus-binseg mean difference -0.0503 CI95 [-0.1264, 0.0210], W/T/L 14/6/15.`
- `Friedman/Nemenyi`: SAA mean rank `5.6143`, best `binseg` mean rank `4.5000`, delta `1.1143 < CD95 3.6254`, interpretation `INCONCLUSIVE_NOT_EQUIVALENCE`.
- `oracle_allowed`: `false`

Expected change-log discipline:

- `91b38e1f -> bdf16c21 -> b19ff223 -> 5f9f2fb`.
- Score `0.6941`, mean-score rank `4/15`, rank CI `[1,7]`, W/T/L `14/6/15` and Friedman p-value did not change across the last three wrapper updates.
