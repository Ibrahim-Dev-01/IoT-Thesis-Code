import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from tqdm import tqdm

fs = 20e6

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

for ch in channels:

    lo = channels[ch]["lo"]
    psd_runs = []
    
    print(f"\nProcessing {ch}") 

    for file in tqdm(channels[ch]["files"], desc=f"Runs"):

        data = np.fromfile(file, dtype=np.complex64)

        data = data[:10_000_000] # Use only first 10M samples for faster processing

        f, Pxx = welch(
            data,
            fs=fs,
            nperseg=4096,
            return_onesided=False,
            scaling='density'
        )

        Pxx = np.fft.fftshift(Pxx)
        psd_runs.append(Pxx)

    psd_avg = np.mean(psd_runs, axis=0)

    f = np.fft.fftshift(f)
    freq = (f + lo) / 1e9
    psd_db = 10*np.log10(psd_avg + 1e-12)

    plt.figure(figsize=(10,5))
    plt.plot(freq, psd_db)
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("Power Spectral Density (dB/Hz)")
    plt.title(f"WiFi Baseline PSD - {ch}")
    plt.grid(True)
    plt.show()