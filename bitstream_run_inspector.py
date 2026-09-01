from pathlib import Path
from itertools import groupby

data = Path("jabra_bits.bin").read_bytes()

print("Total bytes:", len(data))
print("Unique values:", sorted(set(data)))
print("Zeros:", data.count(0))
print("Ones:", data.count(1))

runs = [(value, sum(1 for _ in group)) for value, group in groupby(data)]

print("Number of runs:", len(runs))
print("First 30 runs:")
for r in runs[:30]:
    print(r)

one_runs = [length for value, length in runs if value == 1]
zero_runs = [length for value, length in runs if value == 0]

print("One-runs:", len(one_runs))
print("Zero-runs:", len(zero_runs))

if one_runs:
    print("One-run min/max/avg:", min(one_runs), max(one_runs), sum(one_runs)/len(one_runs))

if zero_runs:
    print("Zero-run min/max/avg:", min(zero_runs), max(zero_runs), sum(zero_runs)/len(zero_runs))
