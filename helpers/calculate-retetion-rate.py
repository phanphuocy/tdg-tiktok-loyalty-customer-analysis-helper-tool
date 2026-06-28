import pandas as pd

df = pd.read_csv('pivot_monthly_customers_acquisition.csv')
df = df.sort_values('Order_Month').reset_index(drop=True)

new = df[df['Acquisition_Type']=='Newly Accquired'][['Order_Month','Num_Of_Customers']].set_index('Order_Month')
ret = df[df['Acquisition_Type']=='Return From Previous Month'][['Order_Month','Num_Of_Customers']].set_index('Order_Month')

months = sorted(df['Order_Month'].unique())
total_new = 0
print('Tháng | Khách mới | Pool cũ tích lũy (tháng trước) | Khách return | Retention rate')
for m in months:
    n = new.loc[m, 'Num_Of_Customers'] if m in new.index else 0
    r = ret.loc[m, 'Num_Of_Customers'] if m in ret.index else 0
    pool = total_new  # pool = tổng khách mới tích lũy đến cuối tháng TRƯỚC
    rate = r / pool * 100 if pool > 0 else None
    print(f'{m} | mới={n} | pool={pool} | return={r} | rate={rate:.1f}%' if rate is not None else f'{m} | mới={n} | pool={pool} | return={r} | rate=N/A')
    total_new += n

print()
print('Tổng khách mới (= tổng khách hàng shop):', total_new)
