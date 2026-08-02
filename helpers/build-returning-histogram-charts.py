import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect('data.db')
# conn = sqlite3.connect('data_th7.db')

query = """--sql
SELECT * FROM monthly_customers_data 
WHERE Acquisition_Type = 'Return From Previous Month'
"""

df = pd.read_sql_query(query, conn)

conn.close()

# 2. Convert relevant columns to datetime objects
df['Lifetime_First_Seen'] = pd.to_datetime(df['Lifetime_First_Seen'], errors='coerce')
df['Order_Month'] = pd.to_datetime(df['Order_Month'], errors='coerce')

# Drop any rows with missing essential dates to prevent plotting errors
df = df.dropna(subset=['Lifetime_First_Seen', 'Order_Month'])

# Sort values to ensure chronological order for the legend
df = df.sort_values('Order_Month')

# 3. Extract the year-month (e.g., "2025-09") for labels and grouping
df['Month_Label'] = df['Order_Month'].dt.strftime('%Y-%m')
unique_months = df['Month_Label'].unique()

# 4. Prepare a list of data subsets for each month
data_to_plot = [df[df['Month_Label'] == month]['Lifetime_First_Seen'] for month in unique_months]

# 5. Generate distinct colors dynamically using matplotlib's 'tab10' colormap
cmap = plt.get_cmap('tab10') 
colors = [cmap(i % 10) for i in range(len(unique_months))]

# 6. Create the stacked histogram chart
plt.figure(figsize=(14, 8))
plt.hist(
    data_to_plot, 
    bins=60,  # Increased bins from 15 to 30 to better show a longer timeline
    stacked=True, 
    color=colors,
    label=unique_months,
    edgecolor='black'
)

# 7. Add formatting, titles, and legend
plt.title('Histogram of Lifetime First Seen (Sept 2025 - May 2026)')
plt.xlabel('Lifetime First Seen (Time-Series)')
plt.ylabel('Number of Returning Customers')
plt.legend(title='Returning Cohort (Order Month)')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.grid(axis='x', linestyle='--', alpha=0.3)
plt.tight_layout()

# 8. Save the output to a .png file
plt.savefig('charts/returning-cohort/full_timeline_histogram.png')

# 2. Convert relevant columns to datetime objects
df['Lifetime_First_Seen'] = pd.to_datetime(df['Lifetime_First_Seen'], errors='coerce')
df['Order_Month'] = pd.to_datetime(df['Order_Month'], errors='coerce')

# Drop any rows with missing essential dates
df = df.dropna(subset=['Lifetime_First_Seen', 'Order_Month'])

# Sort values to ensure chronological order
df = df.sort_values('Order_Month')

# 3. Extract the year-month for loop grouping
df['Month_Label'] = df['Order_Month'].dt.strftime('%Y-%m')
unique_months = df['Month_Label'].unique()

# Generate distinct colors dynamically
cmap = plt.get_cmap('tab10') 

# 4. Loop through each unique month and generate a separate histogram
for i, month in enumerate(unique_months):
    
    # Filter data for just the specific month
    subset = df[df['Month_Label'] == month]['Lifetime_First_Seen']
    
    # Set up the plot window
    plt.figure(figsize=(10, 6))
    
    # Plot the histogram, keeping color consistent with the previous full-timeline chart
    plt.hist(subset, bins=15, color=cmap(i % 10), edgecolor='black')
    
    # Format labels and titles specifically for the current month
    plt.title(f'Histogram of Lifetime First Seen - Cohort: {month}')
    plt.xlabel('Lifetime First Seen (Time-Series)')
    plt.ylabel('Number of Returning Customers')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.grid(axis='x', linestyle='--', alpha=0.3)   
    plt.tight_layout()
    
    # Save the individual plot file
    filename = f'charts/returning-cohort/monthly_histogram_{month}.png'
    plt.savefig(filename)
    
    # CLOSE the figure so the next iteration starts fresh and doesn't overlap
    plt.close() 
    print(f"Generated {filename}")