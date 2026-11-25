#!/usr/bin/env python3
"""Run ALL final-project recordings automatically, one after another.

Usage (close the Arduino Serial Monitor first!):
    caffeinate -i python3 run_all.py
Takes about 25 minutes. Do not touch the box or the cables while it runs.
Data go to a new folder  data_YYYYMMDD_HHMM/  next to this script.
"""
import glob
import os
import sys
import time
import datetime

import serial

# (mode, tag).  K = calibration, N = noise, 1..5 = dynamic signals
PLAN = [("K", "pre"), ("N", "1"), ("N", "2")]
PLAN += [(m, f"r{r}") for r in (1, 2, 3) for m in "12345"]
PLAN += [("K", "post")]

DURATION_S = {"K": 90}          # all other modes: 60 s
DEFAULT_S = 60
SAMPLE_HZ = 200
REST_S = 8                      # pause between runs (LDR recovers, LEDs off)
NAMES = {"K": "calibration", "N": "noise", "1": "large steps", "2": "small steps",
         "3": "ramp", "4": "slow sine", "5": "random walk"}


def dur(mode):
    return DURATION_S.get(mode, DEFAULT_S)


def find_port():
    ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))
    if not ports:
        sys.exit("No Arduino port found (/dev/cu.usbmodem* or /dev/cu.usbserial*). "
                 "Is the USB cable plugged in? Is the Serial Monitor closed?")
    return ports[0]


def one_run(ser, mode, path):
    """Start one run, save CSV, return (ok, n_samples, a0_min, a0_mean, a0_max)."""
    ser.reset_input_buffer()
    ser.write(mode.encode())
    t_start = time.time()
    limit = dur(mode) + 20
    n, done = 0, False
    vals = []
    with open(path, "w") as f:
        while time.time() - t_start < limit:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if line.startswith("# DONE"):
                done = True
                break
            if line.startswith("#"):
                continue
            f.write(line + "\n")
            if not line.startswith("ms"):
                n += 1
                try:
                    vals.append(int(line.split(",")[1]) / 8.0)
                except (IndexError, ValueError):
                    pass
    expected = dur(mode) * SAMPLE_HZ
    ok = done and n >= 0.95 * expected
    if vals:
        return ok, n, min(vals), sum(vals) / len(vals), max(vals)
    return ok, n, float("nan"), float("nan"), float("nan")


def main():
    port = find_port()
    total = sum(dur(m) + 3 + REST_S for m, _ in PLAN)
    print(f"Port: {port}")
    print(f"{len(PLAN)} runs, about {total / 60:.0f} minutes. Do not touch the box!\n")

    outdir = "data_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(outdir, exist_ok=True)

    ser = serial.Serial(port, 115200, timeout=1)
    t0 = time.time()
    ready = False
    while time.time() - t0 < 10:               # opening the port resets the Mega
        if ser.readline().decode(errors="ignore").strip().startswith("# READY"):
            ready = True
            break
    if not ready:
        print("Did not see '# READY' (is final_recorder.ino uploaded?). Continuing anyway.")

    summary = []
    for i, (mode, tag) in enumerate(PLAN, 1):
        name = f"run_{mode}_{tag}.csv"
        path = os.path.join(outdir, name)
        print(f"[{i}/{len(PLAN)}] {name}  ({NAMES[mode]}, {dur(mode)} s) ...", flush=True)
        res = one_run(ser, mode, path)
        if not res[0]:
            print("   run incomplete, repeating once ...", flush=True)
            time.sleep(REST_S)
            res = one_run(ser, mode, path)
        ok, n, lo, mean, hi = res
        status = "OK" if ok else "PROBLEM"
        line = f"{name:18s} {status:8s} samples={n:6d}  A0 min/mean/max = {lo:.0f}/{mean:.0f}/{hi:.0f}"
        print("   " + line, flush=True)
        summary.append(line)
        time.sleep(REST_S)
    ser.close()

    with open(os.path.join(outdir, "summary.txt"), "w") as f:
        f.write("\n".join(summary) + "\n")
    print("\nALL DONE. Files are in:", outdir)
    print("\n".join(summary))


if __name__ == "__main__":
    main()
