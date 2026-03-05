import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

fs = 2e6
data = np.fromfile("baseline_433_LO433.925M_sr2M_gain30_1m.cfile",
                   dtype=np.complex64)

# Use only first few million samples for quick PSD
segment = data[:5_000_000]

f, Pxx = welch(segment, fs=fs, nperseg=4096)

plt.semilogy(f/1e6 - 1.0, Pxx)  # baseband frequency
plt.xlabel("Frequency Offset (MHz)")
plt.ylabel("Power Spectral Density")
plt.title("433 MHz Baseline PSD")
plt.show()