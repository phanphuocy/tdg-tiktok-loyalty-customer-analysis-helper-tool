#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dựng các biểu đồ CHỦ ĐẠO cho phần B — Phân tích khách hàng mới / quay lại
Kênh TikTok Shop Trường Dương Store.

Nguồn dữ liệu : SQLite  ->  file 'data.db', table 'monthly_customers_acquisition'
Đầu ra        : mỗi biểu đồ là 1 file .png RIÊNG (không gộp chung) trong thư mục ./charts

Quy ước màu (theo yêu cầu):
    - Khách MỚI      : xanh  #4285f4
    - Khách QUAY LẠI : đỏ    #ea4335
"""

import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # render ra file, không cần màn hình
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

# ----------------------------------------------------------------------------
# 0. CẤU HÌNH
# ----------------------------------------------------------------------------
DB_PATH   = "data.db"                          # <-- file SQLite của bạn
TABLE     = "pivot_monthly_customers_acquisition"
OUT_DIR   = "charts/new-returning/"                           # thư mục lưu các .png
DPI       = 300

NEW   = "#4285f4"   # khách mới  (xanh)
RET   = "#ea4335"   # khách quay lại (đỏ)
INK   = "#202124"   # màu chữ chính
MUTE  = "#5f6368"   # màu chữ phụ
GRID  = "#e8eaed"   # màu lưới
PANEL = "#f1f3f4"   # nền nhạt cho vùng giai đoạn

# Bảng màu thương hiệu (cho biểu đồ cơ cấu giỏ hàng)
BRAND = {
    "Kinka":  "#fbbc04",   # vàng/amber (cà phê)
    "Revy":   "#4285f4",   # xanh
    "SiMee":  "#ea4335",   # đỏ
}

# Nhãn hiển thị cho hai loại khách
LABEL_NEW = "Khách mới"
LABEL_RET = "Khách quay lại"

# Style chung
plt.rcParams.update({
    # "font.family":      "DejaVu Sans",  # hỗ trợ dấu tiếng Việt
    "font.family":      "Open Sans",  # hỗ trợ dấu tiếng Việt
    "font.size":        9,
    "axes.edgecolor":   MUTE,
    "axes.labelcolor":  INK,
    "text.color":       INK,
    "xtick.color":      MUTE,
    "ytick.color":      MUTE,
    "axes.grid":        True,
    "grid.color":       GRID,
    "grid.linewidth":   0.8,
    "figure.dpi":       DPI,
    "savefig.dpi":      DPI,
    "savefig.bbox":     "tight",
})


# ----------------------------------------------------------------------------
# 1. NẠP & CHUẨN BỊ DỮ LIỆU
# ----------------------------------------------------------------------------
def load_data(db_path=DB_PATH, table=TABLE):
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table}", con)
    con.close()

    # chuẩn hoá tên loại khách -> 'new' / 'ret'
    def kind(x):
        x = str(x).lower()
        if "return" in x:
            return "ret"
        return "new"
    df["kind"] = df["Acquisition_Type"].map(kind)

    # sắp xếp theo tháng (chuỗi 'YYYY-MM' sắp xếp đúng theo thứ tự thời gian)
    df = df.sort_values("Order_Month").reset_index(drop=True)

    # gắn giai đoạn P1/P2/P3
    def phase(m):
        if m <= "2025-12":
            return "P1"
        if m <= "2026-03":
            return "P2"
        return "P3"
    df["phase"] = df["Order_Month"].map(phase)

    # chi tiêu trên đầu người
    df["spend_per_head"] = df["Total_Customer_Spending"] / df["Num_Of_Customers"]
    return df


def pivot_kind(df, value):
    """Trả về bảng index=tháng, cột = ['new','ret'] cho 1 chỉ số."""
    p = df.pivot_table(index="Order_Month", columns="kind",
                       values=value, aggfunc="first")
    return p.sort_index()


def short_month(m):
    """ '2026-01' -> 'T1/26' """
    y, mo = m.split("-")
    return f"T{int(mo)}/{y[2:]}"


# ----------------------------------------------------------------------------
# Tiện ích style trục
# ----------------------------------------------------------------------------
def clean_axes(ax, hide_y=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUTE)
    ax.spines["bottom"].set_color(MUTE)
    ax.set_axisbelow(True)
    if hide_y:
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)


def vnd(x):
    return f"{x:,.0f}".replace(",", ".")


def save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"  ✔ {path}")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 1 — Quy mô khách mới theo tháng (Slide 5)
# ----------------------------------------------------------------------------
def chart_acquisition(df):
    new = pivot_kind(df, "Num_Of_Customers")["new"]
    months = list(new.index)
    x = np.arange(len(months))
    vals = new.values

    fig, ax = plt.subplots(figsize=(10, 5.2))

    # nền giai đoạn
    phase_of = df.drop_duplicates("Order_Month").set_index("Order_Month")["phase"]
    bounds = {"P1": [], "P2": [], "P3": []}
    for i, m in enumerate(months):
        bounds[phase_of[m]].append(i)
    for ph, idxs in bounds.items():
        if idxs:
            ax.axvspan(min(idxs) - 0.5, max(idxs) + 0.5,
                       color=PANEL, alpha=0.6, zorder=0)
            ax.text((min(idxs) + max(idxs)) / 2, max(vals) * 1.06, ph,
                    ha="center", va="bottom", color=MUTE, fontsize=11, fontweight="bold")

    bars = ax.bar(x, vals, color=NEW, width=0.62, zorder=3)

    # nhãn giá trị
    for xi, v in zip(x, vals):
        ax.text(xi, v + max(vals) * 0.015, f"{v:,.0f}".replace(",", "."),
                ha="center", va="bottom", fontsize=9, color=INK)

    # callout tháng 1/2026
    if "2026-01" in months:
        j = months.index("2026-01")
        ax.annotate("625 khách — ~26% toàn base\nchỉ trong 30 ngày",
                    xy=(j, vals[j]), xytext=(j - 2.3, max(vals) * 0.82),
                    fontsize=10, color=RET, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=RET, lw=1.6))

    ax.set_xticks(x)
    ax.set_xticklabels([short_month(m) for m in months])
    ax.set_ylabel("Số khách hàng mới")
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_title("Quy mô khách hàng mới theo tháng",
                 fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax.text(0, 1.02, "Lực kéo khách mới tăng vọt ~9 lần ở P2 nhờ Cà phê Muối viral + Tết",
            transform=ax.transAxes, fontsize=10.5, color=MUTE)
    clean_axes(ax)
    save(fig, "01_quy_mo_khach_moi.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 2 — Khách mới vs Khách quay lại (Slide 6)
# ----------------------------------------------------------------------------
def chart_new_vs_returning(df):
    new = pivot_kind(df, "Num_Of_Customers")["new"]
    ret = pivot_kind(df, "Num_Of_Customers")["ret"]
    months = list(new.index)
    x = np.arange(len(months))

    fig, ax1 = plt.subplots(figsize=(10, 5.2))
    ax2 = ax1.twinx()  # trục phụ cho khách quay lại (độ lớn nhỏ hơn nhiều)

    l1, = ax1.plot(x, new.values, color=NEW, lw=2.6, marker="o",
                   markersize=6, label=LABEL_NEW, zorder=3)
    l2, = ax2.plot(x, ret.reindex(months).values, color=RET, lw=2.6, marker="s",
                   markersize=6, label=LABEL_RET, zorder=3)

    ax1.set_ylabel(f"{LABEL_NEW} (trục trái)", color=NEW)
    ax2.set_ylabel(f"{LABEL_RET} (trục phải)", color=RET)
    ax1.tick_params(axis="y", colors=NEW)
    ax2.tick_params(axis="y", colors=RET)

    ax1.set_xticks(x)
    ax1.set_xticklabels([short_month(m) for m in months])
    ax1.set_ylim(0, np.nanmax(new.values) * 1.15)
    ax2.set_ylim(0, np.nanmax(ret.values) * 1.35)

    ax1.set_title("Hai dòng chảy, hai hình dạng khác nhau",
                  fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax1.text(0, 1.02,
             "Khách mới gấp khúc theo mùa vụ · Khách quay lại tăng đều, gần như tuyến tính",
             transform=ax1.transAxes, fontsize=10.5, color=MUTE)

    clean_axes(ax1)
    ax2.spines["top"].set_visible(False)
    ax1.legend(handles=[l1, l2], loc="upper left", frameon=False, fontsize=10.5)
    save(fig, "02_khach_moi_vs_quay_lai.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 3 — Tỷ trọng mới/quay lại theo giai đoạn (Slide 8)
# ----------------------------------------------------------------------------
def chart_share_by_phase(df):
    g = (df.groupby(["phase", "kind"])["Num_Of_Customers"]
           .sum().unstack("kind").fillna(0))
    # thêm dòng toàn kỳ
    total = df.groupby("kind")["Num_Of_Customers"].sum()
    g.loc["Toàn kỳ"] = total
    order = ["P1", "P2", "P3", "Toàn kỳ"]
    g = g.reindex(order)

    pct_new = g["new"] / (g["new"] + g["ret"]) * 100
    pct_ret = g["ret"] / (g["new"] + g["ret"]) * 100

    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(9, 5.4))

    ax.bar(x, pct_new, color=NEW, width=0.6, label=LABEL_NEW)
    ax.bar(x, pct_ret, bottom=pct_new, color=RET, width=0.6, label=LABEL_RET)

    for xi, pn, pr, nret in zip(x, pct_new, pct_ret, g["ret"]):
        ax.text(xi, pn / 2, f"{pn:.1f}%", ha="center", va="center",
                color="white", fontsize=11, fontweight="bold")
        # nhãn % + số tuyệt đối khách quay lại
        ax.text(xi, pn + pr / 2, f"{pr:.1f}%", ha="center", va="center",
                color="white", fontsize=10.5, fontweight="bold")
        ax.text(xi, 101.5, f"{int(nret)} khách\nquay lại", ha="center", va="bottom",
                color=RET, fontsize=9.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=11)
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_ylim(0, 112)
    ax.set_ylabel("Tỷ trọng số lượng khách")
    ax.set_title("Tỷ trọng giảm, nhưng số người vẫn tăng",
                 fontsize=15, fontweight="bold", color=INK, loc="left", pad=22)
    ax.text(0, 1.04,
            "Tỷ trọng quay lại tụt còn 5,7% ở P2 là do mẫu số phình to (pha loãng), không phải khách cũ rời bỏ",
            transform=ax.transAxes, fontsize=10, color=MUTE)
    clean_axes(ax)
    ax.legend(loc="lower center", ncol=2, frameon=False, fontsize=10.5,
              bbox_to_anchor=(0.5, -0.16))
    save(fig, "03_ty_trong_theo_giai_doan.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 4 — Pool tích lũy vs Retention rate (Slide 9)
# ----------------------------------------------------------------------------
def chart_pool_vs_retention(df):
    new = pivot_kind(df, "Num_Of_Customers")["new"]
    ret = pivot_kind(df, "Num_Of_Customers")["ret"]
    months = list(new.index)

    # pool đến cuối tháng trước = cộng dồn khách mới tới M-1
    cum_new = new.cumsum()
    pool_prev = cum_new.shift(1)             # pool tại đầu tháng M
    retention = (ret.reindex(months) / pool_prev) * 100

    # chỉ vẽ các tháng có khách quay lại (từ T11)
    mask = ~retention.isna()
    months_r = [m for m in months if mask[m]]
    x = np.arange(len(months_r))
    pool_vals = pool_prev[months_r].values
    ret_vals = retention[months_r].values

    fig, ax1 = plt.subplots(figsize=(10, 5.4))
    ax2 = ax1.twinx()

    ax1.bar(x, pool_vals, color="#c6dafc", width=0.6,
            label="Pool khách tích lũy (đầu tháng)", zorder=2)
    for xi, v in zip(x, pool_vals):
        ax1.text(xi, v + max(pool_vals) * 0.015, f"{int(v):,}".replace(",", "."),
                 ha="center", va="bottom", fontsize=8.5, color=MUTE)

    l, = ax2.plot(x, ret_vals, color=RET, lw=2.8, marker="o", markersize=7,
                  label="Retention rate (%)", zorder=4)
    for xi, v in zip(x, ret_vals):
        ax2.text(xi, v + max(ret_vals) * 0.05, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=9.5, color=RET, fontweight="bold")

    # vùng cảnh báo điểm gãy P2 (từ T2/2026)
    if "2026-02" in months_r:
        j = months_r.index("2026-02")
        ax1.axvspan(j - 0.5, len(months_r) - 0.5, color="#fce8e6", alpha=0.6, zorder=0)
        ax2.text((j + len(months_r) - 1) / 2, max(ret_vals) * 0.55,
                 "Điểm gãy: viral kéo vào\nkhách low-intent → pool phình,\nretention kẹt ~2,8%",
                 ha="center", va="center", fontsize=9.5, color=RET)

    ax1.set_xticks(x)
    ax1.set_xticklabels([short_month(m) for m in months_r])
    ax1.set_ylabel("Pool khách tích lũy")
    ax2.set_ylabel("Retention rate", color=RET)
    ax2.tick_params(axis="y", colors=RET)
    ax2.set_ylim(0, max(ret_vals) * 1.25)
    ax2.yaxis.set_major_formatter(PercentFormatter())

    ax1.set_title("Pool đi lên, Retention đi xuống",
                  fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax1.text(0, 1.02,
             "Tăng trưởng khách mới nhanh đang che khuất sự suy yếu của phễu giữ chân",
             transform=ax1.transAxes, fontsize=10.5, color=MUTE)
    clean_axes(ax1)
    ax2.spines["top"].set_visible(False)
    # gộp legend
    h1, lb1 = ax1.get_legend_handles_labels()
    h2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, lb1 + lb2, loc="upper right", frameon=False, fontsize=10)
    save(fig, "04_pool_vs_retention.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 5 — Bất cân xứng: % đầu người vs % doanh thu (khách quay lại) (Slide 10)
# ----------------------------------------------------------------------------
def chart_spending_asymmetry(df):
    r = df[df["kind"] == "ret"].sort_values("Order_Month")
    r = r[~r["Pct_Total_Customer_Spending"].isna()]
    months = list(r["Order_Month"])
    head = r["Pct_Num_Of_Customers"].values
    spend = r["Pct_Total_Customer_Spending"].values
    y = np.arange(len(months))[::-1]  # tháng mới nhất ở trên

    fig, ax = plt.subplots(figsize=(9.5, 5.6))

    for yi, h, s in zip(y, head, spend):
        ax.plot([h, s], [yi, yi], color="#dadce0", lw=3, zorder=1)
        mult = s / h if h else float("nan")
        ax.text(max(h, s) + 1.2, yi, f"×{mult:.1f}", va="center",
                fontsize=10, color=RET, fontweight="bold")

    ax.scatter(head, y, color="#bdbdbd", s=80, zorder=3, label="% đầu người")
    ax.scatter(spend, y, color=RET, s=110, zorder=3, label="% doanh thu")

    ax.set_yticks(y)
    ax.set_yticklabels([short_month(m) for m in months])
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_xlim(0, max(spend) * 1.18)
    ax.set_xlabel("Tỷ trọng của khách quay lại")
    ax.set_title("Ít người, nhiều tiền — bất cân xứng có cấu trúc",
                 fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax.text(0, 1.02,
            "Khách quay lại luôn đóng góp doanh thu vượt xa tỷ lệ đầu người của họ (×1,2 – ×3,6)",
            transform=ax.transAxes, fontsize=10.5, color=MUTE)
    clean_axes(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=10.5)
    save(fig, "05_bat_can_xung_chi_tieu.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 6 — Hai đòn bẩy: APV vs Tần suất (tỷ lệ quay lại ÷ mới) (Slide 11)
# ----------------------------------------------------------------------------
def chart_apv_vs_frequency(df):
    apv = pivot_kind(df, "Average_Purchase_Value")
    freq = pivot_kind(df, "Buying_Frequency")

    months = [m for m in apv.index if not pd.isna(apv.loc[m, "ret"])]
    x = np.arange(len(months))
    apv_ratio = [apv.loc[m, "ret"] / apv.loc[m, "new"] for m in months]
    freq_ratio = [freq.loc[m, "ret"] / freq.loc[m, "new"] for m in months]

    C_APV = "#1a73e8"   # đòn bẩy đơn giá
    C_FRQ = "#f29900"   # đòn bẩy tần suất

    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.axhline(1.0, color=MUTE, lw=1, ls="--", zorder=1)
    ax.text(len(months) - 1, 1.02, "ngang bằng khách mới", ha="right",
            va="bottom", fontsize=9, color=MUTE)

    ax.plot(x, apv_ratio, color=C_APV, lw=2.6, marker="o", markersize=6,
            label="Hệ số APV (đơn giá)")
    ax.plot(x, freq_ratio, color=C_FRQ, lw=2.6, marker="s", markersize=6,
            label="Hệ số tần suất")

    for xi, v in zip(x, apv_ratio):
        ax.text(xi, v + 0.06, f"{v:.1f}×", ha="center", fontsize=8.5, color=C_APV)
    for xi, v in zip(x, freq_ratio):
        ax.text(xi, v - 0.12, f"{v:.1f}×", ha="center", fontsize=8.5, color=C_FRQ)

    # chú thích hội tụ APV ở P3
    ax.annotate("APV hội tụ về ~1×\n→ chuyển sang nudge tần suất",
                xy=(x[-1], apv_ratio[-1]), xytext=(x[-1] - 2.6, max(apv_ratio) * 0.9),
                fontsize=9.5, color=C_APV,
                arrowprops=dict(arrowstyle="->", color=C_APV, lw=1.4))

    ax.set_xticks(x)
    ax.set_xticklabels([short_month(m) for m in months])
    ax.set_ylabel("Lần (khách quay lại ÷ khách mới)")
    ax.set_ylim(0, max(max(apv_ratio), max(freq_ratio)) * 1.2)
    ax.set_title("APV và tần suất — hai đòn bẩy khác nhau",
                 fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax.text(0, 1.02,
            "Khoảng cách đơn giá thu hẹp dần; sức mạnh khách quay lại dồn về tần suất",
            transform=ax.transAxes, fontsize=10.5, color=MUTE)
    clean_axes(ax)
    ax.legend(loc="upper right", frameon=False, fontsize=10.5)
    save(fig, "06_apv_vs_tan_suat.png")


# ----------------------------------------------------------------------------
# BIỂU ĐỒ 7a / 7b — Cơ cấu giỏ hàng theo brand (mỗi tệp khách 1 file) (Slide 12)
# ----------------------------------------------------------------------------
def _basket_area(df, kind, fname, subtitle):
    sub = df[df["kind"] == kind].sort_values("Order_Month")
    months = list(sub["Order_Month"])
    x = np.arange(len(months))

    cols = {
        "Kinka": "Basket_Pct_Kinka_Products",
        "Revy":  "Basket_Pct_Revy_Products",
        "SiMee": "Basket_Pct_SiMee_Products",
    }
    data = {b: sub[c].fillna(0).values for b, c in cols.items()}
    other = 100 - sum(data.values())  # phần còn lại (Medical/IONCare)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.stackplot(x,
                 data["Kinka"], data["Revy"], data["SiMee"], other,
                 colors=[BRAND["Kinka"], BRAND["Revy"], BRAND["SiMee"], "#dadce0"],
                 labels=["Kinka", "Revy", "SiMee", "Khác"], alpha=0.95)

    ax.set_xticks(x)
    ax.set_xticklabels([short_month(m) for m in months])
    ax.set_xlim(0, len(months) - 1)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_ylabel("Tỷ trọng SKU trong giỏ")
    ax.set_title(f"Cơ cấu giỏ hàng — {subtitle}",
                 fontsize=15, fontweight="bold", color=INK, loc="left", pad=14)
    ax.text(0, 1.02,
            "Tỷ trọng theo số lượng sản phẩm trong giỏ (Kinka / Revy / SiMee)",
            transform=ax.transAxes, fontsize=10.5, color=MUTE)
    clean_axes(ax)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower center", ncol=4, frameon=False, fontsize=10,
              bbox_to_anchor=(0.5, -0.18))
    save(fig, fname)


def chart_basket(df):
    _basket_area(df, "new", "07a_co_cau_gio_khach_moi.png", "Khách mới")
    _basket_area(df, "ret", "07b_co_cau_gio_khach_quay_lai.png", "Khách quay lại")


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    print(f"Đang đọc dữ liệu từ '{DB_PATH}' · table '{TABLE}' ...")
    df = load_data()
    print(f"Đã nạp {len(df)} dòng. Bắt đầu dựng biểu đồ -> ./{OUT_DIR}/\n")

    chart_acquisition(df)        # 01
    chart_new_vs_returning(df)   # 02
    chart_share_by_phase(df)     # 03
    chart_pool_vs_retention(df)  # 04
    chart_spending_asymmetry(df) # 05
    chart_apv_vs_frequency(df)   # 06
    chart_basket(df)             # 07a, 07b

    print("\nHoàn tất.")


if __name__ == "__main__":
    main()