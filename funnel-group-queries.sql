
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
    CREATE TABLE switch_funnel_group AS 
        SELECT Funnel_Group, Switching_Status, Loyalty_Tier, 
            COUNT(Buyer_Username) AS Num_Of_Customers, ROUND(AVG(Days_To_Switch), 2) AS Avg_Days_To_Switch, 
            ROUND(AVG(Total_Customer_Spending), 0) AS Avg_Customer_Value,
            ROUND(AVG(Average_Purchase_Value), 0) AS Avg_Purchase_Value,
            ROUND(AVG(Num_Of_Orders), 2) AS Avg_Num_Of_Orders,
            ROUND(AVG(Num_Of_Canceled_Orders), 2) AS Avg_Num_of_Canceled_Orders,
            ROUND(AVG(Retention_Time_Period), 2) AS Avg_Retention_Time_Period,
            ROUND(SUM(Retention_Time_Period) / (SUM(Num_of_Orders) - SUM(Num_of_Canceled_Orders)), 2) AS Avg_Days_Between_Noncanceled_Purchases
        FROM total_customers_data
        WHERE Loyalty_Tier = 'Regular / Loyal'
        GROUP BY Funnel_Group
        ORDER BY COUNT(Buyer_Username) DESC;
"""