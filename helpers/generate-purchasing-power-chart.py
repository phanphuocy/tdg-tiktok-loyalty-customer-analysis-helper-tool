import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np

# ── 0. Load & prep ────────────────────────────────────────────────────────────
df = pd.read_csv("pivot_monthly_customers_acquisition.csv")

# Keep only months with both groups; exclude T9 & T10 (no return customers)
df = df[df["Order_Month"] >= "2025-11"].copy()

new = df[df["Acquisition_Type"] == "Newly Accquired"].set_index("Order_Month").sort_index()
ret = df[df["Acquisition_Type"] == "Return From Previous Month"].set_index("Order_Month").sort_index()

MONTHS = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
LABELS  = ["T11/25", "T12/25", "T1/26", "T2/26", "T3/26", "T4/26", "T5/26"]

new = new.loc[MONTHS]
ret = ret.loc[MONTHS]

# ── 1. Computed series ────────────────────────────────────────────────────────
# Panel A – Spending Efficiency (Spend% / Customer%)
eff_new = new["Pct_Total_Customer_Spending"] / new["Pct_Num_Of_Customers"]
eff_ret = ret["Pct_Total_Customer_Spending"] / ret["Pct_Num_Of_Customers"]

# Panel B – APV ratio and Frequency ratio (Return vs New)
apv_ratio  = ret["Average_Purchase_Value"].values / new["Average_Purchase_Value"].values
freq_ratio = ret["Buying_Frequency"].values / new["Buying_Frequency"].values

# Panel C – Sức mua = APV * Frequency  (unit: VNĐ)
suc_mua_new = new["Average_Purchase_Value"] * new["Buying_Frequency"]
suc_mua_ret = ret["Average_Purchase_Value"] * ret["Buying_Frequency"]

x = np.arange(len(MONTHS))
BAR_W = 0.35

# ── 2. Style constants ────────────────────────────────────────────────────────
C_NEW   = "#4285f4"   # blue  – khách mới
C_RET   = "#ea4335"   # red  – khách quay lại
C_APV   = "#2a78d6"   # blue  – APV ratio line
C_FREQ  = "#eda100"   # amber – Freq ratio line
C_REF   = "#e34948"   # red   – reference line (1x)
C_GRID  = "#e1e0d9"
C_TEXT  = "#2C2C2A"
C_MUTED = "#898781"
C_PHASE = "#f5f4f0"

FONT_TITLE = dict(fontsize=11, fontweight="500", color=C_TEXT)
FONT_LABEL = dict(fontsize=9,  color=C_MUTED)
FONT_TICK  = dict(fontsize=8.5, color=C_MUTED)
FONT_ANNOT = dict(fontsize=8,  color=C_TEXT)

def style_ax(ax):
    ax.set_facecolor("white")
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(C_GRID)
    ax.tick_params(colors=C_MUTED, length=3)
    ax.yaxis.grid(True, color=C_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS, **FONT_TICK)

def add_phase_bands(ax, ymin, ymax):
    """Subtle phase-shading + label on the x-axis band."""
    # P1: index 0-1, P2: 2-4, P3: 5-6
    for span, label, alpha in [
        ((-0.5, 1.5), "P1", 0.04),
        ((1.5,  4.5), "P2", 0.0),
        ((4.5,  6.5), "P3", 0.04),
    ]:
        ax.axvspan(span[0], span[1], ymin=0, ymax=1,
                   color="#2a78d6", alpha=alpha, zorder=0, linewidth=0)
        # phase text near top
        mid = (span[0] + span[1]) / 2
        ax.text(mid, ymax * 0.97, label,
                fontsize=8, color="#2a78d6", alpha=0.6,
                ha="center", va="top", fontstyle="italic")

# ── 3. Figure layout ─────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 13), facecolor="white")
fig.text(0.5, 0.985,
         "Phân tích sức mua theo nhóm khách — Mới vs. Quay lại",
         ha="center", va="top",
         fontsize=15, fontweight="500", color=C_TEXT)
fig.text(0.5, 0.965,
         "Nguồn: TikTok Shop pivot data  |  Đơn vị: VNĐ, lần, %",
         ha="center", va="top",
         fontsize=9, color=C_MUTED)

gs = fig.add_gridspec(3, 1, hspace=0.52, top=0.93, bottom=0.06,
                      left=0.07, right=0.97)

ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])
ax3 = fig.add_subplot(gs[2])

# ── Panel A: Spending Efficiency ─────────────────────────────────────────────
style_ax(ax1)
ax1.bar(x - BAR_W/2, eff_new.values, BAR_W, color=C_NEW,  label="Khách mới",       zorder=3, alpha=0.9)
ax1.bar(x + BAR_W/2, eff_ret.values, BAR_W, color=C_RET,  label="Khách quay lại",  zorder=3, alpha=0.9)
ax1.axhline(1.0, color=C_REF, linewidth=1.4, linestyle="--", zorder=4, label="Ngưỡng 1.0x")

ymax_a = 4.2
add_phase_bands(ax1, 0, ymax_a)
ax1.set_ylim(0, ymax_a)
ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1fx"))
ax1.set_title("① Hệ số nhân sức mua  (Spend% ÷ Customer%)", **FONT_TITLE, pad=8)
ax1.set_ylabel("Hệ số", **FONT_LABEL)

# value labels on bars
for i, (vn, vr) in enumerate(zip(eff_new.values, eff_ret.values)):
    ax1.text(i - BAR_W/2, vn + 0.06, f"{vn:.2f}x",
             ha="center", va="bottom", **FONT_ANNOT)
    ax1.text(i + BAR_W/2, vr + 0.06, f"{vr:.2f}x",
             ha="center", va="bottom", **FONT_ANNOT)

# annotation T11 outlier
ax1.annotate("T11: 6.1x gap\n(11 người → 49% doanh thu)",
             xy=(0 + BAR_W/2, eff_ret.values[0]),
             xytext=(1.3, 3.55),
             fontsize=7.5, color=C_RET,
             arrowprops=dict(arrowstyle="-|>", color=C_RET,
                             lw=0.9, connectionstyle="arc3,rad=-0.3"))

ax1.legend(loc="upper right", fontsize=8, framealpha=0,
           ncol=3, handlelength=1.4, labelcolor=C_TEXT)

# ── Panel B: APV vs Frequency ratio ──────────────────────────────────────────
style_ax(ax2)
ax2.plot(x, apv_ratio,  "o-", color=C_APV,  linewidth=2,  markersize=6,
         label="Tỷ lệ APV (Quay lại / Mới)", zorder=3)
ax2.plot(x, freq_ratio, "s--", color=C_FREQ, linewidth=2, markersize=6,
         label="Tỷ lệ Tần suất (Quay lại / Mới)", zorder=3)
ax2.axhline(1.0, color=C_REF, linewidth=1.2, linestyle=":", zorder=2, label="Bằng nhau (1.0x)")

ymax_b = 3.8
add_phase_bands(ax2, 0, ymax_b)
ax2.set_ylim(0.5, ymax_b)
ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1fx"))
ax2.set_title("② Đóng góp APV vs. Tần suất vào khoảng cách sức mua  (Quay lại ÷ Mới)", **FONT_TITLE, pad=8)
ax2.set_ylabel("Tỷ lệ (lần)", **FONT_LABEL)

# data labels
for i, (va, vf) in enumerate(zip(apv_ratio, freq_ratio)):
    offset_a = 0.13 if va > vf else -0.25
    offset_f = 0.13 if vf > va else -0.25
    ax2.text(i, va + offset_a, f"{va:.2f}x", ha="center", va="bottom",
             fontsize=7.5, color=C_APV)
    ax2.text(i, vf + offset_f, f"{vf:.2f}x", ha="center", va="bottom",
             fontsize=7.5, color=C_FREQ)

# shaded area between lines
ax2.fill_between(x, apv_ratio, freq_ratio,
                 where=(freq_ratio > apv_ratio),
                 alpha=0.08, color=C_FREQ,
                 label="Freq > APV (tần suất dominant)")
ax2.fill_between(x, apv_ratio, freq_ratio,
                 where=(apv_ratio >= freq_ratio),
                 alpha=0.08, color=C_APV,
                 label="APV > Freq (giá trị đơn hàng dominant)")

ax2.legend(loc="upper right", fontsize=7.8, framealpha=0,
           ncol=2, handlelength=1.4, labelcolor=C_TEXT)

# ── Panel C: Sức mua tuyệt đối (APV × Frequency) ─────────────────────────────
style_ax(ax3)
ax3.bar(x - BAR_W/2, suc_mua_new.values / 1000, BAR_W, color=C_NEW,
        label="Khách mới", zorder=3, alpha=0.9)
ax3.bar(x + BAR_W/2, suc_mua_ret.values / 1000, BAR_W, color=C_RET,
        label="Khách quay lại", zorder=3, alpha=0.9)

ymax_c = 550
add_phase_bands(ax3, 0, ymax_c)
ax3.set_ylim(0, ymax_c)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v)}K"))
ax3.set_title("③ Sức mua theo nhóm  (APV × Tần suất, đơn vị: nghìn VNĐ / khách)", **FONT_TITLE, pad=8)
ax3.set_ylabel("VNĐ / khách (K)", **FONT_LABEL)

# value labels + ratio annotation
for i, (vn, vr) in enumerate(zip(suc_mua_new.values, suc_mua_ret.values)):
    ax3.text(i - BAR_W/2, vn/1000 + 5, f"{vn/1000:.0f}K",
             ha="center", va="bottom", **FONT_ANNOT)
    ax3.text(i + BAR_W/2, vr/1000 + 5, f"{vr/1000:.0f}K",
             ha="center", va="bottom", **FONT_ANNOT)
    ratio = vr / vn
    ax3.text(i, max(vn, vr)/1000 + 28,
             f"×{ratio:.1f}",
             ha="center", va="bottom",
             fontsize=8, color="#533AB7", fontweight="500")

# legend for the ×ratio annotation
ratio_patch = mpatches.Patch(color="#533AB7", alpha=0.7,
                             label="×ratio = sức mua quay lại ÷ mới")
ax3.legend(handles=[
    mpatches.Patch(color=C_NEW, label="Khách mới"),
    mpatches.Patch(color=C_RET, label="Khách quay lại"),
    ratio_patch,
], loc="upper right", fontsize=8, framealpha=0,
   ncol=3, handlelength=1.4, labelcolor=C_TEXT)

# ── 4. Shared x-axis footer note ─────────────────────────────────────────────
fig.text(0.07, 0.015,
         "Ghi chú: T10/2025 loại khỏi biểu đồ (chỉ có nhóm mới, không có nhóm quay lại để so sánh). "
         "Vùng xanh nhạt = P1/P3; nền trắng = P2.",
         fontsize=7.5, color=C_MUTED, va="bottom")

# ── 5. Save ──────────────────────────────────────────────────────────────────
out = "charts/spending_power_analysis.png"
plt.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved → {out}")