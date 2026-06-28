# -*- coding: utf-8 -*-
"""
build_overview_charts.py
=========================
Tự động sinh bộ biểu đồ minh hoạ phần "Ngữ cảnh kinh doanh" cho báo cáo
"Phân tích khách hàng mới & quay lại — Kênh TikTok Trường Dương Store".

Nguồn dữ liệu: SQLite (data.db)
  - Biểu đồ tổng quan  -> bảng `pivot_monthly_customers_acquisition`
  - Biểu đồ theo SKU   -> bảng đơn hàng thô (mặc định `orders_raw`)

Cách chạy:
    python build_overview_charts.py
Toàn bộ ảnh PNG (300 DPI) được lưu vào thư mục ./charts/
"""

import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MultipleLocator

# ======================================================================
# 1. CẤU HÌNH  — chỉnh ở đây cho khớp môi trường của bạn
# ======================================================================
DB_PATH          = "data.db"                              # file SQLite
PIVOT_TABLE      = "pivot_monthly_customers_acquisition"  # bảng pivot tháng
RAW_ORDERS_TABLE = "excel_data"                           # bảng đơn hàng thô
OUT_DIR          = "charts/overview/"

# Phạm vi báo cáo: từ ngày lập shop đến hết 31/05/2026 (đồng bộ với pivot)
SCOPE_END = pd.Timestamp("2026-05-31 23:59:59")

# 3 SKU cà phê cần vẽ (Product_SKU_Name, Product_Variant)
SKU_TARGETS = [
    ("Cà phê Muối",       "1 hộp 180g"),
    ("Cà phê Combo 3 Hộp", "3 hộp 180g"),
    ("Cà phê Combo 5 Hộp", "5 hộp 180g"),
]

# Bảng màu thương hiệu (dùng nhất quán toàn báo cáo)
BRAND = {
    "Kinka":   {"col": "#fbbc04", "label": "Kinka (Trà & Cà phê)"},
    "Revy":    {"col": "#4285f4", "label": "Revy (Chăm sóc gia đình)"},
    "SiMee":   {"col": "#ea4335", "label": "SiMee (Chăm sóc cá nhân)"},
    "Medical": {"col": "#4C78A8", "label": "Y tế"},
    "IONCare": {"col": "#9C6FB0", "label": "IONCare"},
}
BRAND_ORDER = ["Kinka", "Revy", "SiMee", "Medical", "IONCare"]

# Màu cho 2 tệp khách
C_NEW    = "#4285f4"   # khách mới
C_RETURN = "#ea4335"   # khách quay lại
C_ORDER  = "#9B2226"   # đường số đơn

# Màu cho 3 SKU (dùng ở biểu đồ stacked units)
SKU_COLORS = {
    "Cà phê Muối":        "#1f77b4",
    "Cà phê Combo 3 Hộp": "#ff7f0e",
    "Cà phê Combo 5 Hộp": "#9467bd",
}

# 3 giai đoạn kinh doanh (để vẽ dải nền)
PHASES = [
    ("2025-09", "2025-12", "GĐ 1 · Thiết lập nền tảng", "#EDEDED"),
    ("2026-01", "2026-03", "GĐ 2 · Bùng nổ cận/sau Tết", "#FBEFDD"),
    ("2026-04", "2026-05", "GĐ 3 · Tối ưu nội dung & giá", "#E5F0E9"),
]

# ======================================================================
# 2. STYLE & HELPERS
# ======================================================================
plt.rcParams.update({
    # "font.family": "DejaVu Sans",
    "font.family": "Open Sans",
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.edgecolor": "#888888",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#E6E6E6",
    "grid.linewidth": 0.8,
    "figure.dpi": 110,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

VN_MONTH = {9: "Th9", 10: "Th10", 11: "Th11", 12: "Th12",
            1: "Th1", 2: "Th2", 3: "Th3", 4: "Th4", 5: "Th5"}


def month_label(ym):
    """'2026-01' -> 'Th1\\n2026' (chỉ hiện năm ở tháng đầu mỗi năm)."""
    y, m = ym.split("-")
    m = int(m)
    if m in (1, 9) or m == 10:   # mốc bắt đầu năm / bắt đầu shop
        return f"{VN_MONTH[m]}\n{y}"
    return VN_MONTH[m]


def vnd_millions(x, _pos=None):
    return f"{x/1e6:.0f}tr" if x else "0"


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


def draw_phase_bands(ax, months, y=1.0, label=True):
    """Tô dải nền 3 giai đoạn theo vị trí tháng trên trục x (index-based)."""
    idx = {m: i for i, m in enumerate(months)}
    for start, end, name, col in PHASES:
        if start not in idx or end not in idx:
            present = [m for m in months if start <= m <= end]
            if not present:
                continue
            x0, x1 = idx[present[0]], idx[present[-1]]
        else:
            x0, x1 = idx[start], idx[end]
        ax.axvspan(x0 - 0.5, x1 + 0.5, color=col, alpha=0.55, zorder=0)
        if label:
            ax.text((x0 + x1) / 2, y, name, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=9.5, color="#555555",
                    fontweight="bold")


def active_months(pv):
    """Các tháng có phát sinh doanh thu (loại tháng rỗng đầu kỳ, vd 2025-09)."""
    tot = pv.groupby("Order_Month")["Total_Customer_Spending"].sum()
    return [m for m in sorted(pv["Order_Month"].unique()) if tot.get(m, 0) > 0]


def savefig(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"  ✓ {path}")
    return path


# ======================================================================
# 3. ĐỌC DỮ LIỆU
# ======================================================================
def load_pivot():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {PIVOT_TABLE}", con)
    con.close()
    num = df.columns.difference(["Order_Month", "Acquisition_Type"])
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df = df.sort_values("Order_Month").reset_index(drop=True)
    return df


def load_orders():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {RAW_ORDERS_TABLE}", con)
    con.close()
    for c in ["SKU_Unit_Original_Price", "Quantity",
              "SKU_Seller_Discount", "Order_Amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["dt"] = pd.to_datetime(df["Created_Time"],
                              format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df = df[df["dt"].notna() & (df["dt"] <= SCOPE_END)]
    return df


# ======================================================================
# 4. BIỂU ĐỒ TỔNG QUAN (nguồn: bảng pivot)
# ======================================================================
def chart_revenue_orders(pv):
    """HERO: Doanh thu gộp (khách mới vs quay lại) + số đơn theo tháng."""
    months = active_months(pv)
    p = pv.pivot_table(index="Order_Month", columns="Acquisition_Type",
                       values="Total_Customer_Spending", aggfunc="sum",
                       fill_value=0).reindex(months)
    new = p.get("Newly Accquired", pd.Series(0, index=months))
    ret = p.get("Return From Previous Month", pd.Series(0, index=months))
    orders = pv.groupby("Order_Month")["Num_of_Orders"].sum().reindex(months)

    x = np.arange(len(months))
    fig, ax = plt.subplots(figsize=(12, 6.2))
    draw_phase_bands(ax, months, y=1.02)

    ax.bar(x, new.values, color=C_NEW, label="Khách mới", width=0.62, zorder=3)
    ax.bar(x, ret.values, bottom=new.values, color=C_RETURN,
           label="Khách quay lại", width=0.62, zorder=3)

    total = (new + ret).values
    for i, t in enumerate(total):
        if t > 0:
            ax.text(i, t * 1.01, f"{t/1e6:.1f}tr", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color="#333")

    ax.set_ylabel("Doanh thu gộp (VND)")
    ax.yaxis.set_major_formatter(FuncFormatter(vnd_millions))
    ax.set_ylim(0, total.max() * 1.18)

    ax2 = ax.twinx()
    ax2.plot(x, orders.values, color=C_ORDER, marker="o", lw=2.4,
             markersize=6, label="Số đơn hàng", zorder=4)
    for i, o in enumerate(orders.values):
        ax2.annotate(f"{int(o)}", (i, o), textcoords="offset points",
                     xytext=(0, -13), ha="center", va="top", fontsize=8.5,
                     color=C_ORDER, fontweight="bold", zorder=6,
                     bbox=dict(boxstyle="round,pad=0.15", fc="white",
                               ec="none", alpha=0.9))
    ax2.set_ylabel("Số đơn hàng", color=C_ORDER)
    ax2.tick_params(axis="y", colors=C_ORDER)
    ax2.set_ylim(0, orders.max() * 1.35)
    ax2.grid(False)
    ax2.spines["top"].set_visible(False)

    ax.set_xticks(x)
    ax.set_xticklabels([month_label(m) for m in months])
    style_axis(ax)
    ax.set_title("Doanh thu gộp & sản lượng đơn theo tháng — toàn shop",
                 loc="left", pad=26)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, ncol=3,
              bbox_to_anchor=(0, 0.99))
    fig.text(0.01, -0.02,
             "Doanh thu tính theo Gross (gồm cả đơn hoàn/huỷ, affiliate). "
             "Cao điểm T1/2026 nhờ Cà phê Muối + mùa Tết.",
             fontsize=8.5, color="#888")
    return savefig(fig, "01_doanh_thu_don_hang.png")


def chart_brand_share(pv):
    """Cơ cấu thương hiệu trong giỏ: % số lượng & % chi tiêu theo tháng."""
    months = active_months(pv)
    units = pv.groupby("Order_Month")[
        [f"Basket_Num_{b}_Products" for b in BRAND_ORDER]].sum().reindex(months)
    spend = pv.groupby("Order_Month")[
        [f"Basket_{b}_Spend_Amnt" for b in BRAND_ORDER]].sum().reindex(months)
    units.columns = BRAND_ORDER
    spend.columns = BRAND_ORDER
    units_pct = units.div(units.sum(axis=1), axis=0).fillna(0) * 100
    spend_pct = spend.div(spend.sum(axis=1), axis=0).fillna(0) * 100

    x = np.arange(len(months))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, data, ttl in [(axes[0], units_pct, "Theo SỐ LƯỢNG sản phẩm"),
                          (axes[1], spend_pct, "Theo CHI TIÊU (VND)")]:
        bottom = np.zeros(len(months))
        for b in BRAND_ORDER:
            ax.bar(x, data[b].values, bottom=bottom, width=0.72,
                   color=BRAND[b]["col"], label=BRAND[b]["label"], zorder=3)
            # ghi nhãn % cho Kinka & Revy (2 brand quan trọng nhất)
            if b in ("Kinka", "Revy"):
                for i, v in enumerate(data[b].values):
                    if v >= 7:
                        ax.text(i, bottom[i] + v / 2, f"{v:.0f}", ha="center",
                                va="center", fontsize=8, color="white",
                                fontweight="bold")
            bottom += data[b].values
        ax.set_title(ttl, loc="left", fontsize=13, pad=10)
        ax.set_ylim(0, 100)
        ax.set_xticks(x)
        ax.set_xticklabels([month_label(m) for m in months], fontsize=9.5)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        style_axis(ax)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False,
               bbox_to_anchor=(0.5, -0.04), fontsize=10)
    fig.suptitle("Cơ cấu thương hiệu trong giỏ hàng — giỏ ngày càng kém đa dạng",
                 x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    return savefig(fig, "02_co_cau_thuong_hieu.png")


def chart_brand_spend_abs(pv):
    """Quy mô chi tiêu theo thương hiệu (stacked) — ai đang gánh doanh thu."""
    months = active_months(pv)
    spend = pv.groupby("Order_Month")[
        [f"Basket_{b}_Spend_Amnt" for b in BRAND_ORDER]].sum().reindex(months)
    spend.columns = BRAND_ORDER
    x = np.arange(len(months))

    fig, ax = plt.subplots(figsize=(12, 6))
    draw_phase_bands(ax, months, y=1.02)
    bottom = np.zeros(len(months))
    for b in BRAND_ORDER:
        ax.bar(x, spend[b].values, bottom=bottom, width=0.66,
               color=BRAND[b]["col"], label=BRAND[b]["label"], zorder=3)
        bottom += spend[b].values
    for i, t in enumerate(bottom):
        if t > 0:
            ax.text(i, t * 1.01, f"{t/1e6:.0f}tr", ha="center", va="bottom",
                    fontsize=8.5, color="#333", fontweight="bold")

    ax.set_ylabel("Giá trị hàng hoá trong giỏ (VND)")
    ax.yaxis.set_major_formatter(FuncFormatter(vnd_millions))
    ax.set_ylim(0, bottom.max() * 1.16)
    ax.set_xticks(x)
    ax.set_xticklabels([month_label(m) for m in months])
    style_axis(ax)
    ax.set_title("Doanh thu giỏ hàng theo thương hiệu — Revy gánh GĐ1, "
                 "Kinka bùng nổ GĐ2–3", loc="left", pad=26)
    ax.legend(loc="upper left", frameon=False, ncol=5,
              bbox_to_anchor=(0, 0.99), fontsize=9.5)
    return savefig(fig, "03_doanh_thu_theo_thuong_hieu.png")


def chart_aov_basket(pv):
    """AOV & Avg basket size: khách mới vs khách quay lại."""
    months = active_months(pv)
    x = np.arange(len(months))

    def series(col, atype):
        s = pv[pv["Acquisition_Type"] == atype].set_index("Order_Month")[col]
        return s.reindex(months)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))

    # AOV
    ax = axes[0]
    draw_phase_bands(ax, months, label=False)
    ax.plot(x, series("Average_Purchase_Value", "Newly Accquired").values,
            color=C_NEW, marker="o", lw=2.3, label="Khách mới")
    ax.plot(x, series("Average_Purchase_Value", "Return From Previous Month").values,
            color=C_RETURN, marker="s", lw=2.3, label="Khách quay lại")
    ax.set_title("Giá trị đơn trung bình (AOV)", loc="left", pad=10)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:.0f}k"))
    ax.set_ylabel("VND / đơn")

    # Basket size
    ax = axes[1]
    draw_phase_bands(ax, months, label=False)
    ax.plot(x, series("Avg_Basket_Size", "Newly Accquired").values,
            color=C_NEW, marker="o", lw=2.3, label="Khách mới")
    ax.plot(x, series("Avg_Basket_Size", "Return From Previous Month").values,
            color=C_RETURN, marker="s", lw=2.3, label="Khách quay lại")
    ax.axhline(1.0, color="#bbb", ls="--", lw=1)
    ax.set_title("Số sản phẩm trung bình / giỏ (cross-sell)", loc="left", pad=10)
    ax.set_ylabel("Sản phẩm / khách")

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([month_label(m) for m in months], fontsize=9.5)
        style_axis(ax)
        ax.legend(frameon=False, loc="upper right")

    fig.suptitle("Khách quay lại có giá trị đơn & giỏ hàng cao hơn khách mới",
                 x=0.01, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return savefig(fig, "04_aov_basket_size.png")


def chart_cancellation(pv):
    """Tỷ lệ huỷ đơn theo tháng — thất thoát chi phí thu hút khách."""
    months = active_months(pv)
    x = np.arange(len(months))

    def series(atype):
        s = pv[pv["Acquisition_Type"] == atype].set_index("Order_Month")["Cancellation_Rate"]
        return s.reindex(months)

    fig, ax = plt.subplots(figsize=(12, 5.4))
    draw_phase_bands(ax, months, y=1.02)
    ax.plot(x, series("Newly Accquired").values, color=C_NEW, marker="o",
            lw=2.3, label="Khách mới")
    ax.plot(x, series("Return From Previous Month").values, color=C_RETURN,
            marker="s", lw=2.3, label="Khách quay lại")
    ax.set_ylabel("Tỷ lệ huỷ đơn (%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(0, max(28, np.nanmax(series('Newly Accquired').values) * 1.2))
    ax.set_xticks(x)
    ax.set_xticklabels([month_label(m) for m in months])
    style_axis(ax)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Tỷ lệ huỷ đơn theo tháng — đỉnh điểm cao điểm Tết (T1–T2)",
                 loc="left", pad=26)
    return savefig(fig, "05_ty_le_huy_don.png")


# ======================================================================
# 5. BIỂU ĐỒ THEO SKU (nguồn: bảng đơn hàng thô)
# ======================================================================
def _weekly_price(df_sku):
    """Tính giá trung bình theo tuần (loại các dòng affiliate/quà tặng giá 0)."""
    d = df_sku[df_sku["SKU_Unit_Original_Price"] > 0].copy()
    d["after_seller"] = ((d["SKU_Unit_Original_Price"] * d["Quantity"])
                         - d["SKU_Seller_Discount"]) / d["Quantity"]
    d["cust_paid"] = d["Order_Amount"] / d["Quantity"]
    w = (d.set_index("dt")[["SKU_Unit_Original_Price", "after_seller", "cust_paid"]]
           .resample("W-MON").mean())
    return w


def chart_sku_price(orders, sku_name, variant):
    df_sku = orders[(orders["Product_SKU_Name"] == sku_name)
                    & (orders["Product_Variant"] == variant)]
    w = _weekly_price(df_sku)
    if w.empty:
        print(f"  ! Bỏ qua (không có dữ liệu): {sku_name}")
        return None

    # .to_numpy() để tương thích matplotlib cũ (tránh lỗi multi-dim indexing
    # khi truyền thẳng DatetimeIndex/Series của pandas mới)
    xv = w.index.to_numpy()
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.plot(xv, w["SKU_Unit_Original_Price"].to_numpy(), color="#9AA0A6", lw=2,
            marker="o", ms=4, label="Giá gốc (niêm yết)")
    ax.plot(xv, w["after_seller"].to_numpy(), color="#E08A2B", lw=2.4,
            marker="o", ms=4, label="Giá sau chiết khấu nhà bán")
    ax.plot(xv, w["cust_paid"].to_numpy(), color="#1F3A5F", lw=2.6,
            marker="o", ms=4, label="Giá khách thực trả")

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:.0f}k"))
    ax.set_ylabel("VND / đơn vị")
    style_axis(ax)
    ax.legend(frameon=False, loc="best", ncol=1)
    ax.set_title(f"Diễn biến giá theo tuần — {sku_name} ({variant})",
                 loc="left", pad=12)
    fig.text(0.01, -0.03,
             "Giá TB theo tuần (mốc trục X = đầu mỗi tháng). Đã loại dòng "
             "affiliate/quà tặng (giá gốc = 0).", fontsize=8.5, color="#888")
    fname = "06_gia_" + (sku_name.replace(" ", "_")
                         .replace("à", "a").replace("ê", "e")
                         .replace("ố", "o").replace("ộ", "o")) + ".png"
    return savefig(fig, fname)


def chart_sku_units_stacked(orders):
    """Stacked bar: số đơn vị bán (gross) của 3 SKU theo tuần."""
    frames = {}
    for name, variant in SKU_TARGETS:
        d = orders[(orders["Product_SKU_Name"] == name)
                   & (orders["Product_Variant"] == variant)]
        frames[name] = (d.set_index("dt")["Quantity"]
                        .resample("W-MON").sum())
    units = pd.DataFrame(frames).fillna(0)
    units = units.loc[units.sum(axis=1) > 0]  # bỏ tuần trống đầu kỳ

    fig, ax = plt.subplots(figsize=(12.5, 6))
    xv = units.index.to_numpy()          # tương thích matplotlib cũ
    bottom = np.zeros(len(units))
    width = 5.2  # ngày
    for name, _ in SKU_TARGETS:
        ax.bar(xv, units[name].to_numpy(), bottom=bottom, width=width,
               color=SKU_COLORS[name], label=name, align="center", zorder=3)
        bottom += units[name].to_numpy()
    for xi, tot in zip(xv, bottom):
        if tot > 0:
            ax.text(xi, tot + bottom.max() * 0.015, f"{int(tot)}",
                    ha="center", va="bottom", fontsize=7.5, color="#444")

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.set_ylabel("Số đơn vị bán (gross)")
    ax.set_ylim(0, bottom.max() * 1.15)
    style_axis(ax)
    ax.legend(frameon=False, loc="upper left", ncol=3)
    ax.set_title("Sản lượng 3 SKU cà phê chủ lực theo tuần — Combo 3 Hộp "
                 "vươn lên dẫn dắt", loc="left", pad=12)
    return savefig(fig, "07_san_luong_3_sku.png")


# ======================================================================
# 6. MAIN
# ======================================================================
def main():
    print("→ Đọc dữ liệu từ", DB_PATH)
    pv = load_pivot()
    orders = load_orders()

    print("→ Sinh biểu đồ tổng quan (nguồn: pivot):")
    chart_revenue_orders(pv)
    chart_brand_share(pv)
    chart_brand_spend_abs(pv)
    chart_aov_basket(pv)
    chart_cancellation(pv)

    print("→ Sinh biểu đồ giá theo SKU (nguồn: đơn hàng thô):")
    for name, variant in SKU_TARGETS:
        chart_sku_price(orders, name, variant)

    print("→ Sinh biểu đồ sản lượng 3 SKU:")
    chart_sku_units_stacked(orders)

    print(f"\nHoàn tất. Ảnh nằm trong thư mục ./{OUT_DIR}/")


if __name__ == "__main__":
    main()