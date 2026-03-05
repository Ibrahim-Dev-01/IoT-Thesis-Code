import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from tqdm import tqdm

fs = 20e6
NPERSEG = 4096

channels = {
    "Ch 1": {
        "lo": 2.412e9,
        "files": [
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run02.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run03.cfile"
        ]
    },

    "Ch 6": {
        "lo": 2.437e9,
        "files": [
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run01.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run02.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 6 - baseline_2.4Ghz_LO2.437G_sr20M_gain20_30s_run03.cfile"
        ]
    },

    "Ch 11": {
        "lo": 2.462e9,
        "files": [
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run01.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run02.cfile",
        "D:\\GNU Radio recordings\\2.4 ghz\\CH 11 - baseline_2.4Ghz_LO2.462G_sr20M_gain20_30s_run03.cfile"
        ]
    }
}

def load_subset(fn, fs, seconds=1.0, offset_seconds=5.0):
    n = int(fs * seconds)
    offset = int(fs * offset_seconds)
    mm = np.memmap(fn, dtype=np.complex64, mode="r")
    end = min(len(mm), offset + n)
    return np.array(mm[offset:end])

for ch, info in channels.items():
    lo = info["lo"]
    psds = []

    print(f"\nProcessing {ch}")
    for fn in tqdm(info["files"], desc=f"{ch} runs"):
        x = load_subset(fn, fs, seconds=1.0, offset_seconds=5.0)

        f, Pxx = welch(x, fs=fs, nperseg=NPERSEG, return_onesided=False, scaling="density")
        Pxx = np.fft.fftshift(Pxx)
        psds.append(Pxx)

    Pavg = np.mean(np.array(psds), axis=0)
    f = np.fft.fftshift(f)
    f_ghz = (f + lo) / 1e9
    Pavg_db = 10*np.log10(Pavg + 1e-12)

    plt.figure(figsize=(10,5))
    plt.plot(f_ghz, Pavg_db)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("PSD (dB/Hz)")
    plt.title(f"Wi-Fi Baseline PSD (Averaged) — {ch}")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"baseline_wifi_{ch}.png", dpi=200)
    plt.close()

print("Done. Saved baseline_wifi_CH1.png, baseline_wifi_CH6.png, baseline_wifi_CH11.png")