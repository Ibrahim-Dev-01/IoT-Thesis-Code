#!/usr/bin/env bash
set -euo pipefail

CONDITION="${1:-baseline}"
DEVICE='driver=plutosdr,uri=ip:192.168.2.1'
BASE_DIR="$HOME/phase1/$CONDITION"
SECONDS=0

mkdir -p "$BASE_DIR"

echo "Checking PlutoSDR connectivity... Please Understand"
if ping -c 3 192.168.2.1 >/dev/null 2>&1; then
    echo "Reached PlutoSDR :D"    
    echo "	Let the magic generate!"
else
    echo "ERROR: Could not reach PlutoSDR at 192.168.2.1"
    echo "Check USB/Ethernet connection and IP assignment."
    exit 1
fi

echo
echo "Running Phase 1 for condition: $CONDITION"
echo "Output directory: $BASE_DIR"
echo "Regions: 19 | Frequency: 70 MHz – 6 GHz"
echo

# Regions 1–13: use stable sub-2 GHz settings
LOW_GAIN=35
LOW_REPEATS=5
LOW_R="-r 1M -w 2M -B 250e3 -n $LOW_REPEATS -g $LOW_GAIN"
# PREV: LOW_R="-r 2M -w 2M -B 250e3 -n 5"

# Regions 14–19: use stable >=2 GHz settings
HIGH_GAIN=45
HIGH_REPEATS=10
HIGH_R="-r 5M -w 5M -B 250e3 -n $HIGH_REPEATS -g $HIGH_GAIN"
# PREV: HIGH_R="-r 10M -w 10M -B 250e3 -n 5"

echo
echo "[1/19] 70–200 MHz"
soapy_power --device="$DEVICE" -f 70M:200M   $LOW_R -O "$BASE_DIR/${CONDITION}_01_070_200.csv"

echo
echo "[2/19] 200–400 MHz"
soapy_power --device="$DEVICE" -f 200M:400M  $LOW_R -O "$BASE_DIR/${CONDITION}_02_200_400.csv"

echo
echo "[3/19] 400–480 MHz"
soapy_power --device="$DEVICE" -f 400M:480M  $LOW_R -O "$BASE_DIR/${CONDITION}_03_400_480.csv"

echo
echo "[4/19] 480–700 MHz"
soapy_power --device="$DEVICE" -f 480M:700M  $LOW_R -O "$BASE_DIR/${CONDITION}_04_480_700.csv"

echo
echo "[5/19] 700–870 MHz"
soapy_power --device="$DEVICE" -f 700M:870M  $LOW_R -O "$BASE_DIR/${CONDITION}_05_700_870.csv"

echo
echo "[6/19] 870–1000 MHz"
soapy_power --device="$DEVICE" -f 870M:1000M $LOW_R -O "$BASE_DIR/${CONDITION}_06_870_1000.csv"

echo
echo "[7/19] 1000–1300 MHz"
soapy_power --device="$DEVICE" -f 1000M:1300M $LOW_R -O "$BASE_DIR/${CONDITION}_07_1000_1300.csv"

echo
echo "[8/19] 1300–1575 MHz"
soapy_power --device="$DEVICE" -f 1300M:1575M $LOW_R -O "$BASE_DIR/${CONDITION}_08_1300_1575.csv"

echo
echo "[9/19] 1575–1600 MHz"
soapy_power --device="$DEVICE" -f 1575M:1600M $LOW_R -O "$BASE_DIR/${CONDITION}_09_1575_1600.csv"

echo
echo "[10/19] 1600–1710 MHz"
soapy_power --device="$DEVICE" -f 1600M:1710M $LOW_R -O "$BASE_DIR/${CONDITION}_10_1600_1710.csv"

echo
echo "[11/19] 1710–1900 MHz"
soapy_power --device="$DEVICE" -f 1710M:1900M $LOW_R -O "$BASE_DIR/${CONDITION}_11_1710_1900.csv"

echo
echo "[12/19] 1900–2170 MHz"
soapy_power --device="$DEVICE" -f 1900M:2170M $LOW_R -O "$BASE_DIR/${CONDITION}_12_1900_2170.csv"

echo
echo "[13/19] 2170–2400 MHz"
soapy_power --device="$DEVICE" -f 2170M:2400M $LOW_R -O "$BASE_DIR/${CONDITION}_13_2170_2400.csv"

echo
echo "[14/19] 2400–2510 MHz"
soapy_power --device="$DEVICE" -f 2400M:2510M $HIGH_R -O "$BASE_DIR/${CONDITION}_14_2400_2510.csv"

echo
echo "[15/19] 2510–2700 MHz"
soapy_power --device="$DEVICE" -f 2510M:2700M $HIGH_R -O "$BASE_DIR/${CONDITION}_15_2510_2700.csv"

echo
echo "[16/19] 2700–3800 MHz"
soapy_power --device="$DEVICE" -f 2700M:3800M $HIGH_R -O "$BASE_DIR/${CONDITION}_16_2700_3800.csv"

echo
echo "[17/19] 3800–5150 MHz"
soapy_power --device="$DEVICE" -f 3800M:5150M $HIGH_R -O "$BASE_DIR/${CONDITION}_17_3800_5150.csv"

echo
echo "[18/19] 5150–5470 MHz"
soapy_power --device="$DEVICE" -f 5150M:5470M $HIGH_R -O "$BASE_DIR/${CONDITION}_18_5150_5470.csv"

echo
echo "[19/19] 5470–6000 MHz"
soapy_power --device="$DEVICE" -f 5470M:6000M $HIGH_R -O "$BASE_DIR/${CONDITION}_19_5470_6000.csv"

echo
echo "[DONE] All 19 regions complete."
echo "CSV files saved in: $BASE_DIR"
printf "Total execution time: %02d:%02d:%02d\n" \
    $((SECONDS/3600)) $((SECONDS%3600/60)) $((SECONDS%60))
echo
echo "Quick summary of output files:"
ls -lh "$BASE_DIR"/*.csv 2>/dev/null | awk '{print "  "$5, $9}' || echo "  (no files found)"
echo
