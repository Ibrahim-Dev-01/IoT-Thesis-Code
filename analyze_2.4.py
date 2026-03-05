import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

# ========= USER SETTINGS =========
fs = 20e6  # 20 MS/s sample rate (matches recording)
gain_db = 20  # just for labeling
channels = {
    1: {"LO": 2.412e9, "files": ["wifi_ch1_run01.cfile", "wifi_ch1_run02.cfile", "wifi_ch1_run03.cfile"]},
    6: {"LO": 2.437e9, "files": ["wifi_ch6_run01.cfile", "wifi_ch6_run02.cfile", "wifi_ch6_run03.cfile"]},
    11: {"LO": 2.462e9, "files": ["wifi_ch11_run01.cfile", "wifi_ch11_run02.cfile", "wifi_ch11_run03.cfile"]},
}

# Welch settings - reasonable balance of speed/quality for baseline analysis.
NPERSEG = 8192

# Occupancy settings (simple energy detector)
# We'll compute power over time in short blocks and flag "busy" if above threshold.
BLOCK = 4096  # samples per time block
THRESH_DB_OVER_MEDIAN = 6.0  # "busy if > median + 6 dB" (baseline-friendly heuristic)

summary_rows = []

for ch, info in channels.items():
    lo = info["lo"]
    psds = []
    run_busy = []

    for fn in info["files"]:
        print(f"Loading: {fn}")
        x = np.fromfile(fn, dtype=np.complex64)

        # --- PSD ---
        f, Pxx = welch(x, fs=fs, nperseg=NPERSEG, return_onesided=False, scaling="density")
        Pxx = np.fft.fftshift(Pxx)
        psds.append(Pxx)

        # --- Occupancy ("busy %") ---
        # Compute average power per block (time slices)
        nblocks = len(x) // BLOCK
        xb = x[: nblocks * BLOCK].reshape(nblocks, BLOCK)
        p = np.mean(np.abs(xb) ** 2, axis=1)  # linear power
        p_db = 10 * np.log10(p + 1e-12)

        median_db = np.median(p_db)
        thresh_db = median_db + THRESH_DB_OVER_MEDIAN
        busy_pct = 100.0 * np.mean(p_db > thresh_db)
        run_busy.append(busy_pct)

    # Average PSD across runs
    Pavg = np.mean(np.array(psds), axis=0)

    # Frequency axis to absolute GHz
    f = np.fft.fftshift(f)
    f_ghz = (f + lo) / 1e9
    Pavg_db = 10 * np.log10(Pavg + 1e-12)

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(f_ghz, Pavg_db)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("PSD (dB/Hz)")
    plt.title(f"Wi-Fi Baseline PSD (Ch {ch}, LO={lo/1e9:.3f} GHz, Fs={fs/1e6:.0f} MS/s, Gain={gain_db} dB)")
    plt.grid(True)
    plt.tight_layout()
    out_png = f"baseline_wifi_ch{ch}_psd.png"
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"Saved: {out_png}")

    # Summaries
    busy_mean = float(np.mean(run_busy))
    busy_std = float(np.std(run_busy, ddof=1)) if len(run_busy) > 1 else 0.0
    noise_floor_db = float(np.median(Pavg_db))  # crude but useful reference

    summary_rows.append((ch, lo/1e9, busy_mean, busy_std, noise_floor_db))

# Write summary CSV
import csv
with open("wifi_baseline_summary.csv", "w", newline="") as fcsv:
    w = csv.writer(fcsv)
    w.writerow(["channel", "lo_ghz", "busy_pct_mean", "busy_pct_std", "psd_median_db_per_hz"])
    for row in summary_rows:
        w.writerow(row)

print("Saved: wifi_baseline_summary.csv")
print("Done.")