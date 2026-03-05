import numpy as np

filename = "baseline_433_LO433.925M_sr2M_gain30_1m.cfile"
data = np.fromfile(filename, dtype=np.complex64)

print("Total samples:", len(data))
print("Duration (seconds):", len(data) / 2e6)