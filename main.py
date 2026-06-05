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

print(orders_workbook)
print(orders_sheet)

print("----------------------------------------------------------------")

# 2. Extract rows (Separating headers from data)
orders_rows = list(orders_sheet.iter_rows(values_only=True))
if not orders_rows:
    print("The Excel sheet is empty.")
    exit()

orders_headers = orders_rows[0]  # First row contains column names
orders_data_rows = orders_rows[2:]  # Remaining rows contain the actual data

print(type(orders_headers))

labelled_tuples, missing_ids = label_tuples_from_csv(
    csv_path=product_labels_filename,
    tuples=orders_data_rows,
    id_index=5,
)

labelled_headers = add_label_header_tuple(orders_headers)

print(labelled_headers)
print(len(labelled_headers))

print(labelled_tuples[0])
print(len(missing_ids))


# 3. Clean headers for SQL safety (replace spaces/special chars with underscores)
clean_headers = [
    str(h).strip().replace(" ", "_").replace("-", "_") if h else f"column_{i}"
    for i, h in enumerate(labelled_headers)
]

print("Clean headers")
print(clean_headers)
print(len(clean_headers))

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

# 7. Commit changes and close the connection
conn.commit()
conn.close()

print(f"Successfully converted {len(labelled_tuples)} rows into 'data.db'!")