from pathlib import Path
from itertools import groupby

data = Path("jabra_bits.bin").read_bytes()
runs = [(v, sum(1 for _ in g)) for v, g in groupby(data)]

one_runs = [l for v, l in runs if v == 1]
zero_runs = [l for v, l in runs if v == 0]

print("Metric, Value")
print(f"Total bytes, {len(data)}")
print(f"Zeros, {data.count(0)}")
print(f"Ones, {data.count(1)}")
print(f"Zero ratio, {data.count(0)/len(data):.4f}")
print(f"One ratio, {data.count(1)/len(data):.4f}")
print(f"Total runs, {len(runs)}")
print(f"Average 0-run, {sum(zero_runs)/len(zero_runs):.2f}")
print(f"Average 1-run, {sum(one_runs)/len(one_runs):.2f}")
print(f"Max 0-run, {max(zero_runs)}")
print(f"Max 1-run, {max(one_runs)}")
