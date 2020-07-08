import argparse
import pandas as pd
import pyodbc


def main():
    """ Extract production data from PDM (OMNIA) """
    parser = argparse.ArgumentParser(
        description="Extract production data from PDM (OMNIA)"
    )
    parser.add_argument("field", help="Enter name of field")

    args = parser.parse_args()
    field = args.field
    sub_dir = field.lower()
    field = field.replace("_", " ")

    csv_file = (
        "//statoil.net/unix_st/private/ashska/development/webviz-4d/"
        + sub_dir
        + "/production_data/prod_data.csv"
    )
    print(field)

    server = "productionoptimizationprod.database.windows.net"
    driver = "ODBC Driver 17 for SQL Server"
    cnxn = pyodbc.connect(
        "DRIVER="
        + driver
        + ";SERVER="
        + server
        + ";PORT=1443;DATABASE=pdm;Authentication=ActiveDirectoryIntegrated"
    )

    print("Loading data from OMNIA ...")
    try:
        sql = "select * from PDM.DAILY_PROD_W where npd_field_name like'" + field + "'"

        df = pd.read_sql(sql, cnxn)

        df.to_csv(csv_file)
        print(df)
        print("Production data stored to file:", csv_file)
    except:
        print("ERROR: field", field, "not found in database")


if __name__ == "__main__":
    main()
