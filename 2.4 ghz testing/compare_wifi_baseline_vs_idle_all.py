import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
import csv
from tqdm import tqdm

# =======================
# Settings
# =======================
fs = 20e6
NPERSEG = 4096

# Speed/robustness: sample short segments from each 30s capture
# You can increase seconds_per_chunk later (e.g., 2.0 or 5.0)
seconds_per_chunk = 1.0
offset_seconds = 5.0  # start a bit after t=0

def load_subset_memmap(fn, fs, seconds, offset_s):
    n = int(fs * seconds)
    off = int(fs * offset_s)
    mm = np.memmap(fn, dtype=np.complex64, mode="r")
    end = min(len(mm), off + n)
    return np.array(mm[off:end])

def avg_psd(files, lo_hz, label):
    psds = []
    for fn in tqdm(files, desc=f"PSD {label}", leave=False):
        x = load_subset_memmap(fn, fs, seconds_per_chunk, offset_seconds)
        f, Pxx = welch(x, fs=fs, nperseg=NPERSEG, return_onesided=False, scaling="density")
        psds.append(np.fft.fftshift(Pxx))

    f = np.fft.fftshift(f)
    Pavg = np.mean(np.array(psds), axis=0)
    f_ghz = (f + lo_hz) / 1e9
    Pavg_db = 10*np.log10(Pavg + 1e-12)
    return f_ghz, Pavg_db

channels = {
    1: {
        "lo": 2.412e9,
        "baseline": [
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run03.cfile",
        ],
        "idle": [
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 1 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 1 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 1 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run03.cfile",
        ],
    },
    6: {
        "lo": 2.437e9,
        "baseline": [
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run03.cfile",
        ],
        "idle": [
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 6 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 6 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 6 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run03.cfile",
        ],
    },
    11: {
        "lo": 2.462e9,
        "baseline": [
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run03.cfile",
        ],
        "idle": [
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 11 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 11 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run02.cfile",
            "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 11 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run03.cfile",
        ],
    },
}

summary = []

for ch, info in channels.items():
    lo = info["lo"]

    print(f"\n=== Channel {ch} (LO={lo/1e9:.3f} GHz) ===")
    f_base, base_db = avg_psd(info["baseline"], lo, f"CH{ch} baseline")
    f_idle, idle_db = avg_psd(info["idle"], lo, f"CH{ch} idle")

    delta_db = idle_db - base_db

    # Overlay plot
    plt.figure(figsize=(10,5))
    plt.plot(f_base, base_db, label="Baseline (avg)")
    plt.plot(f_idle, idle_db, label="Idle (avg)", alpha=0.9)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("PSD (dB/Hz)")
    plt.title(f"Wi-Fi CH{ch}: Baseline vs Idle (Averaged PSD)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"wifi_ch{ch}_baseline_vs_idle_overlay.png", dpi=200)
    plt.close()

    # Delta plot
    plt.figure(figsize=(10,5))
    plt.plot(f_base, delta_db)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("ΔPSD (dB)  [Idle - Baseline]")
    plt.title(f"Wi-Fi CH{ch}: ΔPSD (Idle - Baseline)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"wifi_ch{ch}_delta_psd_idle_minus_baseline.png", dpi=200)
    plt.close()

    # Simple summary stats
    base_median = float(np.median(base_db))
    idle_median = float(np.median(idle_db))
    delta_median = float(np.median(delta_db))
    delta_peak = float(np.max(delta_db))

    summary.append([ch, lo/1e9, base_median, idle_median, delta_median, delta_peak])

# Save summary CSV
with open("wifi_baseline_vs_idle_summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["channel", "lo_ghz", "baseline_psd_median_dbhz", "idle_psd_median_dbhz", "delta_median_db", "delta_peak_db"])
    w.writerows(summary)

print("\nSaved plots + wifi_baseline_vs_idle_summary.csv")