import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from tqdm import tqdm

# ====== SETTINGS ======
fs = 2e6
lo = 433.925e6

baseline_files = [
    "D:\\GNU Radio recordings\\433 mhz\\baseline_433_LO433.925M_sr2M_gain30_5m_run01.cfile",
    "D:\\GNU Radio recordings\\433 mhz\\baseline_433_LO433.925M_sr2M_gain30_5m_run02.cfile",
    "D:\\GNU Radio recordings\\433 mhz\\baseline_433_LO433.925M_sr2M_gain30_5m_run03.cfile",
]

active_files = [
    "D:\\GNU Radio recordings\\433 mhz testing\\433_active_LO433.925M_sr2M_gain30_60s_run01.cfile",
    "D:\\GNU Radio recordings\\433 mhz testing\\433_active_LO433.925M_sr2M_gain30_60s_run02.cfile",
    "D:\\GNU Radio recordings\\433 mhz testing\\433_active_LO433.925M_sr2M_gain30_60s_run03.cfile",
]

# Use subsets for speed (still representative)
BASELINE_SECONDS = 10   # from each 5-min file
ACTIVE_SECONDS   = 60   # use full active capture (already short)

NPERSEG = 8192

def load_subset(fn, seconds, offset_seconds=5):
    n = int(fs * seconds)
    off = int(fs * offset_seconds)
    mm = np.memmap(fn, dtype=np.complex64, mode="r")
    end = min(len(mm), off + n)
    
    return np.array(mm[off:end])

def avg_psd(files, seconds, label):
    psds = []
    for fn in tqdm(files, desc=f"PSD {label}"):
        x = load_subset(fn, seconds=seconds, offset_seconds=5)
        f, Pxx = welch(x, fs=fs, nperseg=NPERSEG, return_onesided=False, scaling="density")
        psds.append(np.fft.fftshift(Pxx))
    f = np.fft.fftshift(f)
    Pavg = np.mean(np.array(psds), axis=0)
    
    return f, Pavg

# ====== Compute averaged PSDs ======
f, P_base = avg_psd(baseline_files, BASELINE_SECONDS, "baseline")
_, P_act  = avg_psd(active_files, ACTIVE_SECONDS, "active")

# Convert frequency axis to MHz
f_mhz = (f + lo) / 1e6

# Convert to dB/Hz
base_db = 10*np.log10(P_base + 1e-12)
act_db  = 10*np.log10(P_act  + 1e-12)
delta_db = act_db - base_db

# ====== Plot 1: PSD overlay ======
plt.figure(figsize=(10,5))
plt.plot(f_mhz, base_db, label="Baseline (avg)")
plt.plot(f_mhz, act_db,  label="Active Nexa (avg)", alpha=0.9)
plt.xlabel("Frequency (MHz)")
plt.ylabel("PSD (dB/Hz)")
plt.title("433 MHz PSD: Baseline vs Nexa Active")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("433_psd_overlay.png", dpi=200)
plt.close()

# ====== Plot 2: Delta PSD ======
plt.figure(figsize=(10,5))
plt.plot(f_mhz, delta_db)
plt.xlabel("Frequency (MHz)")
plt.ylabel("ΔPSD (dB)  [Active - Baseline]")
plt.title("433 MHz ΔPSD: Nexa-induced Spectral Increase")
plt.grid(True)
plt.tight_layout()
plt.savefig("433_delta_psd.png", dpi=200)
plt.close()

print("Saved: 433_psd_overlay.png")
print("Saved: 433_delta_psd.png")

# ====== Plot 3: Time-domain power (show bursts) ======
# Use run01 as an example (you can repeat for others)
example_fn = active_files[0]
x = np.fromfile(example_fn, dtype=np.complex64)

block = 4096
nblocks = len(x)//block
xb = x[:nblocks*block].reshape(nblocks, block)
p = np.mean(np.abs(xb)**2, axis=1)
p_db = 10*np.log10(p + 1e-12)

t = (np.arange(nblocks) * block) / fs

plt.figure(figsize=(10,5))
plt.plot(t, p_db)
plt.xlabel("Time (s)")
plt.ylabel("Block Power (dB, relative)")
plt.title(f"433 MHz Nexa Active: Burst Visibility (example: {example_fn})")
plt.grid(True)
plt.tight_layout()
plt.savefig("433_active_bursts_timepower.png", dpi=200)
plt.close()

print("Saved: 433_active_bursts_timepower.png")
print("Done.")