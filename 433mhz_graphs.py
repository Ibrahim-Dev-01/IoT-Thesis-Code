import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Recreates the graphs we made in chat from rtl_power CSV files.

DATA_DIR = Path(r"C:\\Users\\Zaid_\\Shared_VM\\Feb 2. Testing")

FILES = {
    "baseline_r1": DATA_DIR / "baseline_433MHz_off_none_10m_r1.csv",
    "baseline_r2": DATA_DIR / "baseline_433MHz_off_none_10m_r2.csv",
    "random_r1":   DATA_DIR / "nexa_433MHz_random_active_5m_r1.csv",
    "random_r2":   DATA_DIR / "nexa_433MHz_random_active_5m_r2.csv",
    "fixed_r1":    DATA_DIR / "nexa_433MHz_fixed10s_active_5m_r1.csv",
    "fixed_r2":    DATA_DIR / "nexa_433MHz_fixed10s_active_5m_r2.csv",
    "idle":        DATA_DIR / "nexa_433MHz_idle_active_10m.csv",
}

OUT_DIR = Path("Plots for 433mhz")
OUT_DIR.mkdir(exist_ok=True)

FREQ_MIN_HZ = 433e6
FREQ_MAX_HZ = 434.8e6


def load_rtl_power(path: Path):
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            try:
                nums = [float(x) for x in parts[2:]]  # skip date, time
            except ValueError:
                continue
            rows.append(nums)

    if not rows:
        raise ValueError(f"No numeric rows parsed from {path}")

    data = np.array(rows, dtype=float)
    first = data[0]

    power_start = next((i for i, v in enumerate(first) if v < 0), 3)

    start_f = first[0]
    end_f = first[1]
    bin_w = first[2]

    power = data[:, power_start:]
    avg = power.mean(axis=0)
    freqs = np.linspace(start_f, end_f, power.shape[1], endpoint=False)

    return freqs, avg, power, bin_w


def interp_to_reference(freq_ref, freq_other, avg_other):
    return np.interp(freq_ref, freq_other, avg_other)


def band_mask(freqs_hz):
    return (freqs_hz >= FREQ_MIN_HZ) & (freqs_hz <= FREQ_MAX_HZ)


def save_plot(filename: str):
    plt.savefig(OUT_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    f_b1, avg_b1, p_b1, bw = load_rtl_power(FILES["baseline_r1"])
    f_b2, avg_b2, p_b2, _  = load_rtl_power(FILES["baseline_r2"])
    f_r1, avg_r1, p_r1, _  = load_rtl_power(FILES["random_r1"])
    f_r2, avg_r2, p_r2, _  = load_rtl_power(FILES["random_r2"])
    f_f1, avg_f1, p_f1, _  = load_rtl_power(FILES["fixed_r1"])
    f_f2, avg_f2, p_f2, _  = load_rtl_power(FILES["fixed_r2"])
    f_i,  avg_i,  p_i,  _  = load_rtl_power(FILES["idle"])

    freq_ref = f_b1
    avg_b2_i = interp_to_reference(freq_ref, f_b2, avg_b2)
    avg_r1_i = interp_to_reference(freq_ref, f_r1, avg_r1)
    avg_r2_i = interp_to_reference(freq_ref, f_r2, avg_r2)
    avg_f1_i = interp_to_reference(freq_ref, f_f1, avg_f1)
    avg_f2_i = interp_to_reference(freq_ref, f_f2, avg_f2)
    avg_i_i  = interp_to_reference(freq_ref, f_i,  avg_i)

    mask = band_mask(freq_ref)
    freqs_mhz = freq_ref[mask] / 1e6

    baseline_mean = (avg_b1 + avg_b2_i) / 2
    random_mean   = (avg_r1_i + avg_r2_i) / 2
    fixed_mean    = (avg_f1_i + avg_f2_i) / 2

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, avg_b1[mask], label="Baseline r1")
    plt.plot(freqs_mhz, avg_b2_i[mask], label="Baseline r2")
    plt.plot(freqs_mhz, baseline_mean[mask], label="Baseline mean", linewidth=2.5)
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline measurements and mean (433 MHz band)")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline measurements and mean (433 MHz band).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, avg_b1[mask], label="Baseline r1")
    plt.plot(freqs_mhz, avg_b2_i[mask], label="Baseline r2")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline measurements (no IoT device present)")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline measurements (no IoT device present).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, avg_b1[mask], label="Baseline r1")
    plt.plot(freqs_mhz, avg_b2_i[mask], label="Baseline r2")
    plt.plot(freqs_mhz, avg_r1_i[mask], label="Random r1")
    plt.plot(freqs_mhz, avg_r2_i[mask], label="Random r2")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline vs Random Nexa activity (all runs shown)")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline vs Random Nexa activity (all runs).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, baseline_mean[mask], label="Baseline (mean of r1 & r2)")
    plt.plot(freqs_mhz, random_mean[mask], label="Random activity (mean of r1 & r2)")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline vs Random Nexa Activity (433 MHz band)")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline vs Random Nexa Activity (433 MHz band).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, (random_mean - baseline_mean)[mask])
    plt.axhline(0, linestyle="--")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Δ Power (dB)")
    plt.title("Difference: Random Activity − Baseline")
    plt.grid(True)
    save_plot("Difference - Random Activity (Baseline).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, avg_b1[mask], label="Baseline r1")
    plt.plot(freqs_mhz, avg_b2_i[mask], label="Baseline r2")
    plt.plot(freqs_mhz, avg_f1_i[mask], label="Fixed 10 s r1")
    plt.plot(freqs_mhz, avg_f2_i[mask], label="Fixed 10 s r2")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline vs Fixed-Interval Nexa Activity (all runs)")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline vs Fixed-Interval Nexa Activity (all runs).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, (fixed_mean - baseline_mean)[mask])
    plt.axhline(0, linestyle="--")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Δ Power (dB)")
    plt.title("Difference to baseline (Fixed 10 s − Baseline)")
    plt.grid(True)
    save_plot("Difference to baseline (Fixed 10 s − Baseline).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, avg_b1[mask], label="Baseline r1")
    plt.plot(freqs_mhz, avg_b2_i[mask], label="Baseline r2")
    plt.plot(freqs_mhz, avg_i_i[mask], label="Idle (device ON)")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("Baseline vs Idle Nexa Device")
    plt.grid(True)
    plt.legend()
    save_plot("Baseline vs Idle Nexa Device.png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, (avg_i_i - baseline_mean)[mask])
    plt.axhline(0, linestyle="--")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Δ Power (dB)")
    plt.title("Difference to baseline (Idle)")
    plt.grid(True)
    save_plot("Difference to baseline (Idle).png")

    plt.figure(figsize=(10, 6))
    plt.plot(freqs_mhz, baseline_mean[mask], label="Baseline (OFF)")
    plt.plot(freqs_mhz, random_mean[mask], label="Random activity")
    plt.plot(freqs_mhz, fixed_mean[mask], label="Fixed activity (10 s)")
    plt.plot(freqs_mhz, avg_i_i[mask], label="Idle (device ON, no interaction)")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Power (dB)")
    plt.title("433 MHz Band – Average Spectrum per Experiment Condition")
    plt.grid(True)
    plt.legend()
    save_plot("433 MHz Band – Average Spectrum per Experiment Condition.png")

    print(f"Done. Effective bin width ≈ {bw/1e3:.2f} kHz")
    print(f"Plots saved to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
