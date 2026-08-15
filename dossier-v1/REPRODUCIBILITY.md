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

`sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08`

Expected headline discipline:

- `headline`: `default F-measure paired common-set rank 4/15 on 35 of 42 datasets`
- `rank_ci`: `rank CI95 [1.0, 7.0], score 0.6941 CI95 [0.6310, 0.7542]`
- `pairwise`: `SAA-minus-binseg mean difference -0.0503 CI95 [-0.1264, 0.0210], W/T/L 14/6/15.`
- `oracle_allowed`: `false`
