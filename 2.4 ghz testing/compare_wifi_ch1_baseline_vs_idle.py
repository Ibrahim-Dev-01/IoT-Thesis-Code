import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

# ===== SETTINGS =====
fs = 20e6
lo = 2.412e9
NPERSEG = 4096  # keep small for speed

baseline_file = "D:\\GNU Radio recordings\\2.4 ghz\\CH 1 - baseline_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile"
idle_file     = "D:\\GNU Radio recordings\\2.4 ghz testing\\CH 1 - idle_2.4Ghz_LO2.412G_sr20M_gain20_30s_run01.cfile"

def psd_avg(filename):
    # memmap avoids slow full read overhead
    x = np.memmap(filename, dtype=np.complex64, mode="r")
    # use first 1 second for fast check (increase later)
    x = np.array(x[:int(fs*1.0)])
    f, Pxx = welch(x, fs=fs, nperseg=NPERSEG, return_onesided=False, scaling="density")
    f = np.fft.fftshift(f)
    Pxx = np.fft.fftshift(Pxx)
    Pxx_db = 10*np.log10(Pxx + 1e-12)
    f_ghz = (f + lo) / 1e9
    return f_ghz, Pxx_db

f_b, base_db = psd_avg(baseline_file)
f_i, idle_db = psd_avg(idle_file)

# ---- Plot overlay ----
plt.figure(figsize=(10,5))
plt.plot(f_b, base_db, label="Baseline")
plt.plot(f_i, idle_db, label="Idle", alpha=0.9)
plt.xlabel("Frequency (GHz)")
plt.ylabel("PSD (dB/Hz)")
plt.title("Wi-Fi CH1: Baseline vs Idle (PSD Overlay)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("wifi_ch1_psd_overlay_baseline_vs_idle.png", dpi=200)
plt.show()

# ---- Delta plot ----
delta = idle_db - base_db
plt.figure(figsize=(10,5))
plt.plot(f_b, delta)
plt.xlabel("Frequency (GHz)")
plt.ylabel("ΔPSD (dB) [Idle - Baseline]")
plt.title("Wi-Fi CH1: ΔPSD (Idle - Baseline)")
plt.grid(True)
plt.tight_layout()
plt.savefig("wifi_ch1_delta_psd_baseline_vs_idle.png", dpi=200)
plt.show()

print("Saved: wifi_ch1_psd_overlay_baseline_vs_idle.png")
print("Saved: wifi_ch1_delta_psd_baseline_vs_idle.png")