import pyodbc
import pandas as pd

server = "productionoptimizationprod.database.windows.net"
driver = "ODBC Driver 17 for SQL Server"
cnxn = pyodbc.connect(
    "DRIVER="
    + driver
    + ";SERVER="
    + server
    + ";PORT=1443;DATABASE=pdm;Authentication=ActiveDirectoryIntegrated"
)

sql = "select * from PDM.DAILY_PROD_W where npd_field_name like 'Grane'"
df = pd.read_sql(sql, cnxn)

df.to_csv("grane_prod_data.csv")
print(df)
