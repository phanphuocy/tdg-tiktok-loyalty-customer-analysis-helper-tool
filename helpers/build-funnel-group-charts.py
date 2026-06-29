#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_funnel_charts.py
=========================
Sinh bộ biểu đồ phân tích Funnel Group cho thuyết trình.

NGUỒN DỮ LIỆU : SQLite "data.db", gồm 2 bảng
    - switch_total_funnel_group     (tổng hợp toàn dải, khách Regular/Loyal)
    - switch_monthly_funnel_group   (số khách loyal acquire theo từng tháng)

QUY ƯỚC MÀU :
    Kinka (cà phê / trà)        -> VÀNG
    Revy  (chăm sóc gia đình)   -> XANH DƯƠNG
    SiMee (chăm sóc cá nhân)    -> ĐỎ
    Sắc nhạt = "Only with ..."  | Sắc đậm = "Start with ..."
    Nhóm đa ngành = màu pha của các ngành thành phần.

FONT : Open Sans (tự dò trong máy -> tự tải bản instance tĩnh -> fallback DejaVu).

CÁCH DÙNG :
    python generate_funnel_charts.py            # đọc ./data.db, xuất ./charts/
    python generate_funnel_charts.py my.db out  # tuỳ chỉnh db & thư mục xuất
"""

import os
import sys
import sqlite3
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# ----------------------------------------------------------------------------- #
# 0. THAM SỐ                                                                     #
# ----------------------------------------------------------------------------- #
DB_PATH  = sys.argv[1] if len(sys.argv) > 1 else "data.db"
OUT_DIR  = sys.argv[2] if len(sys.argv) > 2 else "charts/funnel-group"
DPI      = 300
os.makedirs(OUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------------- #
# 1. FONT OPEN SANS                                                              #
# ----------------------------------------------------------------------------- #
def setup_open_sans():
    """Đăng ký Open Sans cho matplotlib, có nhiều lớp dự phòng."""
    # 1.1 thử tìm Open Sans đã cài sẵn
    for f in fm.fontManager.ttflist:
        if "open sans" in f.name.lower():
            return "Open Sans"

    # 1.2 thử các file .ttf cạnh script (nếu đã tải sẵn)
    here = os.path.dirname(os.path.abspath(__file__))
    local_candidates = []
    for d in (here, os.path.join(here, "fonts")):
        if os.path.isdir(d):
            local_candidates += [os.path.join(d, x) for x in os.listdir(d)
                                 if x.lower().startswith("opensans") and x.lower().endswith(".ttf")]
    # 1.3 nếu chưa có thì tải bản variable từ kho google/fonts trên GitHub
    if not local_candidates:
        try:
            fdir = os.path.join(here, "fonts")
            os.makedirs(fdir, exist_ok=True)
            url = ("https://raw.githubusercontent.com/google/fonts/main/"
                   "ofl/opensans/OpenSans%5Bwdth,wght%5D.ttf")
            dst = os.path.join(fdir, "OpenSans-VF.ttf")
            urllib.request.urlretrieve(url, dst)
            local_candidates = [dst]
        except Exception as e:
            print("  [font] Không tải được Open Sans:", e)

    registered = False
    for path in local_candidates:
        try:
            fm.fontManager.addfont(path)
            registered = True
        except Exception:
            pass

    if registered:
        for f in fm.fontManager.ttflist:
            if "open sans" in f.name.lower():
                return "Open Sans"

    print("  [font] Dùng tạm DejaVu Sans (không tìm thấy Open Sans).")
    return "DejaVu Sans"


FONT = setup_open_sans()
plt.rcParams.update({
    "font.family": FONT,
    "axes.titleweight": "bold",
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.grid": True,
    "grid.color": "#E6E6E6",
    "grid.linewidth": 0.8,
    "font.size": 12,
})

# ----------------------------------------------------------------------------- #
# 2. BẢNG MÀU & NHÃN                                                             #
# ----------------------------------------------------------------------------- #
# màu chủ đạo từng ngành
KINKA = "#E5A50A"   # vàng / amber
REVY  = "#1F6FB2"   # xanh dương
SIMEE = "#C0392B"   # đỏ
INK   = "#2B2B2B"   # màu chữ tiêu đề

# sắc nhạt (Only) / đậm (Start) + nhóm pha
COLORS = {
    "Only with Kinka":            "#F4CE5E",   # vàng nhạt
    "Start with Kinka":           "#E5A50A",   # vàng đậm
    "Only with Revy":             "#9DC3E6",   # xanh nhạt
    "Start with Revy":            "#1F6FB2",   # xanh đậm
    "Only with SiMee":            "#E8A6A0",   # đỏ nhạt
    "Start with SiMee":           "#C0392B",   # đỏ đậm
    "Start with Revy and SiMee":  "#7D3C98",   # tím = xanh + đỏ
    "Start with Kinka and Revy":  "#6FA84B",   # xanh lá = vàng + xanh
    "Start with Kinka and SiMee": "#D9772B",   # cam = vàng + đỏ
    "Start with all 3 brands":    "#5D5D5D",   # xám đậm
    "Not buy any of 3 brands":    "#BDBDBD",
    "Unsorted":                   "#D9D9D9",
}
DEFAULT_COLOR = "#9E9E9E"

VN_LABEL = {
    "Only with Kinka":            "Chỉ Kinka",
    "Start with Kinka":           "Khởi đầu Kinka",
    "Only with Revy":             "Chỉ Revy",
    "Start with Revy":            "Khởi đầu Revy",
    "Only with SiMee":            "Chỉ SiMee",
    "Start with SiMee":           "Khởi đầu SiMee",
    "Start with Revy and SiMee":  "Khởi đầu Revy + SiMee",
    "Start with Kinka and Revy":  "Khởi đầu Kinka + Revy",
    "Start with Kinka and SiMee": "Khởi đầu Kinka + SiMee",
    "Start with all 3 brands":    "Khởi đầu cả 3 ngành",
}

# thứ tự xếp chồng (Kinka -> Revy -> SiMee -> đa ngành)
STACK_ORDER = [
    "Only with Kinka", "Start with Kinka", "Start with Kinka and Revy",
    "Start with Kinka and SiMee",
    "Only with Revy", "Start with Revy", "Start with Revy and SiMee",
    "Only with SiMee", "Start with SiMee", "Start with all 3 brands",
]

def color_of(g):   return COLORS.get(g, DEFAULT_COLOR)
def label_of(g):   return VN_LABEL.get(g, g)

# ----------------------------------------------------------------------------- #
# 3. ĐỊNH DẠNG SỐ KIỂU VIỆT NAM                                                  #
# ----------------------------------------------------------------------------- #
def vnd(x):
    return f"{x:,.0f}".replace(",", ".") + "đ"

def trieu(x, _=None):           # cho trục: 1.097.019 -> "1,1 tr"
    return f"{x/1e6:.1f}".replace(".", ",") + " tr"

def pct(x, _=None):
    return f"{x:.0f}%"

# ----------------------------------------------------------------------------- #
# 4. NẠP DỮ LIỆU TỪ data.db                                                      #
# ----------------------------------------------------------------------------- #
con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row

total_rows = [dict(r) for r in con.execute(
    "SELECT * FROM switch_total_funnel_group").fetchall()]
monthly_rows = [dict(r) for r in con.execute(
    "SELECT * FROM switch_monthly_funnel_group").fetchall()]
con.close()

# --- chuẩn hoá bảng tổng ---
for r in total_rows:
    r["n"]   = int(r["Num_Of_Customers"] or 0)
    r["ltv"] = float(r["Avg_Customer_Value"] or 0)
    r["aov"] = float(r["Avg_Purchase_Value"] or 0)
    r["orders"]   = float(r["Avg_Num_Of_Orders"] or 0)
    r["cancel"]   = float(r["Avg_Num_of_Canceled_Orders"] or 0)
    r["d2switch"] = r["Avg_Days_To_Switch"]
    r["retention"] = float(r["Avg_Retention_Time_Period"] or 0)
    r["total_value"] = r["n"] * r["ltv"]
    r["cancel_rate"] = (r["cancel"] / r["orders"] * 100) if r["orders"] else 0
TOTAL = {r["Funnel_Group"]: r for r in total_rows}

# --- pivot bảng tháng ---
months = sorted({r["Month"] for r in monthly_rows})
groups_seen = [g for g in STACK_ORDER
               if any(r["Funnel_Group"] == g for r in monthly_rows)]
PIV = {m: {g: 0 for g in groups_seen} for m in months}
for r in monthly_rows:
    PIV[r["Month"]][r["Funnel_Group"]] += int(r["Num_of_Customers"] or 0)

# 3 giai đoạn marketing
PHASES = [("GĐ1: Set-up & livestream\n(09–12/2025)", ["2025-09","2025-10","2025-11","2025-12"]),
          ("GĐ2: Tết + viral salted coffee\n(01–03/2026)", ["2026-01","2026-02","2026-03"]),
          ("GĐ3: Nâng cấp video + affiliate\n(04–05/2026)", ["2026-04","2026-05"])]
CENSORED = {"2026-04", "2026-05"}   # cohort còn quá trẻ -> switching bị kiểm duyệt phải


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("  ✓", path)


def credit(ax, text="Nguồn: data.db · Khách Regular/Loyal"):
    ax.annotate(text, xy=(1, -0.16), xycoords="axes fraction",
                ha="right", va="top", fontsize=9, color="#9A9A9A")

# =========================================================================== #
# CHART 1 — Thẻ điểm giá trị: LTV theo funnel group                            #
# =========================================================================== #
def chart1_ltv():
    data = sorted(total_rows, key=lambda r: r["ltv"])
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ypos = range(len(data))
    bars = ax.barh(list(ypos), [r["ltv"] for r in data],
                   color=[color_of(r["Funnel_Group"]) for r in data],
                   edgecolor="white", height=0.72)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels([f"{label_of(r['Funnel_Group'])}  (n={r['n']})" for r in data])
    ax.xaxis.set_major_formatter(plt.FuncFormatter(trieu))
    ax.set_xlabel("Giá trị vòng đời trung bình (LTV)")
    ax.grid(axis="y", visible=False)
    for r, b in zip(data, bars):
        ax.text(b.get_width() + max(r["ltv"] for r in data)*0.01,
                b.get_y() + b.get_height()/2,
                f"{vnd(r['ltv'])} · {r['orders']:.1f} đơn",
                va="center", fontsize=10.5, color=INK)
    ax.set_xlim(0, max(r["ltv"] for r in data) * 1.28)
    ax.set_title("CHẤT LƯỢNG TỪNG FUNNEL GROUP — LTV trung bình mỗi khách loyal",
                 fontsize=15, color=INK, pad=34, loc="left")
    ax.text(0, 1.05, "Switcher (sắc đậm/đa ngành) tạo giá trị vượt trội so với khách 'Only'",
            transform=ax.transAxes, fontsize=11, color="#666")
    credit(ax)
    save(fig, "01_ltv_theo_funnel_group.png")

# =========================================================================== #
# CHART 2 — Switcher "gánh team": tỷ trọng số lượng vs giá trị                  #
# =========================================================================== #
def chart2_switcher_weight():
    sw = [r for r in total_rows if (r["Switching_Status"] or "").lower() == "switcher"]
    non = [r for r in total_rows if (r["Switching_Status"] or "").lower() != "switcher"]
    n_sw, n_non = sum(r["n"] for r in sw), sum(r["n"] for r in non)
    v_sw, v_non = sum(r["total_value"] for r in sw), sum(r["total_value"] for r in non)
    n_tot, v_tot = n_sw + n_non, v_sw + v_non

    cats = ["Số lượng khách", "Giá trị (LTV × SL)"]
    sw_pct  = [n_sw / n_tot * 100, v_sw / v_tot * 100]
    non_pct = [n_non / n_tot * 100, v_non / v_tot * 100]

    fig, ax = plt.subplots(figsize=(9, 6.2))
    C_SW, C_NON = "#E5A50A", "#C9C9C9"
    b1 = ax.bar(cats, sw_pct,  color=C_SW,  edgecolor="white", width=0.55, label="Switcher")
    b2 = ax.bar(cats, non_pct, bottom=sw_pct, color=C_NON, edgecolor="white",
                width=0.55, label="Non-switcher")
    for i in range(2):
        ax.text(i, sw_pct[i]/2, f"Switcher\n{sw_pct[i]:.1f}%",
                ha="center", va="center", color="white", fontweight="bold", fontsize=12.5)
        ax.text(i, sw_pct[i] + non_pct[i]/2, f"Non-switcher\n{non_pct[i]:.1f}%",
                ha="center", va="center", color="#555", fontsize=11.5)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(pct))
    ax.set_ylabel("Tỷ trọng")
    ax.grid(axis="x", visible=False)
    ax.set_title("SWITCHER 'GÁNH TEAM'", fontsize=16, color=INK, pad=26, loc="left")
    ratio = (v_sw/n_sw) / (v_non/n_non)
    ax.text(0, 1.04,
            f"Chỉ {sw_pct[0]:.0f}% đầu người nhưng tạo {sw_pct[1]:.0f}% giá trị  ·  "
            f"1 switcher ≈ {ratio:.1f}× một non-switcher",
            transform=ax.transAxes, fontsize=11.5, color="#666")
    credit(ax)
    save(fig, "02_switcher_ganh_team.png")

# =========================================================================== #
# CHART 3 — Tỷ lệ mua chéo theo CỬA VÀO (single-brand entry)                    #
# =========================================================================== #
def chart3_switch_rate():
    brands = [("Kinka", KINKA, "Only with Kinka", "Start with Kinka"),
              ("Revy",  REVY,  "Only with Revy",  "Start with Revy"),
              ("SiMee", SIMEE, "Only with SiMee", "Start with SiMee")]
    rows = []
    for name, col, only_g, start_g in brands:
        n_only  = TOTAL.get(only_g,  {}).get("n", 0)
        n_start = TOTAL.get(start_g, {}).get("n", 0)
        tot = n_only + n_start
        rate = (n_start / tot * 100) if tot else 0
        rows.append((name, col, rate, n_start, tot))

    fig, ax = plt.subplots(figsize=(9, 6))
    xs = range(len(rows))
    bars = ax.bar(list(xs), [r[2] for r in rows],
                  color=[r[1] for r in rows], edgecolor="white", width=0.6)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{r[0]}\n(cửa vào {r[4]} khách)" for r in rows], fontsize=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(pct))
    ax.set_ylabel("Tỷ lệ khách mua chéo sang ngành khác")
    ax.set_ylim(0, 112)
    ax.grid(axis="x", visible=False)
    for r, b in zip(rows, bars):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+2,
                f"{r[2]:.0f}%\n({r[3]}/{r[4]})", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=INK)
    ax.set_title("NGHỊCH LÝ SẢN PHẨM MỒI — Tỷ lệ mua chéo theo cửa vào",
                 fontsize=15, color=INK, pad=26, loc="left")
    ax.text(0, 1.04,
            "Kinka (cà phê) kéo traffic giỏi nhất nhưng mua chéo kém nhất — "
            "mục tiêu 'mồi sang Revy/SiMee' mới đạt rất thấp",
            transform=ax.transAxes, fontsize=11, color="#666")
    credit(ax)
    save(fig, "03_ty_le_mua_cheo_theo_cua_vao.png")

# =========================================================================== #
# CHART 4 — Cửa sổ vàng: số ngày đến khi switch                                 #
# =========================================================================== #
def chart4_golden_window():
    data = [r for r in total_rows if r["d2switch"] is not None]
    data.sort(key=lambda r: r["d2switch"])
    fig, ax = plt.subplots(figsize=(10, 5.6))
    xs = range(len(data))
    bars = ax.bar(list(xs), [r["d2switch"] for r in data],
                  color=[color_of(r["Funnel_Group"]) for r in data],
                  edgecolor="white", width=0.6)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{label_of(r['Funnel_Group'])}\n(n={r['n']})" for r in data],
                       fontsize=11)
    ax.set_ylabel("Số ngày trung bình đến khi mua chéo")
    ax.grid(axis="x", visible=False)
    for r, b in zip(data, bars):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+1.2,
                f"{r['d2switch']:.0f} ngày", ha="center", va="bottom",
                fontsize=11.5, fontweight="bold", color=INK)
    ax.set_ylim(0, max(r["d2switch"] for r in data)*1.18)
    ax.set_title("CỬA SỔ VÀNG — Mất bao lâu để khách mua chéo?",
                 fontsize=15, color=INK, pad=26, loc="left")
    ax.text(0, 1.04,
            "Khách khởi đầu Kinka switch NHANH nhất (~3 tuần) — thời điểm vàng để chào Revy/SiMee",
            transform=ax.transAxes, fontsize=11, color="#666")
    credit(ax)
    save(fig, "04_cua_so_vang_days_to_switch.png")

# =========================================================================== #
# CHART 5 — Tỷ lệ hủy đơn theo funnel group                                     #
# =========================================================================== #
def chart5_cancel():
    data = sorted(total_rows, key=lambda r: r["cancel_rate"])
    fig, ax = plt.subplots(figsize=(10.5, 6))
    xs = range(len(data))
    bars = ax.bar(list(xs), [r["cancel_rate"] for r in data],
                  color=[color_of(r["Funnel_Group"]) for r in data],
                  edgecolor="white", width=0.66)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{label_of(r['Funnel_Group'])}\n(n={r['n']})" for r in data],
                       fontsize=10, rotation=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(pct))
    ax.set_ylabel("Tỷ lệ hủy (đơn hủy / tổng đơn)")
    ax.grid(axis="x", visible=False)
    for r, b in zip(data, bars):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.4,
                f"{r['cancel_rate']:.1f}%", ha="center", va="bottom",
                fontsize=10.5, fontweight="bold", color=INK)
    ax.set_ylim(0, max(r["cancel_rate"] for r in data)*1.2)
    ax.set_title("THÓI QUEN HỦY ĐƠN theo funnel group",
                 fontsize=15, color=INK, pad=26, loc="left")
    ax.text(0, 1.04,
            "Khởi đầu Kinka hủy thấp nhất (sạch) — Khởi đầu Revy hủy cao, rào cản cần xử lý",
            transform=ax.transAxes, fontsize=11, color="#666")
    credit(ax)
    save(fig, "05_ty_le_huy_don.png")

# =========================================================================== #
# CHART 6 — Bản đồ giá trị: LTV vs số đơn (bubble = quy mô)                      #
# =========================================================================== #
def chart6_value_map():
    # offset nhãn riêng cho từng nhóm để tránh đè nhau: (dx, dy, ha, va) theo points
    LABEL_OFF = {
        "Only with Kinka":           (62, -22, "left",   "center"),
        "Start with Kinka":          (22, -2,  "left",   "center"),
        "Only with Revy":            (0, 20,   "center", "bottom"),
        "Start with Revy":           (0, 18,   "center", "bottom"),
        "Start with SiMee":          (0, 18,   "center", "bottom"),
        "Start with Revy and SiMee": (-12, -22,"center", "top"),
        "Start with Kinka and Revy": (-52, 0,  "right",  "center"),
    }
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    for r in total_rows:
        size = 120 + r["n"] * 14
        ax.scatter(r["orders"], r["ltv"], s=size, color=color_of(r["Funnel_Group"]),
                   edgecolor="white", linewidth=1.4, alpha=0.92, zorder=3)
        dx, dy, ha, va = LABEL_OFF.get(r["Funnel_Group"], (0, 14, "center", "bottom"))
        ax.annotate(label_of(r["Funnel_Group"]), (r["orders"], r["ltv"]),
                    textcoords="offset points", xytext=(dx, dy),
                    ha=ha, va=va, fontsize=9.5, color=INK, zorder=5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(trieu))
    ax.set_xlabel("Số đơn trung bình / khách")
    ax.set_ylabel("LTV trung bình / khách")
    # đường trung bình tham chiếu
    avg_ltv = sum(r["total_value"] for r in total_rows) / sum(r["n"] for r in total_rows)
    ax.axhline(avg_ltv, color="#BBBBBB", ls="--", lw=1)
    ax.text(ax.get_xlim()[1], avg_ltv, f" LTV bình quân {vnd(avg_ltv)}",
            va="bottom", ha="right", fontsize=9, color="#888")
    ax.set_title("BẢN ĐỒ GIÁ TRỊ — Số đơn × LTV (kích thước bong bóng = quy mô khách)",
                 fontsize=14.5, color=INK, pad=24, loc="left")
    ax.text(0, 1.03,
            "Càng mua chéo nhiều ngành, khách càng mua nhiều đơn và giá trị càng cao",
            transform=ax.transAxes, fontsize=11, color="#666")
    ax.margins(0.18)
    credit(ax)
    save(fig, "06_ban_do_gia_tri_ltv_vs_don.png")

# =========================================================================== #
# CHART 7 — Cấu trúc acquire khách loyal theo tháng (stacked)                   #
# =========================================================================== #
def chart7_monthly_stack():
    fig, ax = plt.subplots(figsize=(12.5, 6.8))
    x = range(len(months))
    bottoms = [0]*len(months)
    for g in groups_seen:
        vals = [PIV[m][g] for m in months]
        ax.bar(list(x), vals, bottom=bottoms, color=color_of(g),
               edgecolor="white", width=0.78, label=label_of(g))
        bottoms = [b+v for b, v in zip(bottoms, vals)]
    # tổng mỗi tháng
    for i, m in enumerate(months):
        tot = sum(PIV[m].values())
        ax.text(i, tot+1.5, str(tot), ha="center", va="bottom",
                fontsize=10.5, fontweight="bold", color=INK)
    ax.set_xticks(list(x))
    ax.set_xticklabels(months, fontsize=10.5)
    ax.set_ylabel("Số khách loyal acquire")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, max(sum(PIV[m].values()) for m in months)*1.16)

    # dải giai đoạn
    ymax = ax.get_ylim()[1]
    band_colors = ["#FBF3DD", "#F6E2DE", "#DEE9F4"]
    for (label, mlist), bc in zip(PHASES, band_colors):
        idx = [i for i, m in enumerate(months) if m in mlist]
        if not idx:
            continue
        ax.axvspan(min(idx)-0.45, max(idx)+0.45, color=bc, alpha=0.55, zorder=0)
        ax.text((min(idx)+max(idx))/2, ymax*0.985, label, ha="center", va="top",
                fontsize=9.5, color="#555", style="italic")
    ax.legend(ncol=4, fontsize=9.5, loc="upper left",
              bbox_to_anchor=(0, -0.08), frameon=False)
    ax.set_title("CẤU TRÚC ACQUIRE KHÁCH LOYAL THEO THÁNG",
                 fontsize=15, color=INK, pad=32, loc="left")
    ax.text(0, 1.045,
            "Mồi cà phê đẩy quy mô (T1/2026) nhưng làm tệp 'cà phê hoá' — phễu nông dần",
            transform=ax.transAxes, fontsize=11, color="#666")
    save(fig, "07_cau_truc_acquire_theo_thang.png")

# =========================================================================== #
# CHART 8 — Tỷ trọng switcher theo tháng + 3 giai đoạn                          #
# =========================================================================== #
def chart8_switcher_trend():
    sw_share, totals = [], []
    for m in months:
        tot = sum(PIV[m].values())
        sw  = sum(v for g, v in PIV[m].items() if g.startswith("Start"))
        sw_share.append(sw/tot*100 if tot else 0)
        totals.append(tot)

    fig, ax = plt.subplots(figsize=(12, 6.2))
    x = list(range(len(months)))
    # nền 3 giai đoạn
    band_colors = ["#FBF3DD", "#F6E2DE", "#DEE9F4"]
    for (label, mlist), bc in zip(PHASES, band_colors):
        idx = [i for i, m in enumerate(months) if m in mlist]
        if idx:
            ax.axvspan(min(idx)-0.5, max(idx)+0.5, color=bc, alpha=0.6, zorder=0)

    ax.plot(x, sw_share, color="#7D3C98", lw=2.6, marker="o", ms=8,
            zorder=3, label="% switcher trong cohort")
    for xi, (m, s) in enumerate(zip(months, sw_share)):
        cens = m in CENSORED
        ax.annotate(f"{s:.0f}%", (xi, s), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=10.5,
                    fontweight="bold", color="#7D3C98")
        if cens:   # đánh dấu cohort bị kiểm duyệt phải
            ax.scatter([xi], [s], s=240, facecolor="none",
                       edgecolor="#C0392B", lw=2, zorder=4)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(n={t})" for m, t in zip(months, totals)], fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(pct))
    ax.set_ylabel("% khách acquire là switcher")
    ax.set_ylim(0, max(sw_share)*1.25)
    ax.grid(axis="x", visible=False)

    # chú thích kiểm duyệt phải
    ax.annotate("Vòng tròn đỏ = cohort còn quá trẻ\n(switching chưa kịp bộc lộ — đừng vội kết luận)",
                xy=(len(months)-1, sw_share[-1]), xytext=(len(months)-3.2, max(sw_share)*1.05),
                fontsize=9.5, color="#C0392B",
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.2))
    ax.set_title("PHỄU NÔNG DẦN — Tỷ trọng switcher giảm khi scale bằng mồi cà phê",
                 fontsize=14.5, color=INK, pad=26, loc="left")
    ax.text(0, 1.04,
            "Cross-sell engine không scale theo traffic engine: % switcher rơi mạnh từ GĐ1 sang GĐ2",
            transform=ax.transAxes, fontsize=11, color="#666")
    credit(ax)
    save(fig, "08_xu_huong_switcher_theo_thang.png")


# ----------------------------------------------------------------------------- #
# RUN ALL                                                                       #
# ----------------------------------------------------------------------------- #
if __name__ == "__main__":
    print(f"Font dùng: {FONT}")
    print(f"Đọc: {DB_PATH}  |  Xuất: {OUT_DIR}/")
    chart1_ltv()
    chart2_switcher_weight()
    chart3_switch_rate()
    chart4_golden_window()
    chart5_cancel()
    chart6_value_map()
    chart7_monthly_stack()
    chart8_switcher_trend()
    print("Hoàn tất — 8 biểu đồ đã được tạo.")