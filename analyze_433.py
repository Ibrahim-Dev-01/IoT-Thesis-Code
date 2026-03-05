import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

# === USER SETTINGS ===
filename = "baseline_433_LO433.925M_sr2M_gain30_5m_run01.cfile"
fs = 2e6              # Sample rate
lo = 433.925e6       # LO frequency

# === LOAD DATA ===
data = np.fromfile(filename, dtype=np.complex64)

print("Total samples in file:", len(data))

# Use only first 20 million samples (~10 seconds at 2 MS/s)
data = data[:20_000_000]

print("Samples used for PSD:", len(data))

# === COMPUTE PSD ===
f, Pxx = welch(data,
               fs=fs,
               nperseg=4096,
               return_onesided=False,
               scaling='density')

# Shift frequency axis
f = np.fft.fftshift(f)
Pxx = np.fft.fftshift(Pxx)

# Convert to MHz
f_mhz = (f + lo) / 1e6

# Convert power to dB
Pxx_dB = 10 * np.log10(Pxx)

# === PLOT ===
plt.figure(figsize=(10,6))
plt.plot(f_mhz, Pxx_dB)
plt.xlabel("Frequency (MHz)")
plt.ylabel("Power Spectral Density (dB/Hz)")
plt.title("Baseline 433 MHz PSD")
plt.grid(True)
plt.show()

