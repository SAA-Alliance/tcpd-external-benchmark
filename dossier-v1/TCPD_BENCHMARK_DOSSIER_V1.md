# TCPD Benchmark Dossier V1

Generated: `2026-08-15T13:11:19Z`
Canonical source result: `sha256:74a3cb1c150ed3a0c06177f1dec2fef69f9385d0c95b7c9345dcd78c85934222`

## Boundary

Research-only external adapter evidence. No raw TCPD series are exported. Non-separation in Nemenyi is reported as `INCONCLUSIVE`, not equality or superiority.

## Claim Discipline

- Published headline: default F-measure paired common-set rank 4/15 (CI95 1-7) on 35 of 42 paired datasets
- Required uncertainty: rank CI95 [1.0, 7.0], score 0.6941 CI95 [0.6310, 0.7542]
- Frame reconciliation: earlier successful-rows frame rank 6 lies within the paired-frame rank CI [1,7]; the frames are consistent and the paired frame removes missing-row selection effects.
- Pairwise read: SAA-minus-binseg mean difference -0.0503 CI95 [-0.1264, 0.0210], W/T/L 14/6/15.
- Friedman/Nemenyi result: statistic 217.8456; p 1.217e-38; CD95 3.625; SAA CD group binseg, pelt, bocpd, SAA, segneigh, amoc, zero, cpnp, ecp; interpretation INCONCLUSIVE_NOT_EQUIVALENCE.
- Real-world stability: real-world 37 stability: default F rank 4/15 on 30 of 37; default covering rank 5/15 on 30 of 37; all_42 covering rank 5/15.
- Change log: sha256:91b38e1f -> sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08; headline discipline wrapper added; numeric_fields_changed=false.
- Change log: sha256:bdf16c21688b9c9e661b2b94f7e928a1aa568847139a5e155517ff22883bca08 -> sha256:this_artifact_declared_in_dossier_root; headline field made self-contained; full pairwise table, frame reconciliation and Friedman/Nemenyi result surfaced; numeric_fields_changed=false.
- Rule: headline may cite default ranks only, never oracle ranks
- Rule: rank must be printed with bootstrap rank CI
- Rule: score must be printed with bootstrap score CI
- Rule: pairwise SAA-minus-top-method CI and W/T/L must be printed near the headline
- Rule: Friedman/Nemenyi must be printed with INCONCLUSIVE_NOT_EQUIVALENCE caveat
- Rule: default and oracle frames must not be compared directly because their common-set denominators differ
- Rule: real-world 37 subset must be printed as a stability check, not as a cherry-picked replacement frame

## Headline

### all_42

- `default_f_measure` · common datasets `35/42` · SAA mean `0.6941` CI95 `[0.6310, 0.7542]` · paired avg-rank position `4/15` CI95 `[1.0, 7.0]` · Friedman p `1.217e-38` · CD95 `3.625`
  - Nemenyi not separated from SAA: binseg, pelt, bocpd, SAA, segneigh, amoc, zero, cpnp, ecp
- `default_covering` · common datasets `35/42` · SAA mean `0.6542` CI95 `[0.5914, 0.7150]` · paired avg-rank position `5/15` CI95 `[1.0, 7.0]` · Friedman p `2.358e-35` · CD95 `3.625`
  - Nemenyi not separated from SAA: binseg, pelt, amoc, segneigh, SAA, bocpd, rbocpdms, bocpdms, zero, prophet, ecp, cpnp
- `oracle_f_measure` · common datasets `37/42` · SAA mean `0.8699` CI95 `[0.8318, 0.9058]` · paired avg-rank position `6/15` CI95 `[2.0, 7.0]` · Friedman p `9.063e-52` · CD95 `3.526`
  - Nemenyi not separated from SAA: bocpd, binseg, segneigh, rfpop, pelt, SAA, cpnp, ecp, amoc
- `oracle_covering` · common datasets `37/42` · SAA mean `0.7906` CI95 `[0.7512, 0.8304]` · paired avg-rank position `3/15` CI95 `[1.0, 6.0]` · Friedman p `1.974e-39` · CD95 `3.526`
  - Nemenyi not separated from SAA: bocpd, rfpop, SAA, segneigh, binseg, pelt, cpnp, amoc, ecp

### real_world_37

- `default_f_measure` · common datasets `30/37` · SAA mean `0.6639` CI95 `[0.6008, 0.7240]` · paired avg-rank position `4/15` CI95 `[1.0, 7.0]` · Friedman p `4.137e-31` · CD95 `3.916`
  - Nemenyi not separated from SAA: binseg, pelt, bocpd, SAA, segneigh, amoc, zero, cpnp, ecp, bocpdms
- `default_covering` · common datasets `30/37` · SAA mean `0.6334` CI95 `[0.5698, 0.6949]` · paired avg-rank position `5/15` CI95 `[1.0, 7.0]` · Friedman p `1.751e-31` · CD95 `3.916`
  - Nemenyi not separated from SAA: binseg, pelt, amoc, segneigh, SAA, bocpd, bocpdms, rbocpdms, zero, prophet, ecp, cpnp
- `oracle_f_measure` · common datasets `32/37` · SAA mean `0.8508` CI95 `[0.8110, 0.8892]` · paired avg-rank position `6/15` CI95 `[3.0, 7.0]` · Friedman p `1.437e-44` · CD95 `3.792`
  - Nemenyi not separated from SAA: bocpd, binseg, segneigh, rfpop, pelt, SAA, cpnp, ecp, amoc
- `oracle_covering` · common datasets `32/37` · SAA mean `0.7679` CI95 `[0.7304, 0.8066]` · paired avg-rank position `5/15` CI95 `[2.0, 7.0]` · Friedman p `2.07e-35` · CD95 `3.792`
  - Nemenyi not separated from SAA: bocpd, rfpop, segneigh, binseg, SAA, pelt, cpnp, amoc, ecp, bocpdms, rbocpdms

## Top Ranking Rows

### all_42 · default_f_measure

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | binseg | 4.500 | 0.7444 | 1 |
| 2 | pelt | 4.843 | 0.7100 | 2 |
| 3 | bocpd | 5.400 | 0.6896 | 5 |
| 4 | SAA | 5.614 | 0.6941 | 4 |
| 5 | segneigh | 5.857 | 0.6755 | 6 |
| 6 | amoc | 6.043 | 0.7037 | 3 |
| 7 | zero | 7.071 | 0.6690 | 7 |
| 8 | cpnp | 7.171 | 0.6067 | 8 |

### all_42 · default_covering

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | binseg | 4.929 | 0.7058 | 1 |
| 2 | pelt | 5.043 | 0.6888 | 3 |
| 3 | amoc | 5.357 | 0.7016 | 2 |
| 4 | segneigh | 5.471 | 0.6764 | 4 |
| 5 | SAA | 6.143 | 0.6542 | 5 |
| 6 | bocpd | 6.443 | 0.6360 | 7 |
| 7 | rbocpdms | 7.457 | 0.6454 | 6 |
| 8 | bocpdms | 7.486 | 0.6337 | 8 |

### all_42 · oracle_f_measure

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | bocpd | 4.473 | 0.8962 | 1 |
| 2 | binseg | 4.703 | 0.8865 | 3 |
| 3 | segneigh | 4.851 | 0.8869 | 2 |
| 4 | rfpop | 4.973 | 0.8842 | 4 |
| 5 | pelt | 5.405 | 0.8771 | 5 |
| 6 | SAA | 5.689 | 0.8699 | 6 |
| 7 | cpnp | 6.311 | 0.8605 | 7 |
| 8 | ecp | 7.324 | 0.7966 | 9 |

### all_42 · oracle_covering

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | bocpd | 4.419 | 0.8011 | 2 |
| 2 | rfpop | 5.324 | 0.8020 | 1 |
| 3 | SAA | 5.419 | 0.7906 | 6 |
| 4 | segneigh | 5.500 | 0.7959 | 3 |
| 5 | binseg | 5.676 | 0.7935 | 4 |
| 6 | pelt | 6.095 | 0.7919 | 5 |
| 7 | cpnp | 7.122 | 0.7804 | 7 |
| 8 | amoc | 7.257 | 0.7460 | 9 |

### real_world_37 · default_f_measure

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | binseg | 4.567 | 0.7060 | 1 |
| 2 | pelt | 4.850 | 0.6708 | 2 |
| 3 | bocpd | 5.367 | 0.6560 | 5 |
| 4 | SAA | 5.500 | 0.6639 | 3 |
| 5 | segneigh | 6.033 | 0.6306 | 7 |
| 6 | amoc | 6.333 | 0.6607 | 4 |
| 7 | zero | 6.900 | 0.6517 | 6 |
| 8 | cpnp | 6.983 | 0.5796 | 8 |

### real_world_37 · default_covering

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | binseg | 4.783 | 0.6758 | 1 |
| 2 | pelt | 4.967 | 0.6553 | 3 |
| 3 | amoc | 5.383 | 0.6694 | 2 |
| 4 | segneigh | 5.467 | 0.6409 | 4 |
| 5 | SAA | 5.950 | 0.6334 | 5 |
| 6 | bocpd | 6.667 | 0.5979 | 7 |
| 7 | bocpdms | 7.283 | 0.5876 | 8 |
| 8 | rbocpdms | 7.350 | 0.5988 | 6 |

### real_world_37 · oracle_f_measure

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | bocpd | 4.234 | 0.8859 | 1 |
| 2 | binseg | 4.609 | 0.8728 | 3 |
| 3 | segneigh | 4.672 | 0.8752 | 2 |
| 4 | rfpop | 4.922 | 0.8701 | 4 |
| 5 | pelt | 5.312 | 0.8638 | 5 |
| 6 | SAA | 5.797 | 0.8508 | 6 |
| 7 | cpnp | 6.359 | 0.8447 | 7 |
| 8 | ecp | 7.375 | 0.7734 | 9 |

### real_world_37 · oracle_covering

| rank | method | avg dataset rank | mean score | rank by mean score |
|---:|---|---:|---:|---:|
| 1 | bocpd | 4.438 | 0.7827 | 2 |
| 2 | rfpop | 4.984 | 0.7841 | 1 |
| 3 | segneigh | 5.391 | 0.7769 | 3 |
| 4 | binseg | 5.594 | 0.7741 | 4 |
| 5 | SAA | 5.766 | 0.7679 | 6 |
| 6 | pelt | 5.875 | 0.7724 | 5 |
| 7 | cpnp | 7.062 | 0.7591 | 7 |
| 8 | amoc | 7.750 | 0.7169 | 10 |

## Pairwise Tables

Default F-measure headline pairwise table; SAA-minus-opponent over the same 35 paired datasets:

| opponent | mean diff | CI95 low | CI95 high | W/T/L | sign |
|---|---:|---:|---:|---:|---|
| kcpa | 0.5831 | 0.4992 | 0.6644 | 34/0/1 | SAA higher |
| wbs | 0.2824 | 0.1931 | 0.3749 | 29/3/3 | SAA higher |
| rbocpdms | 0.2492 | 0.1817 | 0.3153 | 30/1/4 | SAA higher |
| prophet | 0.2064 | 0.1317 | 0.2828 | 24/8/3 | SAA higher |
| rfpop | 0.1946 | 0.1000 | 0.2916 | 23/4/8 | SAA higher |
| bocpdms | 0.1862 | 0.1271 | 0.2461 | 27/2/6 | SAA higher |
| ecp | 0.0964 | 0.0233 | 0.1744 | 15/14/6 | SAA higher |
| cpnp | 0.0874 | 0.0085 | 0.1672 | 21/4/10 | SAA higher |
| zero | 0.0251 | -0.0623 | 0.1050 | 13/18/4 | CI crosses 0 |
| segneigh | 0.0186 | -0.0534 | 0.0919 | 16/5/14 | CI crosses 0 |
| bocpd | 0.0045 | -0.0648 | 0.0778 | 15/4/16 | CI crosses 0 |
| amoc | -0.0096 | -0.0929 | 0.0705 | 14/6/15 | CI crosses 0 |
| pelt | -0.0159 | -0.0803 | 0.0485 | 13/6/16 | CI crosses 0 |
| binseg | -0.0503 | -0.1264 | 0.0210 | 14/6/15 | CI crosses 0 |

See `pairwise_score_differences.csv` for every scope and metric.

## Critical-Difference SVGs

- `cd_all_42_default_f_measure.svg`
- `cd_all_42_default_covering.svg`
- `cd_all_42_oracle_f_measure.svg`
- `cd_all_42_oracle_covering.svg`
- `cd_real_world_37_default_f_measure.svg`
- `cd_real_world_37_default_covering.svg`
- `cd_real_world_37_oracle_f_measure.svg`
- `cd_real_world_37_oracle_covering.svg`

## Files

- `TCPD_BENCHMARK_DOSSIER_V1.json`
- `paired_common_dataset_rankings.csv`
- `pairwise_score_differences.csv`

