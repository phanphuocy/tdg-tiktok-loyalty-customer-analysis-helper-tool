import sqlite3
import pandas as pd

# Open a connection to the database
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

# Retrieve the names of all tables inside the database file
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

# Create an Excel writer object to manage multiple sheets
with pd.ExcelWriter("database.xlsx", engine="openpyxl") as writer:
    for table_name in tables:
        # Load each table into a pandas DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        
        # Write to Excel (Sheet name restricted to max 31 characters)
        df.to_excel(writer, sheet_name=table_name[:31], index=False)

# Clean up connection
conn.close()
print("All tables exported successfully!")