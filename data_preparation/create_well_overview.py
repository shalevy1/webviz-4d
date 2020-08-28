""" Create well layers for production and injection files """

import os
import argparse

import math
import pandas as pd
from webviz_4d._datainput import common
from webviz_4d._datainput import well
from webviz_4d._datainput._metadata import (
    get_metadata,
    get_all_intervals,
)
from webviz_4d.wells.well_data_frame import WellDataFrame


OIL_PRODUCTION_FILE = "BORE_OIL_VOL.csv"
GAS_INJECTION_FILE = "BORE_GI_VOL.csv"
WATER_INJECTION_FILE = "BORE_WI_VOL.csv"


def add_production_volumes(drilled_well_info, prod_info_list):
    wellbores = drilled_well_info["wellbore.name"].unique()
    names = drilled_well_info[["wellbore.name", "wellbore.well_name"]]

    print("Looping through all production information ...")
    for prod_info in prod_info_list:
        for column in prod_info.columns:
            values = []
            header = prod_info.name + "_" + column

            for wellbore in wellbores:
                well_name = names[names["wellbore.name"] == wellbore][
                    "wellbore.well_name"
                ].values[0]

                try:
                    value = prod_info[prod_info["Well name"] == well_name][
                        column
                    ].values[0]
                except:
                    value = None
                # print(wellbore,value)
                values.append(value)

            # Add column with volume in 4D interval to dataframe
            drilled_well_info[header] = values

    return drilled_well_info


def main():
    # Main
    description = "Create a well overview file (.csv) with relevant metadata"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config_file", help="Enter path to the WebViz-4D configuration file"
    )

    args = parser.parse_args()
    print(description)
    print(args)

    config_file = args.config_file
    config = common.read_config(config_file)

    # Well and production data
    well_suffix = common.get_config_item(config, "well_suffix")
    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")

    well_directory = common.get_config_item(config, "wellfolder")
    well_directory = common.get_full_path(well_directory)

    prod_info_dir = common.get_config_item(config, "production_data")
    prod_info_dir = common.get_full_path(prod_info_dir)
    update_metadata_file = os.path.join(prod_info_dir, ".production_update.yaml")
    
    prod_info_files = [os.path.join(prod_info_dir, OIL_PRODUCTION_FILE)]
    prod_info_files.append(os.path.join(prod_info_dir, GAS_INJECTION_FILE))
    prod_info_files.append(os.path.join(prod_info_dir, WATER_INJECTION_FILE))

    prod_info_list = []
    for prod_info_file in prod_info_files:
        print("Reading production info from file " + str(prod_info_file))
        prod_info = pd.read_csv(prod_info_file)
        prod_info.name = os.path.basename(str(prod_info_file))

        prod_info_list.append(prod_info)

    
    _drilled_well_df, drilled_well_info, interval_df = well.load_all_wells(
        well_directory, well_suffix)
    print(interval_df)
        
    drilled_well_info = add_production_volumes(drilled_well_info, prod_info_list)
    
    wellbore_overview = drilled_well_info[
    [
        "wellbore.name", 
        "wellbore.well_name",
        "BORE_OIL_VOL.csv_PDM well name",
        "wellbore.drilling_end_date",
        "wellbore.type",
        "wellbore.fluids",     
        "BORE_OIL_VOL.csv_Start date",
        "BORE_OIL_VOL.csv_Stop date",
        "BORE_GI_VOL.csv_Start date",
        "BORE_GI_VOL.csv_Stop date",
        "BORE_WI_VOL.csv_Start date",
        "BORE_WI_VOL.csv_Stop date",
    ]]    
    
    print(wellbore_overview)
    
    wellbores = wellbore_overview["wellbore.name"].unique()
    
    top_completion = []
    end_completion = []
    
    for wellbore in wellbores:
        try:
            top_md = interval_df[interval_df["interval.wellbore"] == wellbore][
                "interval.mdTop"
            ].values[0]
        except:
            top_md = None
            
        top_completion.append(top_md)
        
        try:
            base_md = interval_df[interval_df["interval.wellbore"] == wellbore][
                "interval.mdBottom"
            ].values[-1]
        except:
            base_md = None
        print(wellbore,top_md, base_md)
        end_completion.append(base_md)
        
    wellbore_overview.insert(6,"Top Screen", top_completion)
    wellbore_overview.insert(7,"Base Screen", end_completion)
    
    wellbore_overview.rename(columns=
        {
        "wellbore.name" : "Wellbore",
        "wellbore.well_name" : "Well",
        "wellbore.drilling_end_date" : "Drilling ended",
        "wellbore.type" : "Type",
        "wellbore.fluids" : "Fluid(s)",
        "BORE_OIL_VOL.csv_PDM well name" : "PDM Well",
        "BORE_OIL_VOL.csv_Start date" : "Start oil prod.",
        "BORE_OIL_VOL.csv_Stop date" : "End oil prod.",
        "BORE_GI_VOL.csv_Start date" : "Start gas inj.",
        "BORE_GI_VOL.csv_Stop date" : "End gas inj.", 
        "BORE_WI_VOL.csv_Start date" : "Start water inj.", 
        "BORE_WI_VOL.csv_Stop date" : "End water inj.",
        }, inplace=True
    )

    wellbore_overview.sort_values("Wellbore",inplace=True)
    print(wellbore_overview)
    
    csv_file = os.path.join(well_directory,"wellbore_overview.csv")
    wellbore_overview.to_csv(csv_file, index=False, float_format='%.1f') 
    print("Wellbore overview saved to:",csv_file)
    

if __name__ == "__main__":
    main()
