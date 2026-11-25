# Adaptive Kalman Filtering for an Optical Lock-in Sensor

Final-project implementation and archived recordings for CMU 16-722, by Xinran Xue.
The system measures modulated LED light using a photoresistor, synchronous demodulation,
and a two-state Kalman filter with adaptive process noise. The comparison includes
causal low-pass filtering, a fixed-Q Kalman filter, and non-causal references.

## Quick start (archived data, no hardware required)

Tested with Python 3.12 on macOS. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py
```

Windows: activate `.venv\Scripts\activate` instead. First execution compiles the
Numba kernel. Outputs are JSON files in `results/` and PDF/PNG plots in `figures/`.
The script does not connect to or operate the sensor.

## Included files

| Path | Purpose |
| --- | --- |
| `firmware/final_recorder/final_recorder.ino` | Original Arduino acquisition firmware |
| `acquisition/run_all.py` | Original serial experiment scheduler/logger |
| `analysis/load.py` | Portable CSV loader; milliseconds to seconds, ADC sum divided by 8 |
| `analysis/pipe.py` | Demodulation, calibration, LP, fixed/adaptive KF, RTS |
| `analysis/evalx.py` | Noise, normalized step response, overshoot and RMSE metrics |
| `analysis/final.py` | Single training/test split and matched-noise baselines |
| `analysis/cv.py` | 216-configuration search and two held-out folds |
| `analysis/verify.py` | Data integrity and optimized/original KF comparison |
| `analysis/plot_results.py` | Regenerate representative result figures |
| `data/` | All 19 original CSV recordings and acquisition summary |
| `provenance/pdf_listings/` | Unmodified analysis/acquisition listings recovered from the original report |
| `provenance/recovery_map.json` | Listing line-to-original-PDF-page mapping |
| `results/` | Recomputed numerical results and verification record |

## Data and evaluation

CSV columns: `ms,adc8,ref,level,noise`. Sampling rate is nominally 200 Hz.
`adc8` is the sum of eight ADC readings; divide by eight before analysis.
`run_K_pre/post.csv` are 90-second calibrations. `run_N_1/2.csv` are 60-second
noise recordings. Modes 1-5 each have three 60-second rounds: large steps, small
steps, ramp, sine, and random walk. Recordings are preserved without editing.

Fold A trains on N1 and large-step round 1; tests on N2 and rounds 2/3.
Fold B trains on N2 and large-step round 2; tests on N1 and rounds 1/3.
The grid selects the fastest training t90 subject to training noise <=1.5 counts.
Each baseline is matched to that fold's training noise. The two folds overlap;
they are not independent repeat experiments. Zero-phase LP and RTS use future data.

`t90` is the first 90% crossing after the command, rather than a 10-90% rise interval.
Noise excludes the first 10 s; RMSE excludes the first 5 s. The reference is derived
from pre-calibration and commanded brightness, not an independent ground-truth sensor.
No held-out data are used to select the grid configuration.

## Code provenance and verification

Firmware and logger are copied from the author's original local source files.
The five analysis listings (`load`, `pipe`, `evalx`, `final`, `cv`) were recovered
from the author's original report because separate analysis source files were not
located. Original recovered listings and their PDF page mapping are retained.
Distribution changes provide relative paths, a one-command entry point, validation,
plots, and a Numba implementation of the same KF recurrence. `kalman_numpy` retains
the recovered matrix implementation; verification compares both implementations.
The CV worker pool is serial to avoid platform-specific process spawning.
Parameters and raw recordings were not retuned or replaced during packaging.

`results/verification.json` records checksums, sample counts, and numerical comparison.
`results/report_comparison.md` describes agreement with the report and rounding limits.
Hardware acquisition has not been rerun as part of this software verification.

## Acquiring new recordings (optional)

Use the hardware circuit and wiring documented in the report. Inspect the firmware
pin assignments and serial commands before uploading with Arduino IDE. The logger
uses pyserial at 115200 baud and macOS `/dev/cu.*` port discovery; adapt its port
selection for another operating system. Run it from a separate acquisition directory
to keep new measurements separate from the archived `data/` folder:

```bash
python /absolute/path/to/repository/acquisition/run_all.py
```

## 中文说明

老师可直接按 Quick start 使用已有数据复现，无需连接硬件。代码、19 份原始数据、
运行说明和重算结果都在本仓库。分析代码从原报告代码清单恢复，恢复原件与页码映射
保存在 provenance；未改动原始数据或调参。程序会重算单次划分和两折交叉验证。
