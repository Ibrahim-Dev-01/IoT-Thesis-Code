#!/usr/bin/env python3
"""
RF Spectrum Analyzer — IoT Emissions Lab
Desktop application for soapy_power CSV analysis.

Requirements:
    pip install matplotlib numpy pandas scipy reportlab

Usage:
    python spectrum_analyzer.py
"""

import sys
import os
import csv
import glob
import json
import statistics
import threading
import pathlib
from datetime import datetime
from collections import defaultdict

import numpy as np
import matplotlib

# Try GUI backends in order of preference
_backends = ["TkAgg", "Qt5Agg", "Qt6Agg", "WxAgg", "GTK3Agg"]
_backend_set = False
for _b in _backends:
    try:
        matplotlib.use(_b)
        import matplotlib.pyplot as _plt_test
        _plt_test.figure()          # will raise if display missing
        _plt_test.close("all")
        _backend_set = True
        print(f"Using GUI backend: {_b}")
        break
    except Exception:
        pass

if not _backend_set:
    print("WARNING: No display found. Install tkinter (python3-tk) or PyQt5.")
    print("         On Ubuntu: sudo apt install python3-tk")
    print("         On macOS:  brew install python-tk")
    sys.exit(1)

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, CheckButtons, RadioButtons, Slider
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# Backend-specific imports — loaded lazily when GUI starts
_FigureCanvasTkAgg = None
_NavigationToolbar2Tk = None

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":       "#0d0f12",
    "panel":    "#13161b",
    "border":   "#1f2530",
    "text":     "#cdd6e8",
    "muted":    "#4a5568",
    "accent":   "#00d4aa",
    "blue":     "#378ADD",
    "red":      "#ef4444",
    "amber":    "#f59e0b",
    "green":    "#10b981",
    "purple":   "#8b5cf6",
    "baseline": "#8892a0",
    "idle":     "#378ADD",
    "active_call": "#ef4444",
    "active_music": "#f59e0b",
}

COND_COLORS = {
    "baseline":     C["baseline"],
    "idle":         C["idle"],
    "active_call":  C["active_call"],
    "active_music": C["active_music"],
}

COND_LABELS = {
    "baseline":     "Baseline (no device)",
    "idle":         "Idle (device standby)",
    "active_call":  "Active — phone call",
    "active_music": "Active — music",
}

# ── Known protocol bands ──────────────────────────────────────────────────────
BANDS = [
    {"name": "LTE 700",      "flo":  698, "fhi":  806, "color": "#378ADD", "alpha": 0.08},
    {"name": "LTE 800",      "flo":  806, "fhi":  862, "color": "#378ADD", "alpha": 0.06},
    {"name": "GSM 900",      "flo":  880, "fhi":  960, "color": "#f59e0b", "alpha": 0.09},
    {"name": "Zigbee 915",   "flo":  902, "fhi":  928, "color": "#10b981", "alpha": 0.08},
    {"name": "GPS L1",       "flo": 1574, "fhi": 1577, "color": "#8b5cf6", "alpha": 0.25},
    {"name": "LTE 1800",     "flo": 1710, "fhi": 1880, "color": "#378ADD", "alpha": 0.08},
    {"name": "UMTS/3G",      "flo": 1920, "fhi": 2170, "color": "#8b5cf6", "alpha": 0.07},
    {"name": "WiFi 2.4G",    "flo": 2400, "fhi": 2484, "color": "#ef4444", "alpha": 0.10},
    {"name": "Bluetooth",    "flo": 2402, "fhi": 2480, "color": "#ef4444", "alpha": 0.05},
    {"name": "LTE 2600",     "flo": 2500, "fhi": 2690, "color": "#378ADD", "alpha": 0.06},
    {"name": "WiFi 5G",      "flo": 5170, "fhi": 5835, "color": "#10b981", "alpha": 0.08},
]

ZOOM_PRESETS = {
    "Full (70 MHz – 6 GHz)": (70,    6000),
    "Sub-1 GHz":              (70,    1000),
    "700–870 MHz (LTE)":      (700,   870),
    "870–1000 MHz (GSM/Zigbee)": (870, 1000),
    "1710–1900 MHz (LTE B3)": (1710,  1900),
    "1900–2200 MHz (UMTS)":   (1900,  2200),
    "2400–2510 MHz (BT/WiFi)":(2400,  2510),
    "2.49 GHz detail":        (2470,  2510),
    "5150–5850 MHz (WiFi 5G)":(5150,  5850),
}


# ── CSV parser ────────────────────────────────────────────────────────────────

def parse_soapy_csv(filepath):
    """Parse a soapy_power CSV. Returns list of (freq_mhz, power_dbm)."""
    rows = []
    with open(filepath, newline="", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 7:
                continue
            try:
                flo = float(parts[2]) / 1e6
                fhi = float(parts[3]) / 1e6
                fmid = (flo + fhi) / 2
                pwrs = [float(x) for x in parts[6:] if x.strip()]
                if pwrs:
                    rows.append((fmid, sum(pwrs) / len(pwrs)))
            except (ValueError, IndexError):
                continue
    return rows


def merge_rows(rows):
    """Average duplicate frequencies, return sorted list."""
    seen = defaultdict(list)
    for f, p in rows:
        seen[round(f, 3)].append(p)
    merged = [(f, sum(ps) / len(ps)) for f, ps in seen.items()]
    return sorted(merged, key=lambda x: x[0])


def detect_peaks(data, noise_floor, thresh_db=10):
    """Return list of (freq, power, delta_above_noise) for local maxima."""
    if len(data) < 3:
        return []
    threshold = noise_floor + thresh_db
    peaks = []
    for i in range(1, len(data) - 1):
        f, p = data[i]
        if p > threshold and p >= data[i-1][1] and p >= data[i+1][1]:
            peaks.append((round(f, 2), round(p, 2), round(p - noise_floor, 2)))
    return sorted(peaks, key=lambda x: -x[2])


def near_band(freq):
    """Return name of known band at frequency, or None."""
    for b in BANDS:
        if b["flo"] - 5 <= freq <= b["fhi"] + 5:
            return b["name"]
    return None


def noise_floor(data):
    if not data:
        return -130.0
    return statistics.median([p for _, p in data])


# ── Data store ────────────────────────────────────────────────────────────────

class SpectrumStore:
    def __init__(self):
        self.conditions = {}   # cond_name -> [(freq, power), ...]
        self.noise_floors = {} # cond_name -> float

    def load_files(self, filepaths, cond_name, progress_cb=None):
        all_rows = []
        for i, fp in enumerate(filepaths):
            all_rows.extend(parse_soapy_csv(fp))
            if progress_cb:
                progress_cb(i + 1, len(filepaths))
        merged = merge_rows(all_rows)
        self.conditions[cond_name] = merged
        self.noise_floors[cond_name] = noise_floor(merged)
        return len(merged)

    def get_data(self, cond, freq_range=None):
        data = self.conditions.get(cond, [])
        if freq_range:
            lo, hi = freq_range
            data = [(f, p) for f, p in data if lo <= f <= hi]
        return data

    def compute_delta(self, cond_a, cond_b, freq_range=None):
        """Return (freqs, deltas) for cond_b - cond_a."""
        a = dict(self.get_data(cond_a, freq_range))
        b = dict(self.get_data(cond_b, freq_range))
        common = sorted(set(round(f, 3) for f in a) & set(round(f, 3) for f in b))
        freqs = common
        deltas = [round(b[f] - a[f], 2) for f in common]
        return freqs, deltas

    def get_peaks(self, cond, thresh_db=10, freq_range=None):
        data = self.get_data(cond, freq_range)
        nf = self.noise_floors.get(cond, -126.0)
        return detect_peaks(data, nf, thresh_db)

    def new_peaks_vs_baseline(self, cond, thresh_db=10):
        """Peaks in cond that are not peaks in baseline."""
        if "baseline" not in self.conditions:
            return self.get_peaks(cond, thresh_db)
        base_peaks = set(round(f, 2) for f, p, d in self.get_peaks("baseline", thresh_db - 2))
        return [(f, p, d) for f, p, d in self.get_peaks(cond, thresh_db)
                if round(f, 2) not in base_peaks]


# ── PDF Report ────────────────────────────────────────────────────────────────

def export_pdf(store, output_path, thresh_db=10):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold",
                                 textColor=colors.HexColor("#00d4aa"), spaceAfter=4)
    h2_style    = ParagraphStyle("h2",    fontSize=11, fontName="Helvetica-Bold",
                                 textColor=colors.HexColor("#cdd6e8"), spaceBefore=10, spaceAfter=4)
    body_style  = ParagraphStyle("body",  fontSize=9,  fontName="Helvetica",
                                 textColor=colors.HexColor("#8892a0"), leading=14)
    mono_style  = ParagraphStyle("mono",  fontSize=8,  fontName="Courier",
                                 textColor=colors.HexColor("#cdd6e8"))

    story = []

    # Header
    story.append(Paragraph("RF SPECTRUM ANALYZER — IoT EMISSIONS LAB", title_style))
    story.append(Paragraph(f"Phase 1 Analysis Report · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1f2530"), spaceAfter=8))

    # Scan summary table
    story.append(Paragraph("Scan Summary", h2_style))
    sum_data = [["Condition", "Data points", "Noise floor", "Peaks (>+10 dB)", "Peak power"]]
    for cond, data in store.conditions.items():
        nf = store.noise_floors.get(cond, -130)
        peaks = detect_peaks(data, nf, thresh_db)
        peak_p = max((p for _, p in data), default=-999)
        sum_data.append([
            COND_LABELS.get(cond, cond),
            f"{len(data):,}",
            f"{nf:.1f} dBm",
            str(len(peaks)),
            f"{peak_p:.1f} dBm",
        ])
    ts = TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#13161b")),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.HexColor("#00d4aa")),
        ("TEXTCOLOR",   (0,1), (-1,-1), colors.HexColor("#cdd6e8")),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("FONTNAME",    (0,1), (-1,-1), "Courier"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#0d0f12"), colors.HexColor("#13161b")]),
        ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#1f2530")),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ])
    story.append(Table(sum_data, colWidths=[55*mm, 30*mm, 30*mm, 30*mm, 28*mm],
                       style=ts))
    story.append(Spacer(1, 8))

    # Peaks per condition
    for cond, data in store.conditions.items():
        nf = store.noise_floors.get(cond, -130)
        peaks = detect_peaks(data, nf, thresh_db)
        if not peaks:
            continue
        story.append(Paragraph(f"Anomalous Peaks — {COND_LABELS.get(cond, cond)}", h2_style))
        pdata = [["Frequency", "Power (dBm)", "Δ above noise", "Known band", "Severity"]]
        for f, p, d in peaks[:40]:
            band = near_band(f) or "UNKNOWN"
            sev = "CRITICAL" if d > 30 else "HIGH" if d > 20 else "MEDIUM" if d > 15 else "LOW"
            fstr = f"{f:.1f} MHz" if f < 1000 else f"{f/1000:.3f} GHz"
            pdata.append([fstr, f"{p:.1f}", f"+{d:.1f} dB", band, sev])
        sev_colors = {"CRITICAL": "#A32D2D", "HIGH": "#A32D2D", "MEDIUM": "#854F0B",
                      "LOW": "#085041", "UNKNOWN": "#185FA5"}
        peak_ts = TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#13161b")),
            ("TEXTCOLOR",   (0,0), (-1,0),  colors.HexColor("#00d4aa")),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("FONTNAME",    (0,1), (-1,-1), "Courier"),
            ("TEXTCOLOR",   (0,1), (0,-1),  colors.HexColor("#00d4aa")),
            ("TEXTCOLOR",   (1,1), (2,-1),  colors.HexColor("#cdd6e8")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#0d0f12"), colors.HexColor("#13161b")]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#1f2530")),
            ("ALIGN",       (1,0), (-1,-1), "CENTER"),
            ("TOPPADDING",  (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ])
        # Colour severity column
        for row_i, (f, p, d, *_) in enumerate(peaks[:40], start=1):
            sev = "CRITICAL" if d > 30 else "HIGH" if d > 20 else "MEDIUM" if d > 15 else "LOW"
            col = sev_colors.get(sev, "#cdd6e8")
            peak_ts.add("TEXTCOLOR", (4, row_i), (4, row_i), colors.HexColor(col))
            band = near_band(f)
            if band is None:
                peak_ts.add("TEXTCOLOR", (3, row_i), (3, row_i), colors.HexColor("#E24B4A"))

        story.append(Table(pdata, colWidths=[38*mm, 28*mm, 28*mm, 44*mm, 25*mm],
                           style=peak_ts))
        story.append(Spacer(1, 6))

    doc.build(story)


# ── Main Application ──────────────────────────────────────────────────────────

class SpectrumApp:
    def __init__(self):
        self.store = SpectrumStore()
        self.thresh_db = 10
        self.show_bands = True
        self.zoom = (70, 6000)
        self.active_tab = "spectrum"
        self.compare_conds = []   # which conditions to overlay

        self._build_window()

    # ── Window / layout ──────────────────────────────────────────────────────

    def _build_window(self):
        plt.rcParams.update({
            "figure.facecolor":  C["bg"],
            "axes.facecolor":    C["panel"],
            "axes.edgecolor":    C["border"],
            "axes.labelcolor":   C["muted"],
            "xtick.color":       C["muted"],
            "ytick.color":       C["muted"],
            "text.color":        C["text"],
            "grid.color":        C["border"],
            "grid.linewidth":    0.5,
            "font.family":       "monospace",
            "font.size":         9,
        })

        self.fig = plt.figure(figsize=(16, 9), facecolor=C["bg"])
        self.fig.canvas.manager.set_window_title("RF Spectrum Analyzer — IoT Emissions Lab")

        # ── Main layout: sidebar | chart area
        outer = gridspec.GridSpec(1, 2, figure=self.fig,
                                  left=0.0, right=1.0, top=1.0, bottom=0.0,
                                  width_ratios=[0.22, 0.78], wspace=0.0)

        self.sidebar_ax = self.fig.add_subplot(outer[0])
        self.sidebar_ax.set_facecolor(C["panel"])
        for sp in self.sidebar_ax.spines.values():
            sp.set_color(C["border"])
        self.sidebar_ax.set_xticks([])
        self.sidebar_ax.set_yticks([])

        # ── Right: title bar + tab bar + main chart + status bar
        right = gridspec.GridSpecFromSubplotSpec(4, 1, subplot_spec=outer[1],
            height_ratios=[0.045, 0.045, 0.87, 0.04], hspace=0.0)

        self.title_ax  = self.fig.add_subplot(right[0])
        self.tabbar_ax = self.fig.add_subplot(right[1])
        self.chart_ax  = self.fig.add_subplot(right[2])
        self.status_ax = self.fig.add_subplot(right[3])

        for ax in [self.title_ax, self.tabbar_ax, self.status_ax]:
            ax.set_facecolor(C["panel"])
            for sp in ax.spines.values():
                sp.set_color(C["border"])
            ax.set_xticks([])
            ax.set_yticks([])

        self.chart_ax.set_facecolor(C["bg"])
        for sp in self.chart_ax.spines.values():
            sp.set_color(C["border"])

        self._draw_title_bar()
        self._draw_sidebar()
        self._draw_tab_bar()
        self._draw_empty_chart()
        self._draw_status("Ready — load CSV files to begin")

        self.fig.canvas.mpl_connect("resize_event", self._on_resize)
        plt.tight_layout(pad=0)
        plt.show()

    # ── Title bar ────────────────────────────────────────────────────────────

    def _draw_title_bar(self):
        ax = self.title_ax
        ax.clear()
        ax.set_facecolor(C["panel"])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        # scanning line animation feel
        ax.axhline(0.0, color=C["border"], lw=1)
        ax.text(0.012, 0.5, "⌗  RF SPECTRUM ANALYZER", va="center",
                color=C["accent"], fontsize=10, fontweight="bold", fontfamily="monospace")
        ax.text(0.4, 0.5, "IoT EMISSIONS LAB — PHASE 1", va="center",
                color=C["muted"], fontsize=8, fontfamily="monospace")
        ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        ax.text(0.98, 0.5, ts, va="center", ha="right",
                color=C["muted"], fontsize=8, fontfamily="monospace")
        self.fig.canvas.draw_idle()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _draw_sidebar(self):
        ax = self.sidebar_ax
        ax.clear()
        ax.set_facecolor(C["panel"])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(C["border"])

        y = 0.97

        def section(label, yy):
            ax.text(0.05, yy, label, color=C["muted"], fontsize=7.5,
                    fontfamily="monospace", fontweight="bold",
                    transform=ax.transAxes)
            ax.axhline(yy - 0.012, color=C["border"], lw=0.5,
                       xmin=0.04, xmax=0.96, transform=ax.transAxes)

        def stat_row(label, value, color, yy):
            ax.text(0.05, yy, label, color=C["muted"], fontsize=8,
                    fontfamily="monospace", va="top", transform=ax.transAxes)
            ax.text(0.95, yy, value, color=color, fontsize=9,
                    fontfamily="monospace", va="top", ha="right",
                    fontweight="bold", transform=ax.transAxes)

        # ── Loaded conditions
        section("DATA LOADED", y - 0.01)
        y -= 0.06
        if not self.store.conditions:
            ax.text(0.05, y, "No files loaded", color=C["muted"],
                    fontsize=8, fontfamily="monospace", va="top",
                    transform=ax.transAxes)
            y -= 0.04
        else:
            for cond, data in self.store.conditions.items():
                col = COND_COLORS.get(cond, C["text"])
                nf  = self.store.noise_floors.get(cond, -130)
                ax.add_patch(FancyBboxPatch((0.03, y - 0.048), 0.94, 0.05,
                    boxstyle="round,pad=0.005", linewidth=0.5,
                    edgecolor=col, facecolor=C["bg"],
                    transform=ax.transAxes))
                ax.text(0.07, y - 0.008, COND_LABELS.get(cond, cond),
                        color=col, fontsize=7.5, fontfamily="monospace",
                        va="top", fontweight="bold", transform=ax.transAxes)
                ax.text(0.07, y - 0.028, f"{len(data):,} pts · NF {nf:.1f} dBm",
                        color=C["muted"], fontsize=7, fontfamily="monospace",
                        va="top", transform=ax.transAxes)
                y -= 0.065

        y -= 0.01
        # ── Statistics for active zoom
        section("STATISTICS", y - 0.01)
        y -= 0.06
        active_conds = list(self.store.conditions.keys())
        if active_conds:
            cond = active_conds[0]
            data = self.store.get_data(cond, self.zoom)
            nf   = self.store.noise_floors.get(cond, -130)
            peaks = detect_peaks(data, nf, self.thresh_db)
            peak_p = max((p for _, p in data), default=-130)
            stat_row("Noise floor",  f"{nf:.1f} dBm",      C["accent"],  y);       y -= 0.045
            stat_row("Peak power",   f"{peak_p:.1f} dBm",  C["amber"],   y);       y -= 0.045
            stat_row("Anomalies",    str(len(peaks)),       C["red"],     y);       y -= 0.045
            stat_row("Points",       f"{len(data):,}",      C["blue"],    y);       y -= 0.045

        y -= 0.01
        # ── Zoom presets
        section("ZOOM PRESETS", y - 0.01)
        y -= 0.055
        self._zoom_buttons_y = {}
        for label, rng in ZOOM_PRESETS.items():
            is_active = (rng == self.zoom)
            col = C["accent"] if is_active else C["muted"]
            bg  = C["bg"] if is_active else "none"
            ax.text(0.05, y, f"▸ {label}", color=col, fontsize=7.5,
                    fontfamily="monospace", va="top", transform=ax.transAxes,
                    picker=True)
            self._zoom_buttons_y[y] = rng
            y -= 0.04

        y -= 0.01
        # ── Threshold
        section("THRESHOLD", y - 0.01)
        y -= 0.05
        ax.text(0.05, y, f"Anomaly threshold:  +{self.thresh_db} dB above noise",
                color=C["muted"], fontsize=7.5, fontfamily="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.035
        ax.text(0.05, y, "Use [ and ] keys to adjust",
                color=C["border"], fontsize=7, fontfamily="monospace",
                va="top", transform=ax.transAxes)

        y -= 0.06
        # ── Actions
        section("ACTIONS", y - 0.01)
        y -= 0.05

        btn_labels = [
            ("[L] Load baseline",      "load_baseline"),
            ("[I] Load idle",          "load_idle"),
            ("[C] Load active call",   "load_call"),
            ("[M] Load active music",  "load_music"),
            ("[P] Export PDF report",  "export_pdf"),
            ("[X] Clear all data",     "clear"),
        ]
        self._action_btns = {}
        for label, key in btn_labels:
            ax.text(0.05, y, label, color=C["blue"], fontsize=7.5,
                    fontfamily="monospace", va="top", transform=ax.transAxes,
                    picker=True)
            self._action_btns[y] = key
            y -= 0.038

        # ── Legend
        if self.store.conditions:
            y -= 0.01
            section("LEGEND", y - 0.01)
            y -= 0.05
            for cond in self.store.conditions:
                col = COND_COLORS.get(cond, C["text"])
                ax.add_patch(mpatches.Rectangle((0.05, y - 0.01), 0.07, 0.016,
                    color=col, transform=ax.transAxes))
                ax.text(0.15, y, COND_LABELS.get(cond, cond),
                        color=C["muted"], fontsize=7, fontfamily="monospace",
                        va="top", transform=ax.transAxes)
                y -= 0.032

        self.fig.canvas.mpl_connect("pick_event", self._on_pick)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    # ── Tab bar ───────────────────────────────────────────────────────────────

    def _draw_tab_bar(self):
        ax = self.tabbar_ax
        ax.clear()
        ax.set_facecolor(C["panel"])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        ax.axhline(0.0, color=C["border"], lw=1)

        tabs = [
            ("spectrum",  "SPECTRUM"),
            ("anomaly",   "ANOMALIES"),
            ("compare",   "COMPARE"),
            ("delta",     "DELTA"),
            ("peaks",     "PEAK TABLE"),
        ]
        w = 1.0 / len(tabs)
        self._tab_positions = {}
        for i, (key, label) in enumerate(tabs):
            x = i * w + w / 2
            is_active = (key == self.active_tab)
            col = C["accent"] if is_active else C["muted"]
            ax.text(x, 0.55, label, color=col, ha="center", va="center",
                    fontsize=8.5, fontweight="bold" if is_active else "normal",
                    fontfamily="monospace", picker=True)
            if is_active:
                ax.axhline(0.05, color=C["accent"], lw=2,
                           xmin=i*w + 0.01, xmax=(i+1)*w - 0.01)
            self._tab_positions[(i*w, (i+1)*w)] = key

    # ── Status bar ────────────────────────────────────────────────────────────

    def _draw_status(self, msg, color=None):
        ax = self.status_ax
        ax.clear()
        ax.set_facecolor(C["panel"])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        ax.axhline(1.0, color=C["border"], lw=0.5)
        ax.text(0.01, 0.45, msg, color=color or C["muted"],
                fontsize=7.5, fontfamily="monospace", va="center")
        zoom_str = (f"{self.zoom[0]} MHz – {self.zoom[1] if self.zoom[1]<1000 else f'{self.zoom[1]/1000:.1f} GHz'}")
        ax.text(0.99, 0.45, f"zoom: {zoom_str}  |  thresh: +{self.thresh_db} dB",
                color=C["muted"], fontsize=7.5, fontfamily="monospace",
                va="center", ha="right")
        self.fig.canvas.draw_idle()

    # ── Chart rendering ───────────────────────────────────────────────────────

    def _draw_empty_chart(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.text(0.5, 0.5, "Load CSV files to begin analysis",
                ha="center", va="center", color=C["muted"],
                fontsize=12, fontfamily="monospace", transform=ax.transAxes)
        self.fig.canvas.draw_idle()

    def _add_band_overlays(self, ax, zoom):
        if not self.show_bands:
            return
        lo, hi = zoom
        for b in BANDS:
            if b["fhi"] < lo or b["flo"] > hi:
                continue
            x0 = max(b["flo"], lo)
            x1 = min(b["fhi"], hi)
            ax.axvspan(x0, x1, alpha=b["alpha"], color=b["color"], linewidth=0)

    def _fmt_freq(self, f):
        return f"{f:.1f} MHz" if f < 1000 else f"{f/1000:.3f} GHz"

    def render(self):
        """Dispatch to correct render method based on active tab."""
        tab = self.active_tab
        if tab == "spectrum":
            self._render_spectrum()
        elif tab == "anomaly":
            self._render_anomaly()
        elif tab == "compare":
            self._render_compare()
        elif tab == "delta":
            self._render_delta()
        elif tab == "peaks":
            self._render_peak_table()
        self._draw_sidebar()
        self._draw_tab_bar()

    def _render_spectrum(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.grid(True, alpha=0.3, linewidth=0.4)

        if not self.store.conditions:
            ax.text(0.5, 0.5, "No data loaded", ha="center", va="center",
                    color=C["muted"], fontsize=11, transform=ax.transAxes)
            self.fig.canvas.draw_idle()
            return

        lo, hi = self.zoom
        self._add_band_overlays(ax, self.zoom)

        for cond, data in self.store.conditions.items():
            d = [(f, p) for f, p in data if lo <= f <= hi]
            if not d:
                continue
            freqs = [x[0] for x in d]
            pwrs  = [x[1] for x in d]
            col   = COND_COLORS.get(cond, C["text"])
            ax.plot(freqs, pwrs, color=col, lw=1.1, alpha=0.85,
                    label=COND_LABELS.get(cond, cond))
            # Threshold line
            nf = self.store.noise_floors.get(cond, -126)
            ax.axhline(nf + self.thresh_db, color=col, lw=0.6,
                       ls=(0, (4, 4)), alpha=0.4)

        # Band labels along top
        for b in BANDS:
            mid = (b["flo"] + b["fhi"]) / 2
            if lo <= mid <= hi:
                ax.text(mid, ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else -90,
                        b["name"], color=b["color"], fontsize=6.5, ha="center",
                        va="top", rotation=90, alpha=0.7, fontfamily="monospace")

        ax.set_xlabel("Frequency", color=C["muted"], fontsize=9)
        ax.set_ylabel("Power (dBm)", color=C["muted"], fontsize=9)
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.1f}G" if x >= 1000 else f"{x:.0f}M"))
        leg = ax.legend(loc="lower right", facecolor=C["panel"],
                        edgecolor=C["border"], fontsize=8, framealpha=0.9)
        for t in leg.get_texts():
            t.set_color(C["text"])
        self.fig.canvas.draw_idle()

    def _render_anomaly(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.grid(True, alpha=0.3, linewidth=0.4)

        if not self.store.conditions:
            ax.text(0.5, 0.5, "No data loaded", ha="center", va="center",
                    color=C["muted"], fontsize=11, transform=ax.transAxes)
            self.fig.canvas.draw_idle()
            return

        lo, hi = self.zoom
        self._add_band_overlays(ax, self.zoom)

        for cond, data in self.store.conditions.items():
            d = [(f, p) for f, p in data if lo <= f <= hi]
            if not d:
                continue
            freqs = [x[0] for x in d]
            pwrs  = [x[1] for x in d]
            col = COND_COLORS.get(cond, C["text"])
            ax.plot(freqs, pwrs, color=col, lw=0.7, alpha=0.35)
            nf = self.store.noise_floors.get(cond, -126)
            peaks = detect_peaks(d, nf, self.thresh_db)
            if peaks:
                pf = [p[0] for p in peaks]
                pp = [p[1] for p in peaks]
                ax.scatter(pf, pp, color=col, s=25, zorder=5,
                           label=f"{COND_LABELS.get(cond, cond)} peaks")
                # Annotate top-5 peaks
                for f, p, d_ in peaks[:5]:
                    fstr = self._fmt_freq(f)
                    ax.annotate(f"{fstr}\n{p:.1f} dBm (+{d_:.0f}dB)",
                                xy=(f, p), xytext=(0, 12),
                                textcoords="offset points",
                                color=col, fontsize=6.5, ha="center",
                                fontfamily="monospace",
                                arrowprops=dict(arrowstyle="-", color=col,
                                                lw=0.6, alpha=0.5))

        ax.set_xlabel("Frequency", color=C["muted"], fontsize=9)
        ax.set_ylabel("Power (dBm)", color=C["muted"], fontsize=9)
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.1f}G" if x >= 1000 else f"{x:.0f}M"))
        leg = ax.legend(loc="lower right", facecolor=C["panel"],
                        edgecolor=C["border"], fontsize=8)
        for t in leg.get_texts():
            t.set_color(C["text"])
        self.fig.canvas.draw_idle()

    def _render_compare(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.grid(True, alpha=0.3, linewidth=0.4)

        conds = list(self.store.conditions.keys())
        if len(conds) < 2:
            ax.text(0.5, 0.5, "Load at least 2 conditions to compare",
                    ha="center", va="center", color=C["muted"],
                    fontsize=11, transform=ax.transAxes)
            self.fig.canvas.draw_idle()
            return

        lo, hi = self.zoom
        self._add_band_overlays(ax, self.zoom)

        # Bin data into ~300 bins for clean overlay
        bins = np.linspace(lo, hi, 300)
        bin_w = bins[1] - bins[0]

        for cond in conds:
            data = self.store.get_data(cond, (lo, hi))
            if not data:
                continue
            binned = []
            for b in bins:
                slice_ = [p for f, p in data if b <= f < b + bin_w]
                binned.append(np.mean(slice_) if slice_ else np.nan)
            col = COND_COLORS.get(cond, C["text"])
            ax.plot(bins, binned, color=col, lw=1.3, alpha=0.9,
                    label=COND_LABELS.get(cond, cond))

        ax.set_xlabel("Frequency", color=C["muted"], fontsize=9)
        ax.set_ylabel("Power (dBm)", color=C["muted"], fontsize=9)
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.1f}G" if x >= 1000 else f"{x:.0f}M"))
        leg = ax.legend(loc="lower right", facecolor=C["panel"],
                        edgecolor=C["border"], fontsize=8)
        for t in leg.get_texts():
            t.set_color(C["text"])
        ax.set_title("Condition Overlay — peaks that appear only in active scans are device emissions",
                     color=C["muted"], fontsize=8, pad=6)
        self.fig.canvas.draw_idle()

    def _render_delta(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.grid(True, alpha=0.3, linewidth=0.4)

        conds = [c for c in self.store.conditions if c != "baseline"]
        if "baseline" not in self.store.conditions or not conds:
            ax.text(0.5, 0.5,
                    "Load baseline + at least one other condition\nto see delta",
                    ha="center", va="center", color=C["muted"],
                    fontsize=11, transform=ax.transAxes)
            self.fig.canvas.draw_idle()
            return

        lo, hi = self.zoom
        self._add_band_overlays(ax, self.zoom)
        ax.axhline(0, color=C["border"], lw=0.8)

        for cond in conds:
            freqs, deltas = self.store.compute_delta("baseline", cond, (lo, hi))
            if not freqs:
                continue
            col = COND_COLORS.get(cond, C["text"])
            # Colour bars by sign
            pos_d = [d if d > 0 else 0 for d in deltas]
            neg_d = [d if d < 0 else 0 for d in deltas]
            ax.fill_between(freqs, pos_d, 0, color=col, alpha=0.5,
                            label=f"{COND_LABELS.get(cond, cond)} (positive)")
            ax.fill_between(freqs, neg_d, 0, color=C["muted"], alpha=0.2)
            ax.plot(freqs, deltas, color=col, lw=0.6, alpha=0.6)

        ax.set_xlabel("Frequency", color=C["muted"], fontsize=9)
        ax.set_ylabel("Δ Power (dB)", color=C["muted"], fontsize=9)
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.1f}G" if x >= 1000 else f"{x:.0f}M"))
        leg = ax.legend(loc="lower right", facecolor=C["panel"],
                        edgecolor=C["border"], fontsize=8)
        for t in leg.get_texts():
            t.set_color(C["text"])
        ax.set_title("Delta (condition − baseline) · positive = device emission above background",
                     color=C["muted"], fontsize=8, pad=6)
        self.fig.canvas.draw_idle()

    def _render_peak_table(self):
        ax = self.chart_ax
        ax.clear()
        ax.set_facecolor(C["bg"])
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(C["border"])

        if not self.store.conditions:
            ax.text(0.5, 0.5, "No data loaded", ha="center", va="center",
                    color=C["muted"], fontsize=11, transform=ax.transAxes)
            self.fig.canvas.draw_idle()
            return

        # Build rows
        rows = []
        for cond, data in self.store.conditions.items():
            nf = self.store.noise_floors.get(cond, -126)
            peaks = detect_peaks(data, nf, self.thresh_db)
            for f, p, d in peaks[:20]:
                band = near_band(f) or "UNKNOWN"
                sev  = "CRITICAL" if d > 30 else "HIGH" if d > 20 else "MEDIUM" if d > 15 else "LOW"
                fstr = self._fmt_freq(f)
                cond_short = cond.replace("active_", "").upper()
                rows.append((fstr, f"{p:.1f}", f"+{d:.1f} dB", band, sev, cond_short))

        rows.sort(key=lambda r: -float(r[2].replace("+","").replace(" dB","")))

        headers = ["Frequency", "Power (dBm)", "Δ above noise", "Band", "Severity", "Condition"]
        col_w   = [0.14, 0.12, 0.14, 0.24, 0.12, 0.12]
        x_pos   = [sum(col_w[:i]) + col_w[i]/2 for i in range(len(col_w))]
        y_start = 0.95
        row_h   = 0.032

        # Header row
        for j, (hdr, x) in enumerate(zip(headers, x_pos)):
            ax.text(x + 0.02, y_start, hdr, color=C["accent"], fontsize=7.5,
                    fontfamily="monospace", fontweight="bold", va="top",
                    transform=ax.transAxes)
        ax.axhline(y_start - row_h, color=C["border"], lw=0.8,
                   xmin=0.02, xmax=0.98, transform=ax.transAxes)

        sev_colors = {
            "CRITICAL": C["red"],
            "HIGH":     C["red"],
            "MEDIUM":   C["amber"],
            "LOW":      C["green"],
        }

        max_rows = int((y_start - 0.05) / row_h)
        for i, row in enumerate(rows[:max_rows]):
            y = y_start - (i + 1.5) * row_h
            bg = C["bg"] if i % 2 == 0 else C["panel"]
            ax.add_patch(mpatches.Rectangle((0.02, y - row_h*0.4), 0.96, row_h * 0.9,
                color=bg, transform=ax.transAxes, zorder=0))
            for j, (val, x) in enumerate(zip(row, x_pos)):
                if j == 0:
                    col = C["accent"]
                elif j == 4:
                    col = sev_colors.get(val, C["text"])
                elif j == 3 and val == "UNKNOWN":
                    col = C["red"]
                elif j == 5:
                    col = COND_COLORS.get(val.lower(), C["text"])
                else:
                    col = C["text"]
                ax.text(x + 0.02, y, val, color=col, fontsize=7.5,
                        fontfamily="monospace", va="center",
                        transform=ax.transAxes)

        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(f"Peak Table — all conditions · {len(rows)} peaks above +{self.thresh_db} dB threshold",
                     color=C["muted"], fontsize=8, pad=6)
        self.fig.canvas.draw_idle()

    # ── File dialogs ──────────────────────────────────────────────────────────

    def _load_condition(self, cond_name):
        """Open file dialog and load CSVs for a condition."""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        filepaths = filedialog.askopenfilenames(
            title=f"Load {cond_name} CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        root.destroy()
        if not filepaths:
            self._draw_status(f"No files selected for {cond_name}", C["muted"])
            return
        self._draw_status(f"Loading {len(filepaths)} file(s) for {cond_name}...", C["amber"])
        self.fig.canvas.draw_idle()

        def _load():
            n = self.store.load_files(list(filepaths), cond_name)
            self._draw_status(
                f"Loaded {n:,} points for {COND_LABELS.get(cond_name, cond_name)}", C["accent"])
            self.render()

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def _do_export_pdf(self):
        import tkinter as tk
        from tkinter import filedialog
        if not self.store.conditions:
            self._draw_status("No data to export", C["red"])
            return
        root = tk.Tk()
        root.withdraw()
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"rf_spectrum_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        root.destroy()
        if not path:
            return
        self._draw_status("Generating PDF...", C["amber"])
        self.fig.canvas.draw_idle()
        try:
            export_pdf(self.store, path, self.thresh_db)
            self._draw_status(f"PDF saved: {path}", C["accent"])
        except Exception as e:
            self._draw_status(f"PDF error: {e}", C["red"])

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_key(self, event):
        key = event.key
        if key == "l":
            self._load_condition("baseline")
        elif key == "i":
            self._load_condition("idle")
        elif key == "c":
            self._load_condition("active_call")
        elif key == "m":
            self._load_condition("active_music")
        elif key == "p":
            self._do_export_pdf()
        elif key == "x":
            self.store.conditions.clear()
            self.store.noise_floors.clear()
            self._draw_sidebar()
            self._draw_empty_chart()
            self._draw_status("All data cleared")
        elif key == "]":
            self.thresh_db = min(self.thresh_db + 1, 30)
            self._draw_status(f"Threshold: +{self.thresh_db} dB")
            self.render()
        elif key == "[":
            self.thresh_db = max(self.thresh_db - 1, 3)
            self._draw_status(f"Threshold: +{self.thresh_db} dB")
            self.render()
        elif key == "b":
            self.show_bands = not self.show_bands
            self.render()

    def _on_pick(self, event):
        if not hasattr(event, "artist"):
            return
        artist = event.artist
        if not hasattr(artist, "get_text"):
            return
        label = artist.get_text()

        # Tab clicks
        for cond_key in ["spectrum", "anomaly", "compare", "delta", "peaks"]:
            if cond_key.upper() in label:
                self.active_tab = cond_key
                self._draw_tab_bar()
                self.render()
                return

        # Action clicks
        action_map = {
            "Load baseline":     ("baseline",      self._load_condition),
            "Load idle":         ("idle",           self._load_condition),
            "Load active call":  ("active_call",    self._load_condition),
            "Load active music": ("active_music",   self._load_condition),
            "Export PDF report": (None,             lambda _: self._do_export_pdf()),
            "Clear all data":    (None,             lambda _: self._on_key(type("E", (), {"key":"x"})())),
        }
        for key, (cond, fn) in action_map.items():
            if key in label:
                fn(cond)
                return

        # Zoom preset clicks
        for preset_label, rng in ZOOM_PRESETS.items():
            if preset_label in label or preset_label.split()[0] in label:
                self.zoom = rng
                self._draw_status(f"Zoom: {preset_label}")
                self.render()
                return

    def _on_resize(self, event):
        self.fig.tight_layout(pad=0)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  RF Spectrum Analyzer — IoT Emissions Lab")
    print("=" * 60)
    print()
    print("  Keyboard shortcuts:")
    print("    L  —  Load baseline CSV files")
    print("    I  —  Load idle CSV files")
    print("    C  —  Load active call CSV files")
    print("    M  —  Load active music CSV files")
    print("    P  —  Export PDF report")
    print("    X  —  Clear all data")
    print("   [ ]  —  Decrease / increase anomaly threshold")
    print("    B  —  Toggle protocol band overlays")
    print()
    print("  Click sidebar labels to zoom or switch tabs.")
    print()

    app = SpectrumApp()


if __name__ == "__main__":
    main()