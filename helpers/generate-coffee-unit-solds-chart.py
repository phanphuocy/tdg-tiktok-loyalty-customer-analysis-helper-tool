import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import matplotlib.ticker as ticker

# --- CONFIGURATION ---
DB_PATH_1 = 'data.db'
DB_PATH_2 = 'data2.db'

SKUS_TO_PLOT = [
    {'name': 'Cà phê Muối', 'variant': '1 hộp 180g'},
    {'name': 'Cà phê Combo 3 Hộp', 'variant': '3 hộp 180g'}
]

QUERY = """
SELECT * FROM excel_data
WHERE Product_SKU_Name IN ('Cà phê Muối', 'Cà phê Combo 3 Hộp')
"""

# --- HELPER FUNCTIONS ---
def load_and_preprocess_data(db_path, query, skus):
    """Loads data from SQLite, cleans types, and filters by SKU/Variant."""
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)
        
    # Convert types
    df['Created_Time'] = pd.to_datetime(df['Created_Time'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    df['SKU_Subtotal_After_Discount'] = pd.to_numeric(df['SKU_Subtotal_After_Discount'], errors='coerce')
    
    # Ensure both original price and discount columns are numeric
    df['SKU_Unit_Original_Price'] = pd.to_numeric(df['SKU_Unit_Original_Price'], errors='coerce')
    df['SKU_Seller_Discount'] = pd.to_numeric(df['SKU_Seller_Discount'], errors='coerce')
    
    # Calculate the price after seller discount
    df['SKU_After_Seller_Discount'] = ((df['SKU_Unit_Original_Price'] * df['Quantity']) - df['SKU_Seller_Discount']) / df['Quantity']
    df['SKU_After_Seller_Discount'] = df['SKU_After_Seller_Discount'].clip(lower=0)
    
    # Create a set of valid (name, variant) tuples for fast filtering
    valid_pairs = {(s['name'], s['variant']) for s in skus}
    
    # Filter rows matching the combinations
    mask = df.apply(lambda row: (row['Product_SKU_Name'], row['Product_Variant']) in valid_pairs, axis=1)
    return df[mask].copy()


# --- MAIN EXECUTION ---
def main():
    Path("charts").mkdir(parents=True, exist_ok=True)

    # Load dataset 1 (from data2.db)
    df1 = load_and_preprocess_data(DB_PATH_1, QUERY, SKUS_TO_PLOT)
    
    # ----------------------------------------------------
    # Chart 1: Subplots / Weekly Histograms (Dataset 1)
    # ----------------------------------------------------
    plt.figure(figsize=(14, 8))
    
    for i, sku in enumerate(SKUS_TO_PLOT):
        # Additional date filtering specific to this chart
        filtered_df = df1[
            (df1['Product_SKU_Name'] == sku['name']) & 
            (df1['Product_Variant'] == sku['variant'])
        ]
        
        plt.subplot(2, 1, i + 1)
        bins = pd.date_range(start='2025-09-01', end='2026-06-14', freq='W')
        
        plt.hist(filtered_df['Created_Time'], bins=bins, color='skyblue', edgecolor='black', rwidth=0.8)
        
        plt.title(f'Sales for {sku["name"]} - {sku["variant"]} (Weekly)')
        plt.ylabel('Total Count Sold')
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
        # plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        

    plt.tight_layout()
    plt.savefig('charts/sku_histogram_combined.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 2: Stacked Weekly Bar Chart (Dataset 1)
    # ----------------------------------------------------
    weekly_data = (
        df1.set_index('Created_Time')
        .groupby([pd.Grouper(freq='W'), 'Product_SKU_Name'])['Quantity']
        .sum()
        .unstack(fill_value=0)
    )

    ax2 = weekly_data.plot(kind='bar', stacked=True, figsize=(14, 7), edgecolor='black')
    plt.title('Stacked Sales Count for "Cà phê Muối" & "Cà phê Combo 3 Hộp" (Weekly)')
    plt.xlabel('Date')
    plt.ylabel('Total Count Sold')
    plt.xticks(rotation=45)
    plt.legend(title='Product SKU')

    # Format X-axis
    labels = [item.strftime('%Y-%m-%d') for item in weekly_data.index]
    ax2.set_xticklabels(labels)

    plt.tight_layout()
    plt.savefig('charts/sku_histogram_stacked_weekly.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 3: Stacked Daily Bar Chart (Dataset 2 from data.db)
    # ----------------------------------------------------
    df2 = load_and_preprocess_data(DB_PATH_1, QUERY, SKUS_TO_PLOT)
    
    daily_data = (
        df2.set_index('Created_Time')
        .groupby([pd.Grouper(freq='D'), 'Product_SKU_Name'])['Quantity']
        .sum()
        .unstack(fill_value=0)
    )

    ax3 = daily_data.plot(kind='bar', stacked=True, figsize=(20, 8), edgecolor='none')
    plt.title('Stacked Sales Count for "Cà phê Muối" & "Cà phê Combo 3 Hộp" (Daily)')
    plt.xlabel('Date')
    plt.ylabel('Total Count Sold')
    plt.xticks(rotation=90)
    plt.legend(title='Product SKU')

    # Prevent X-axis label overcrowding
    ax3.xaxis.set_major_locator(plt.MaxNLocator(20))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))

    plt.tight_layout()
    plt.savefig('charts/sku_histogram_stacked_daily.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 4: Pricing Fluctuation Time-Series (Dataset 2)
    # ----------------------------------------------------
    # Group by Day and SKU name to get the daily average price
    daily_price_trend = (
        df2.set_index('Created_Time')
        .groupby([pd.Grouper(freq='W'), 'Product_SKU_Name'])['SKU_Subtotal_After_Discount']
        .mean()
        .unstack()
    )

    plt.figure(figsize=(14, 7))
    
    # Extract the datetime index as a clean NumPy array of dates
    dates = daily_price_trend.index.to_numpy()

    # Plotting line charts for both SKUs
    for sku_name in daily_price_trend.columns:
        # Extract column values as a clean NumPy array to prevent indexing errors
        prices = daily_price_trend[sku_name].to_numpy()
        
        plt.plot(dates, prices, marker='o', markersize=4, linestyle='-', label=sku_name)

    plt.title('Weekly Average SKU Subtotal After Discount (Price Fluctuation)')
    plt.xlabel('Date')
    plt.ylabel('Average Subtotal (VNĐ)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title='Product SKU')
    
    # Format X-axis for better date readability
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    # plt.gca().xaxis.set_major_locator(plt.MaxNLocator(15)) 
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(10000))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('charts/sku_price_fluctuation_trend.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 4: Daily Price Fluctuation (Candlestick Style)
    # ----------------------------------------------------
    # Aggregate daily min, max, and mean (average)
    daily_stats = (
        df2.set_index('Created_Time')
        .groupby([pd.Grouper(freq='D'), 'Product_SKU_Name'])['SKU_Subtotal_After_Discount']
        .agg(['min', 'max', 'mean'])
        .unstack(level='Product_SKU_Name')
    )

    # Drop days where no data exists for either SKU to clean up the plot
    daily_stats = daily_stats.dropna(how='all')

    plt.figure(figsize=(16, 8))
    
    colors = {'Cà phê Muối': '#4CAF50', 'Cà phê Combo 3 Hộp': '#FF9800'}
    dates = daily_stats.index.to_numpy()

    for sku_name in SKUS_TO_PLOT:
        name = sku_name['name']
        if name in daily_stats['mean'].columns:
            # Extract metrics as clean 1D numpy arrays
            mins = daily_stats['min'][name].to_numpy()
            maxs = daily_stats['max'][name].to_numpy()
            means = daily_stats['mean'][name].to_numpy()

            # 1. Draw the vertical line (the "wick") representing Min to Max range
            plt.vlines(dates, ymin=mins, ymax=maxs, color=colors[name], 
                       alpha=0.4, linewidth=2, label=f'{name} Range (Min-Max)')
            
            # 2. Draw a distinct marker (the "body") representing the Average Price
            plt.scatter(dates, means, color=colors[name], edgecolor='black', 
                        s=35, zorder=3, label=f'{name} Daily Avg')

    plt.title('Daily Pricing Fluctuation: Min, Max & Average Subtotal')
    plt.xlabel('Date')
    plt.ylabel('Subtotal (Currency)')
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Handle duplicate labels in legend caused by plotting loops
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper left', title='Price Metrics')

    # Format X-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(plt.MaxNLocator(15))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('charts/sku_price_candlestick_daily.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 5: Daily Average Unit Price Line Chart
    # ----------------------------------------------------
    # Group by Day and SKU, then calculate the mean of the Unit Price
    daily_avg_price = (
        df2.set_index('Created_Time')
        .groupby([pd.Grouper(freq='W'), 'Product_SKU_Name'])['SKU_Unit_Original_Price']
        .mean()
        .unstack()
    )

    # Plotting
    plt.figure(figsize=(16, 7))
    ax5 = daily_avg_price.plot(kind='line', marker='.', markersize=4, linewidth=1.5, figsize=(16, 7))

    # Formatting style
    plt.title('Daily Average Original Unit Price Trend (SKU_Unit_Original_Price)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Average Orignial Unit Price', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(title='Product SKU', frameon=True)

    # Since it's daily data, we use MaxNLocator to prevent X-axis labels from overlapping
    ax5.xaxis.set_major_locator(plt.MaxNLocator(20))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('charts/sku_avg_price_daily_line.png')
    plt.close()

    # ----------------------------------------------------
    # Chart 6: Daily Average Price After Seller Discount
    # ----------------------------------------------------
    # Resample daily and calculate the mean of your new calculated column
    daily_discounted_price = (
        df2.set_index('Created_Time')
        .groupby([pd.Grouper(freq='W'), 'Product_SKU_Name'])['SKU_After_Seller_Discount']
        .mean()
        .unstack()
    )

    # Plotting the daily time-series line chart
    plt.figure(figsize=(16, 7))
    ax6 = daily_discounted_price.plot(kind='line', marker='.', markersize=4, linewidth=1.5, figsize=(16, 7))

    # Formatting style
    plt.title('Daily Average Price After Seller Discount', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price After Discount (VND / Unit)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(title='Product SKU', frameon=True)

    # MaxNLocator handles dense daily dates seamlessly without text overlapping
    ax6.xaxis.set_major_locator(plt.MaxNLocator(20))
    ax6.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
    ax6.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax6.yaxis.set_major_locator(ticker.MultipleLocator(5000))
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('charts/sku_after_seller_discount_daily.png')
    plt.close()

    

if __name__ == "__main__":
    main()