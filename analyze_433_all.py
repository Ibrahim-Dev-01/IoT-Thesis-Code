import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

files = [
    "D:\\GNU Radio recordings\\baseline_433_LO433.925M_sr2M_gain30_5m_run01.cfile",
    "D:\\GNU Radio recordings\\baseline_433_LO433.925M_sr2M_gain30_5m_run02.cfile",
    "D:\\GNU Radio recordings\\baseline_433_LO433.925M_sr2M_gain30_5m_run03.cfile",
]
fs = 2e6
lo = 433.925e6

psd_list = []

for filename in files:
    print(f"\nProcessing {filename}")

    data = np.fromfile(filename, dtype=np.complex64)
    data = data[:20_000_000]

    f, Pxx = welch(data,
                   fs=fs,
                   nperseg=4096,
                   return_onesided=False,
                   scaling='density')

    Pxx = np.fft.fftshift(Pxx)
    psd_list.append(Pxx)

psd_array = np.array(psd_list)

Pxx_avg = np.mean(psd_array, axis=0)

f = np.fft.fftshift(f)
f_mhz = (f + lo) / 1e6

# Convert to dB
Pxx_avg_dB = 10 * np.log10(Pxx_avg + 1e-12)

# === Plot ===
plt.figure(figsize=(10,6))
plt.plot(f_mhz, Pxx_avg_dB)
plt.xlabel("Frequency (MHz)")
plt.ylabel("Power Spectral Density (dB/Hz)")
plt.title("Averaged Baseline 433 MHz PSD (3 Runs)")
plt.grid(True)
plt.tight_layout()
plt.show()