import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_PATH = r"Zaid Ibrahim\Shared_VM\Testing with PlutoSDR - RTC-410W"

folders = {
    "Baseline": os.path.join(BASE_PATH, "Baseline", "New Baseline"),
    "Idle": os.path.join(BASE_PATH, "Idle"),
    "Live Stream": os.path.join(BASE_PATH, "Active", "Live Stream"),
    "Motion Constant": os.path.join(BASE_PATH, "Active", "Trigger Motion Capture", "Constant"),
    "Motion Periodic": os.path.join(BASE_PATH, "Active", "Trigger Motion Capture", "Periodic"),
}

def load_csv(path):
    df = pd.read_csv(path, comment="#")
    df = df.select_dtypes(include="number")
    return df.iloc[:,0], df.iloc[:,1]

regions = range(1,20)

plt.figure(figsize=(18, 22))

for i, region in enumerate(regions, 1):
    plt.subplot(7,3,i)
    for label, folder in folders.items():
        for file in os.listdir(folder):
            if f"_{region:02}_" in file:
                path = os.path.join(folder, file)
                try:
                    freq, power = load_csv(path)
                    plt.plot(freq, power, label=label)
                except:
                    pass

    plt.title(f"Region {region}")
    plt.xlabel("Frequency")
    plt.ylabel("Power (dB)")
    plt.legend(fontsize=7)
    plt.grid()

plt.tight_layout()
plt.savefig("RTC410W_Comparison.png", dpi=300)
plt.show()