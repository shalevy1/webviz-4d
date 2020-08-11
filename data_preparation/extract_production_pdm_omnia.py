import pyodbc
import pandas as pd
import argparse

def main():
    parser = argparse.ArgumentParser(description="Extract production data from PDM (OMNIA)")
    parser.add_argument("field", help="Enter name of field")
    parser.add_argument("path", help="Enter linux path to the production_data directory")

    args = parser.parse_args()  
    field = args.field 
    folder = args.path
    
    csv_file = folder + '/production_data/prod_data.csv'
    print("Field = ", field)
    print("Path = ", folder)
    print("Output file = ", csv_file)
    
    server = 'productionoptimizationprod.database.windows.net'
    driver = 'ODBC Driver 17 for SQL Server'
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1443;DATABASE=pdm;Authentication=ActiveDirectoryIntegrated')

    print("Loading data from OMNIA ...")
    #try:
    sql = "select * from PDM.DAILY_PROD_W where npd_field_name like'" + field + "'"

    df = pd.read_sql(sql, cnxn)

    if not df.empty:
        df.to_csv(csv_file)
        print("Production data stored to file:", csv_file)
        print(df)    
        
if __name__ == "__main__":
    main()        
