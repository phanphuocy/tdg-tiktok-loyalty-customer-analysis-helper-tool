CLEAR_OUT_GIFT_DATA = """
    --sql
    UPDATE excel_data
    SET Category = 'Quà tặng'
    WHERE SKU_Subtotal_Before_Discount = 0 AND Normal_Or_Pre_order IS NOT NULL;
"""

PRE_CREATE_TOTAL_ORDERS_TABLE = """
    --sql
    DROP TABLE IF EXISTS total_orders_data;
"""

CREATE_TOTAL_ORDERS_TABLE = """
    --sql
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

PRE_CREATE_TOTAL_CUSTOMERS_TABLE = """
    --sql
    DROP TABLE IF EXISTS total_customers_data;
"""

CREATE_TOTAL_CUSTOMERS_TABLE = """
    --sql
    CREATE TABLE total_customers_data AS
    WITH customer_aggregates AS (
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
            SUM(Basket_Total_IONCare_Packsize) AS Basket_Total_IONCare_Packsize,
            --- These attributes reserved to calculate the interests of customers into each brand products
            MIN(CASE WHEN Basket_Num_Kinka_Products > 0 THEN Order_Time END) AS First_Time_Purchase_Kinka,
            MIN(CASE WHEN Basket_Num_Revy_Products > 0 THEN Order_Time END) AS First_Time_Purchase_Revy,
            MIN(CASE WHEN Basket_Num_SiMee_Products > 0 THEN Order_Time END) AS First_Time_Purchase_SiMee
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
        END AS Loyalty_Tier,
        CASE
            WHEN First_Time_Purchase_Kinka IS NULL AND First_Time_Purchase_Revy IS NULL AND First_Time_Purchase_SiMee IS NULL THEN 'Not buy any of 3 brands'
            WHEN First_Time_Purchase_Kinka > 0 AND First_Time_Purchase_Revy IS NULL AND First_Time_Purchase_SiMee IS NULL THEN 'Only with Kinka'
            WHEN First_Time_Purchase_Kinka IS NULL AND First_Time_Purchase_Revy > 0 AND First_Time_Purchase_SiMee IS NULL THEN 'Only with Revy'
            WHEN First_Time_Purchase_Kinka IS NULL AND First_Time_Purchase_Revy IS NULL AND First_Time_Purchase_SiMee > 0 THEN 'Only with SiMee'
            WHEN 
                First_Time_Purchase_Kinka IS NOT NULL AND First_Time_Purchase_Revy IS NOT NULL
                AND MIN(First_Time_Purchase_Kinka, First_Time_Purchase_Revy, COALESCE(First_Time_Purchase_SiMee, '9999-12-31 23:59')) = First_Time_Purchase_Kinka
                AND First_Time_Purchase_Kinka = First_Time_Purchase_Revy
                THEN 'Start with Kinka and Revy'
            WHEN 
                First_Time_Purchase_Kinka IS NOT NULL AND First_Time_Purchase_SiMee IS NOT NULL
                AND MIN(First_Time_Purchase_Kinka, First_Time_Purchase_SiMee, COALESCE(First_Time_Purchase_Revy, '9999-12-31 23:59')) = First_Time_Purchase_Kinka
                AND First_Time_Purchase_Kinka = First_Time_Purchase_SiMee
                THEN 'Start with Kinka and SiMee'
            WHEN 
                First_Time_Purchase_Revy IS NOT NULL AND First_Time_Purchase_SiMee IS NOT NULL
                AND MIN(First_Time_Purchase_Revy, First_Time_Purchase_SiMee, COALESCE(First_Time_Purchase_Kinka, '9999-12-31 23:59')) = First_Time_Purchase_Revy
                AND First_Time_Purchase_Revy = First_Time_Purchase_SiMee
                THEN 'Start with Revy and SiMee'
            WHEN 
                First_Time_Purchase_Kinka IS NOT NULL AND First_Time_Purchase_Revy IS NOT NULL AND First_Time_Purchase_SiMee
                AND First_Time_Purchase_Revy = First_Time_Purchase_SiMee
                AND First_Time_Purchase_Revy = First_Time_Purchase_Kinka
                THEN 'Start with all 3 brands'
            WHEN 
                First_Time_Purchase_Kinka IS NOT NULL
                AND MIN(First_Time_Purchase_Kinka, COALESCE(First_Time_Purchase_Revy, '9999-12-31 23:59'), COALESCE(First_Time_Purchase_SiMee, '9999-12-31 23:59')) = First_Time_Purchase_Kinka
                THEN 'Start with Kinka'
            WHEN 
                First_Time_Purchase_Revy IS NOT NULL
                AND MIN(First_Time_Purchase_Revy, COALESCE(First_Time_Purchase_Kinka, '9999-12-31 23:59'), COALESCE(First_Time_Purchase_SiMee, '9999-12-31 23:59')) = First_Time_Purchase_Revy
                THEN 'Start with Revy'
            WHEN 
                First_Time_Purchase_SiMee IS NOT NULL
                AND MIN(First_Time_Purchase_SiMee, COALESCE(First_Time_Purchase_Revy, '9999-12-31 23:59'), COALESCE(First_Time_Purchase_Kinka, '9999-12-31 23:59')) = First_Time_Purchase_SiMee
                THEN 'Start with SiMee'
            ELSE 'Unsorted'
        END AS 'Funnel_Group'
    FROM customer_aggregates;
"""

PRE_UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_FUNNEL_COL = """
    --SQL
    ALTER TABLE total_customers_data
    ADD Switching_Status VARCHAR(255);
"""

UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_FUNNEL_COL = """
    --SQL
    UPDATE total_customers_data
    SET Switching_Status = CASE 
        -- 1. Switcher Conditions
        WHEN (Funnel_Group = 'Start with Kinka and Revy' AND First_Time_Purchase_SiMee IS NOT NULL)
        OR (Funnel_Group = 'Start with Kinka and SiMee' AND First_Time_Purchase_Revy IS NOT NULL)
        OR (Funnel_Group = 'Start with Revy and SiMee' AND First_Time_Purchase_Kinka IS NOT NULL)
        OR (Funnel_Group = 'Start with Kinka' AND (First_Time_Purchase_Revy IS NOT NULL OR First_Time_Purchase_SiMee IS NOT NULL))
        OR (Funnel_Group = 'Start with Revy' AND (First_Time_Purchase_Kinka IS NOT NULL OR First_Time_Purchase_SiMee IS NOT NULL))
        OR (Funnel_Group = 'Start with SiMee' AND (First_Time_Purchase_Kinka IS NOT NULL OR First_Time_Purchase_Revy IS NOT NULL))
            THEN 'Switcher'

        -- 2. Non-Switcher Conditions
        WHEN Funnel_Group IN ('Only with Kinka', 'Only with Revy', 'Only with SiMee')
        OR (Funnel_Group = 'Start with Kinka and Revy' AND First_Time_Purchase_SiMee IS NULL)
        OR (Funnel_Group = 'Start with Kinka and SiMee' AND First_Time_Purchase_Revy IS NULL)
        OR (Funnel_Group = 'Start with Revy and SiMee' AND First_Time_Purchase_Kinka IS NULL)
            THEN 'Non-switcher'

        -- 3. 1-to-1 Funnel Group Matches
        WHEN Funnel_Group = 'Start with all 3 brands' THEN 'Start with all 3 brands'
        WHEN Funnel_Group = 'Not buy any of 3 brands' THEN 'Not buy any of 3 brands'
        WHEN Funnel_Group = 'Unsorted'                THEN 'Unsorted'

        -- 4. Fallback (Prevents overwriting unmatched rows with NULL)
        ELSE Switching_Status 
    END;
    """

PRE_UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_SWITCHINGTIME_COL = """
    --sql
    ALTER TABLE total_customers_data
    ADD COLUMN Switching_Time VARCHAR(255);
"""

UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_SWITCHINGTIME_COL = """
    --sql
    UPDATE total_customers_data
    SET Switching_Time = CASE
        WHEN Funnel_Group = 'Start with Kinka' THEN MIN(COALESCE(First_Time_Purchase_Revy, '9999-12-31'), COALESCE(First_Time_Purchase_SiMee, '9999-12-31'))
        WHEN Funnel_Group = 'Start with Revy' THEN MIN(COALESCE(First_Time_Purchase_SiMee, '9999-12-31'), COALESCE(First_Time_Purchase_Kinka, '9999-12-31'))
        WHEN Funnel_Group = 'Start with SiMee' THEN MIN(COALESCE(First_Time_Purchase_Revy, '9999-12-31'), COALESCE(First_Time_Purchase_Kinka, '9999-12-31'))
        WHEN Funnel_Group = 'Start with Kinka and Revy' THEN First_Time_Purchase_SiMee
        WHEN Funnel_Group = 'Start with Kinka and SiMee' THEN First_Time_Purchase_Revy
        WHEN Funnel_Group = 'Start with Revy and SiMee' THEN First_Time_Purchase_Kinka
        ELSE 'No Switching Time'
    END
    WHERE Switching_Status = 'Switcher';
"""

PRE_UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_DAYTOSWITCH_COL = """
    --sql
    ALTER TABLE total_customers_data
    ADD COLUMN Days_To_Switch REAL;
"""

UPDATE_TOTAL_CUSTOMERS_TABLE_WITH_DAYTOSWITCH_COL = """
    --sql
    UPDATE total_customers_data
    SET Days_To_Switch = ROUND(JULIANDAY(Switching_Time) - JULIANDAY(First_Seen), 2)
    WHERE Switching_Status = 'Switcher';
"""

CREATE_LOYAL_SWITCHING_CUSTOMERS_FILTER_TABLE = """
    --sql
    CREATE TABLE filter_loyal_switching_customers AS
    SELECT Buyer_Username, Loyalty_Tier, Funnel_Group, First_Seen, Switching_Time, Days_To_Switch, Total_Customer_Spending, Num_of_Orders, Num_of_Canceled_Orders
    FROM total_customers_data
    WHERE Switching_Status = 'Switcher' AND Loyalty_Tier = 'Regular / Loyal'
    ORDER BY Total_Customer_Spending DESC;
"""

CREATE_FUNNELGROUP_PIVOT_TABLE = """
    -- How many days until customer to switch, by each funnel group?
    CREATE TABLE pivot_funnelgroup AS 
       SELECT Funnel_Group, Switching_Status, Loyalty_Tier, 
		COUNT(Buyer_Username) AS Num_Of_Customers, ROUND(AVG(Days_To_Switch), 2) AS Avg_Days_To_Switch, 
        ROUND(AVG(Total_Customer_Spending), 0) AS Avg_Customer_Value,
		ROUND(AVG(Average_Purchase_Value), 0) AS Avg_Purchase_Value,
		ROUND(AVG(Num_of_Orders), 1) AS Avg_Num_Of_Orders
    FROM total_customers_data
    WHERE Loyalty_Tier = 'Regular / Loyal'
    GROUP BY Funnel_Group
    ORDER BY COUNT(Buyer_Username) DESC;
"""


PRE_CREATE_PIVOT_LOYALTY_TABLE = """
    --sql
    DROP TABLE IF EXISTS total_customers_loyalty;
"""

CREATE_PIVOT_LOYALTY_TABLE = """
    --sql
    CREATE TABLE pivot_loyalty_tier AS
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
            ROUND((SUM(Num_of_Canceled_Orders) * 100.0) / SUM(Num_Of_Orders), 2) AS Cancellation_Rate,
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

PRE_CREATE_MONTHLY_CUSTOMERS_TABLE = """
    --sql
    DROP TABLE IF EXISTS monthly_customers_data;
"""

CREATE_MONTHLY_CUSTOMERS_TABLE = """
    --sql
    CREATE TABLE monthly_customers_data AS
    WITH customer_aggregates AS (
        SELECT 
            SUBSTR(Order_Time, 1, 7) AS Order_Month, -- Extracts YYYY-MM
            Buyer_Username,
            COUNT(Order_ID) AS Num_of_Orders,
            COUNT(CASE WHEN Order_Status = 'Đã hủy' THEN 1 END) AS Num_of_Canceled_Orders,
            MIN(MIN(Order_Time)) OVER(PARTITION BY Buyer_Username) AS Lifetime_First_Seen,
            MIN(Order_Time) AS First_Seen_In_Month,
            MAX(MAX(Order_Time)) OVER(PARTITION BY Buyer_Username) AS Lifetime_Last_Seen,
            MAX(Order_Time) AS Last_Seen_In_Month,
            -- (JULIANDAY(MAX(Order_Time)) - JULIANDAY(MIN(Order_Time))) AS Time_Between_Last_N_First_Orders,
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
        GROUP BY Order_Month, Buyer_Username
    )
    SELECT 
        *,
        -- Determine Lifetime period
        (JULIANDAY(Last_Seen_In_Month) - MIN(JULIANDAY(First_Seen_In_Month), JULIANDAY(Lifetime_First_Seen))) AS Retention_Time_Period,
        -- Determine Acquisitional type
        ROUND(Basket_Num_Kinka_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Kinka_Products,
        ROUND(Basket_Num_Revy_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Revy_Products,
        ROUND(Basket_Num_SiMee_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_SiMee_Products,
        ROUND(Basket_Num_Medical_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Medical_Products,
        ROUND(Basket_Num_IONCare_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_IONCare_Products,
        CASE 
            WHEN SUBSTR(Lifetime_First_Seen, 1, 7) < SUBSTR(First_Seen_In_Month, 1, 7) THEN 'Return From Previous Month'
            ELSE 'Newly Accquired'
        END AS Acquisition_Type
    FROM customer_aggregates;
"""

PRE_CREATE_PIVOT_MONTHLY_CUSTOMERS_ACQUISITION = """
    --sql
    DROP TABLE IF EXISTS pivot_monthly_customers_acquisition;
"""

CREATE_PIVOT_MONTHLY_CUSTOMERS_ACQUISITION = """
    --sql
    CREATE TABLE pivot_monthly_customers_acquisition AS
    WITH customer_loyalty_aggregates AS (
        SELECT 
            Order_Month,
            Acquisition_Type, 
            COUNT(Buyer_Username) AS Num_Of_Customers,
            -- Partition by Order_Month ensures percentages reset every month --
            ROUND((COUNT(Buyer_Username) * 100.0) / SUM(COUNT(Buyer_Username)) OVER(PARTITION BY Order_Month), 2) AS Pct_Num_Of_Customers,
            AVG(Retention_Time_Period) AS Retention_Time_Period,
            SUM(Total_Customer_Spending) AS Total_Customer_Spending,
            ROUND((SUM(Total_Customer_Spending) * 100.0) / SUM(SUM(Total_Customer_Spending)) OVER(PARTITION BY Order_Month), 2) AS Pct_Total_Customer_Spending,
            SUM(Num_of_Orders) AS Num_of_Orders,
            SUM(Total_Customer_Spending) / SUM(Num_of_Orders) AS Average_Purchase_Value,
            ROUND(AVG(Num_Of_Orders), 2) AS Buying_Frequency,
            ROUND(AVG(Num_of_Canceled_Orders), 2) AS Avg_Num_of_Canceled_Orders,
            ROUND((SUM(Num_of_Canceled_Orders) * 100.0) / SUM(Num_Of_Orders), 2) AS Cancellation_Rate,
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
            ROUND(SUM(Basket_Total_Kinka_Packsize) / NULLIF(SUM(Basket_Num_Kinka_Products), 0), 2) AS Basket_Avg_Kinka_Packsize,
            ROUND(SUM(Basket_Total_Revy_Packsize) / NULLIF(SUM(Basket_Num_Revy_Products), 0), 2) AS Basket_Avg_Revy_Packsize,
            ROUND(SUM(Basket_Total_SiMee_Packsize) / NULLIF(SUM(Basket_Num_SiMee_Products), 0), 2) AS Basket_Avg_SiMee_Packsize,
            ROUND(SUM(Basket_Total_Medical_Packsize) / NULLIF(SUM(Basket_Num_Medical_Products), 0), 2) AS Basket_Avg_Medical_Packsize,
            ROUND(SUM(Basket_Total_IONCare_Packsize) / NULLIF(SUM(Basket_Num_IONCare_Products), 0), 2) AS Basket_Avg_IONCare_Packsize
        FROM monthly_customers_data
        GROUP BY Order_Month, Acquisition_Type
        ORDER BY Order_Month DESC, Acquisition_Type
    ) SELECT 
        *,
        ROUND(Basket_Num_Kinka_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Kinka_Products,
        ROUND(Basket_Num_Revy_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Revy_Products,
        ROUND(Basket_Num_SiMee_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_SiMee_Products,
        ROUND(Basket_Num_Medical_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_Medical_Products,
        ROUND(Basket_Num_IONCare_Products * 100.0 / NULLIF(Basket_Total_Num_Products, 0), 2) AS Basket_Pct_IONCare_Products,
        Basket_Kinka_Spend_Amnt / NULLIF(Basket_Num_Kinka_Products, 0) AS Basket_Avg_Spend_On_Kinka,
        Basket_Revy_Spend_Amnt / NULLIF(Basket_Num_Revy_Products, 0) AS Basket_Avg_Spend_On_Revy,
        Basket_SiMee_Spend_Amnt / NULLIF(Basket_Num_SiMee_Products, 0) AS Basket_Avg_Spend_On_SiMee,
        Basket_Medical_Spend_Amnt / NULLIF(Basket_Num_Medical_Products, 0) AS Basket_Avg_Spend_On_Medical,
        Basket_IONCare_Spend_Amnt / NULLIF(Basket_Num_IONCare_Products, 0) AS Basket_Avg_Spend_On_IONCare
    FROM customer_loyalty_aggregates;
"""

CREATE_PIVOT_MONTHLY_PRODUCTS = """
    --sql
    -- Calculate pivot tables for average price and packsize of each SKU
    
    CREATE TABLE pivot_monthly_products AS
    SELECT t1.*, 
        COALESCE(t2.Nonaffiliated_Num_Of_Unit_Sold, 0) AS Nonaffiliated_Num_Of_Unit_Sold,
        t1.Affiliated_Num_Of_Unit_Sold - COALESCE(t2.Nonaffiliated_Num_Of_Unit_Sold, 0) AS Num_Of_Affiliate_Sample_Unit,
        COALESCE(t2.Nonaffiliated_Volume_Sold, 0) AS Nonaffiliated_Volume_Sold,
        COALESCE(t2.Nonaffiliated_Avg_Price, 0) AS Nonaffiliated_Avg_Price
    FROM (
        SELECT 
            substr(Created_Time, 7, 4) || '-' || substr(Created_Time, 4, 2) AS Month_Year,
            Category,
            Sub_category,
            Product_SKU_Name,
            Product_Variant,
            SUM(SKU_Subtotal_After_Discount) AS Total_Merchanise_Value,
            SUM(Quantity) AS Affiliated_Num_Of_Unit_Sold,
            ROUND(SUM(Pack_Size),2) AS Affiliated_Volume_Sold
        FROM excel_data
        WHERE Category != 'Quà tặng'
        GROUP BY Month_Year, Product_SKU_Name, Category, Product_Variant
        ORDER BY Category ASC
    ) t1 LEFT JOIN (
        SELECT 
            substr(Created_Time, 7, 4) || '-' || substr(Created_Time, 4, 2) AS Month_Year,
            Product_SKU_Name,
            Product_Variant,
            COALESCE(SUM(Quantity), 0) AS Nonaffiliated_Num_Of_Unit_Sold,
            ROUND(COALESCE(SUM(Pack_Size), 0), 2) AS Nonaffiliated_Volume_Sold,
            ROUND(AVG(SKU_Subtotal_After_Discount / Quantity), 0) AS Nonaffiliated_Avg_Price
        FROM excel_data
        WHERE Category != 'Quà tặng' AND Normal_Or_Pre_order IS NOT NULL
        GROUP BY Month_Year, Product_SKU_Name, Category, Product_Variant
        ORDER BY Category ASC
    ) t2 ON
        t1.Month_Year = t2.Month_Year
        AND t1.Product_SKU_Name = t2.Product_SKU_Name
        AND t1.Product_Variant = t2.Product_Variant;
"""