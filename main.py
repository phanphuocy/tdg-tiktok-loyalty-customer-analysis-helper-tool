from openpyxl import load_workbook
import sqlite3
from pathlib import Path

from labelling import label_tuples_from_csv, add_label_header_tuple

orders_filename = 'Tất cả đơn hàng-2026-06-01-07_52.xlsx'
orders_active_sheet = 'OrderSKUList'

product_labels_filename = 'Product_Additional_Labels - Product_AddtionalLabels_Labels.csv'
product_labels_sheet = 'Product_AddtionalLabels_Labels'

orders_workbook = load_workbook(filename=orders_filename)
orders_sheet = orders_workbook[orders_active_sheet]

# 2. Extract rows (Separating headers from data)
orders_rows = list(orders_sheet.iter_rows(values_only=True))
if not orders_rows:
    print("The Excel sheet is empty.")
    exit()

orders_headers = orders_rows[0]  # First row contains column names
orders_data_rows = orders_rows[2:]  # Remaining rows contain the actual data

labelled_tuples, missing_ids = label_tuples_from_csv(
    csv_path=product_labels_filename,
    tuples=orders_data_rows,
    id_index=5,
)

labelled_headers = add_label_header_tuple(orders_headers)

# 3. Clean headers for SQL safety (replace spaces/special chars with underscores)
clean_headers = [
    str(h).strip().replace(" ", "_").replace("-", "_") if h else f"column_{i}"
    for i, h in enumerate(labelled_headers)
]

# 4. Connect to SQLite database (creates 'data.db' file if it doesn't exist)
file_path = Path('data.db')

if file_path.is_file():
    file_path.unlink()

conn = sqlite3.connect("data.db")
cursor = conn.cursor()

# 5. Dynamically create the SQL table based on Excel headers
# All columns are set to TEXT for safety, but SQLite handles dynamic typing
columns_query = ", ".join([f"[{name}] TEXT" for name in clean_headers])
create_table_query = f"CREATE TABLE IF NOT EXISTS excel_data ({columns_query})"
cursor.execute(create_table_query)

# 6. Build the INSERT query and inject the data rows
placeholders = ", ".join(["?"] * len(clean_headers))
insert_query = f"INSERT INTO excel_data VALUES ({placeholders})"

cursor.executemany(insert_query, labelled_tuples)
print(f"Successfully converted {len(labelled_tuples)} rows into 'data.db'!")

cursor.execute("DROP TABLE IF EXISTS total_orders_data;")
cursor.execute(
    """
    CREATE TABLE total_orders_data AS
        SELECT Order_ID, Order_Amount, Order_Status,
            (
                SUBSTR(Created_Time, 7, 4) || '-' ||   -- YYYY
                SUBSTR(Created_Time, 4, 2) || '-' ||   -- MM
                SUBSTR(Created_Time, 1, 2) || ' ' ||   -- DD
                SUBSTR(Created_Time, 12, 2) || ':' ||  -- HH
                SUBSTR(Created_Time, 15, 2)            -- MM
            ) AS Order_Time,
            COALESCE(Buyer_Username, "No Username") AS Buyer_Username,
            SUM(SKU_Subtotal_After_Discount) AS Sum_SKU_Subtotal_After_Discount,
            SUM(SKU_Subtotal_After_Discount) - Order_Amount AS Different_Amount,
            COUNT(CASE WHEN Brand = 'Kinka' THEN 1 END) AS Basket_Num_Kinka_Products,
            COUNT(CASE WHEN Brand = 'Revy' THEN 1 END) AS Basket_Num_Revy_Products,
            COUNT(CASE WHEN Brand = 'SiMee' THEN 1 END) AS Basket_Num_SiMee_Products,
            COUNT(CASE WHEN Brand = 'Y tế' THEN 1 END) AS Basket_Num_Medical_Products,
            COUNT(CASE WHEN Brand = 'IONCare' THEN 1 END) AS Basket_Num_IONCare_Products,
            SUM(CASE WHEN Brand = 'Kinka' THEN SKU_Subtotal_After_Discount END) AS Basket_Kinka_Spend_Amnt,
            SUM(CASE WHEN Brand = 'Revy' THEN SKU_Subtotal_After_Discount END) AS Basket_Revy_Spend_Amnt,
            SUM(CASE WHEN Brand = 'SiMee' THEN SKU_Subtotal_After_Discount END) AS Basket_SiMee_Spend_Amnt,
            SUM(CASE WHEN Brand = 'Y tế' THEN SKU_Subtotal_After_Discount END) AS Basket_Medical_Spend_Amnt,
            SUM(CASE WHEN Brand = 'IONCare' THEN SKU_Subtotal_After_Discount END) AS Basket_IONCare_Spend_Amnt,
            SUM(CASE WHEN Brand = 'Kinka' THEN Pack_Size END) AS Basket_Total_Kinka_Packsize,
            SUM(CASE WHEN Brand = 'Revy' THEN Pack_Size END) AS Basket_Total_Revy_Packsize,
            SUM(CASE WHEN Brand = 'SiMee' THEN Pack_Size END) AS Basket_Total_SiMee_Packsize,
            SUM(CASE WHEN Brand = 'IONCare' THEN Pack_Size END) AS Basket_Total_IONCare_Packsize,
            SUM(CASE WHEN Brand = 'Y tế' THEN Pack_Size END) AS Basket_Total_Medical_Packsize
        FROM excel_data
        GROUP BY Order_ID
        ORDER BY Order_Time DESC;
    """
)
cursor.execute("SELECT * FROM total_orders_data")
total_orders_data = cursor.fetchall()
print(f"Successfully added {len(total_orders_data)} rows into 'total_orders_data' table!")

cursor.execute("DROP TABLE IF EXISTS total_customers_data;")
cursor.execute(
    """
    CREATE TABLE total_customers_data AS
    WITH customer_aggregates AS (
        -- Step 1: Do the math
        SELECT 
            Buyer_Username,
            COUNT(Order_ID) AS Num_of_Orders,
            COUNT(CASE WHEN Order_Status = 'Đã hủy' THEN 1 END) AS Num_of_Canceled_Orders,
            MIN(Order_Time) AS First_Seen,
            MAX(Order_Time) AS Last_Seen,
            (JULIANDAY(MAX(Order_Time)) - JULIANDAY(MIN(Order_Time))) AS Retention_Time_Period,
            SUM(Order_Amount) AS Total_Customer_Spending,
            SUM(Sum_SKU_Subtotal_After_Discount) AS Merchandise_Value,
            SUM(Order_Amount) / COUNT(Order_ID) AS Average_Purchase_Value,
            SUM(Basket_Num_Kinka_Products) AS Basket_Num_Kinka_Products,
            SUM(Basket_Num_Revy_Products) AS Basket_Num_Revy_Products,
            SUM(Basket_Num_SiMee_Products) AS Basket_Num_SiMee_Products,
            SUM(Basket_Num_Medical_Products) AS Basket_Num_Medical_Products,
            SUM(Basket_Num_IONCare_Products) AS Basket_Num_IONCare_Products,
            SUM(Basket_Num_Kinka_Products) + SUM(Basket_Num_Revy_Products) + SUM(Basket_Num_SiMee_Products) + SUM(Basket_Num_Medical_Products) + SUM(Basket_Num_IONCare_Products) AS Basket_Total_Num_Products,
            ROUND(((SUM(Basket_Num_Kinka_Products) + SUM(Basket_Num_Revy_Products) + SUM(Basket_Num_SiMee_Products) + SUM(Basket_Num_Medical_Products) + SUM(Basket_Num_IONCare_Products)) * 100.0 / COUNT(Order_ID)) / 100, 2) AS Avg_Basket_Size,
            SUM(Basket_Kinka_Spend_Amnt) AS Basket_Kinka_Spend_Amnt,
            SUM(Basket_Revy_Spend_Amnt) AS Basket_Revy_Spend_Amnt,
            SUM(Basket_SiMee_Spend_Amnt) AS Basket_SiMee_Spend_Amnt,
            SUM(Basket_Medical_Spend_Amnt) AS Basket_Medical_Spend_Amnt,
            SUM(Basket_IONCare_Spend_Amnt) AS Basket_IONCare_Spend_Amnt,
            SUM(Basket_Total_Kinka_Packsize) AS Basket_Total_Kinka_Packsize,
            SUM(Basket_Total_Revy_Packsize) AS Basket_Total_Revy_Packsize,
            SUM(Basket_Total_SiMee_Packsize) AS Basket_Total_SiMee_Packsize,
            SUM(Basket_Total_Medical_Packsize) AS Basket_Total_Medical_Packsize,
            SUM(Basket_Total_IONCare_Packsize) AS Basket_Total_IONCare_Packsize
        FROM total_orders_data
        GROUP BY Buyer_Username
    )
    SELECT 
        *,
        -- Calculates proportions of brand's product in basket --
        ROUND(Basket_Num_Kinka_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Kinka_Products,
        ROUND(Basket_Num_Revy_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Revy_Products,
        ROUND(Basket_Num_SiMee_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_SiMee_Products,
        ROUND(Basket_Num_Medical_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Medical_Products,
        ROUND(Basket_Num_IONCare_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_IONCare_Products,
        CASE 
            WHEN Num_of_Orders >= 1 AND Total_Customer_Spending = 0 THEN 'Affiliator'
            WHEN (Num_Of_Orders - Num_of_Canceled_Orders = 0) THEN 'Canceled/No Purchases'
            WHEN Retention_Time_Period < 0.0208 AND Num_Of_Orders >= 2 AND (Num_Of_Orders - Num_of_Canceled_Orders >= 1) AND Num_of_Canceled_Orders != 0 THEN 'Confused One-Time Buyer'
            WHEN Num_of_Orders >= 2 THEN 'Regular / Loyal'
            WHEN Num_of_Orders = 1 THEN 'One-Time Buyer'
            ELSE 'Unsorted'
        END AS Loyalty_Tier
    FROM customer_aggregates;
    """
)
cursor.execute("SELECT * FROM total_customers_data")
total_customers_data = cursor.fetchall()
print(f"Successfully added {len(total_customers_data)} rows into 'total_customers_data' table!")


cursor.execute("DROP TABLE IF EXISTS total_customers_loyalty;")
cursor.execute(
    """
    CREATE TABLE total_customers_loyalty AS
    WITH customer_loyalty_aggregates AS (
        SELECT 
            Loyalty_Tier, 
            COUNT(Buyer_Username) AS Num_Of_Customers,
            ROUND((COUNT(Buyer_Username) * 100.0) / SUM(COUNT(Buyer_Username)) OVER(), 2) AS Pct_Num_Of_Customers,
            SUM(Total_Customer_Spending) AS Total_Customer_Spending,
            ROUND((SUM(Total_Customer_Spending) * 100.0) / SUM(SUM(Total_Customer_Spending)) OVER(), 2) AS Pct_Total_Customer_Spending,
            SUM(Total_Customer_Spending) / SUM(Num_of_Orders) AS Average_Purchase_Value,
            ROUND(AVG(Num_Of_Orders), 2) AS Avg_Num_Of_Orders,
            ROUND(AVG(Num_of_Canceled_Orders), 2) AS Avg_Num_of_Canceled_Orders,
            ROUND((SUM(Num_of_Canceled_Orders) * 100.0) / SUM(Num_Of_Orders), 2) AS Canceled_Rate,
            ROUND(AVG(Retention_Time_Period), 2) AS Avg_Retention_Time_Period,
            SUM(Basket_Num_Kinka_Products) AS Basket_Num_Kinka_Products,
            SUM(Basket_Num_Revy_Products) AS Basket_Num_Revy_Products,
            SUM(Basket_Num_SiMee_Products) AS Basket_Num_SiMee_Products,
            SUM(Basket_Num_Medical_Products) AS Basket_Num_Medical_Products,
            SUM(Basket_Num_IONCare_Products) AS Basket_Num_IONCare_Products,
            SUM(Basket_Kinka_Spend_Amnt) AS Basket_Kinka_Spend_Amnt,
            SUM(Basket_Revy_Spend_Amnt) AS Basket_Revy_Spend_Amnt,
            SUM(Basket_SiMee_Spend_Amnt) AS Basket_SiMee_Spend_Amnt,
            SUM(Basket_Medical_Spend_Amnt) AS Basket_Medical_Spend_Amnt,
            SUM(Basket_IONCare_Spend_Amnt) AS Basket_IONCare_Spend_Amnt,	
            SUM(Basket_Num_Kinka_Products) + SUM(Basket_Num_Revy_Products) + SUM(Basket_Num_SiMee_Products) + SUM(Basket_Num_Medical_Products) + SUM(Basket_Num_IONCare_Products) AS Basket_Total_Num_Products,
            ROUND(((SUM(Basket_Num_Kinka_Products) + SUM(Basket_Num_Revy_Products) + SUM(Basket_Num_SiMee_Products) + SUM(Basket_Num_Medical_Products) + SUM(Basket_Num_IONCare_Products)) * 100.0 / SUM(Num_Of_Orders)) / 100, 2) AS Avg_Basket_Size,
            ROUND(SUM(Basket_Total_Kinka_Packsize) / SUM(Basket_Num_Kinka_Products), 2) AS Basket_Avg_Kinka_Packsize,
            ROUND(SUM(Basket_Total_Revy_Packsize) / SUM(Basket_Num_Revy_Products), 2) AS Basket_Avg_Revy_Packsize,
            ROUND(SUM(Basket_Total_SiMee_Packsize) / SUM(Basket_Num_SiMee_Products), 2) AS Basket_Avg_SiMee_Packsize,
            ROUND(SUM(Basket_Total_Medical_Packsize) / SUM(Basket_Num_Medical_Products), 2) AS Basket_Avg_Medical_Packsize,
            ROUND(SUM(Basket_Total_IONCare_Packsize) / SUM(Basket_Num_IONCare_Products), 2) AS Basket_Avg_IONCare_Packsize
        FROM total_customers_data
        GROUP BY Loyalty_Tier
        ORDER BY Loyalty_Tier
    ) SELECT 
        *,
        -- Percentages of each brand --
        ROUND(Basket_Num_Kinka_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Kinka_Products,
        ROUND(Basket_Num_Revy_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Revy_Products,
        ROUND(Basket_Num_SiMee_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_SiMee_Products,
        ROUND(Basket_Num_Medical_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_Medical_Products,
        ROUND(Basket_Num_IONCare_Products * 100.0 / Basket_Total_Num_Products, 2) AS Basket_Pct_IONCare_Products,
        Basket_Kinka_Spend_Amnt / Basket_Num_Kinka_Products AS Basket_Avg_Spend_On_Kinka,
        Basket_Revy_Spend_Amnt / Basket_Num_Revy_Products AS Basket_Avg_Spend_On_Revy,
        Basket_SiMee_Spend_Amnt / Basket_Num_SiMee_Products AS Basket_Avg_Spend_On_SiMee,
        Basket_Medical_Spend_Amnt / Basket_Num_Medical_Products AS Basket_Avg_Spend_On_Medical,
        Basket_IONCare_Spend_Amnt / Basket_Num_IONCare_Products AS Basket_Avg_Spend_On_IONCare
    FROM customer_loyalty_aggregates;
    """
)

cursor.execute("SELECT * FROM total_customers_loyalty")
total_customers_loyalty = cursor.fetchall()
print(f"Successfully added {len(total_customers_loyalty)} rows into 'total_customers_loyalty' table!")


# 7. Commit changes and close the connection
conn.commit()
conn.close()