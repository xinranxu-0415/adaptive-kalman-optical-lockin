# Reproduction comparison

Reprocessed all 19 archived recordings with the recovered analysis settings.

| Method | Fold | Recomputed noise | Report noise | Recomputed t90 (s) | Report t90 (s) |
|---|---|---:|---:|---:|---:|
| zero-phase LP (non-causal) | A | 1.27196 | 1.27 | 2.12500 | 2.12 |
| zero-phase LP (non-causal) | B | 1.53515 | 1.54 | 1.88000 | 1.88 |
| causal LP | A | 1.52671 | 1.53 | 4.46000 | 4.46 |
| causal LP | B | 1.31814 | 1.32 | 4.76000 | 4.76 |
| fixed-Q Kalman | A | 1.43026 | 1.43 | 5.09000 | 5.09 |
| fixed-Q Kalman | B | 1.40734 | 1.41 | 5.14500 | 5.14 |
| adaptive-Q Kalman | A | 2.64922 | 2.65 | 1.79500 | 1.79 |
| adaptive-Q Kalman | B | 1.31164 | 1.31 | 2.73000 | 2.73 |

All eight fold/method noise and t90 pairs agree at the reported precision.
Single-split adaptive training noise = 1.27077 counts, held-out noise = 2.13737 counts, t90 = 2.185 s (reported approximately 1.27, 2.14, 2.2).
Differences in the final decimal of other summaries can follow rounding of per-fold versus averaged values. The full precision results are in JSON.
The optimized KF amplitude agrees with the recovered matrix implementation within 6e-14 counts on the checked large-step recording; multiplier difference is below 2e-10.
This verifies processing of the archived data. It does not independently validate the physical calibration or repeat hardware acquisition.
