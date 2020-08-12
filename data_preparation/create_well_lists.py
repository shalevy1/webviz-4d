""" Create well layers for production and injection files """

import os
import argparse
import pickle
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


def check_interval(interval):
    """ Flip start and end date if needed """
    dates = [interval[0:10], interval[11:21]]

    if dates[0] > dates[1]:
        selected_interval = dates[1] + "-" + dates[0]
    else:
        selected_interval = interval

    return selected_interval


def get_column_list(columns, pdm_column, interval):
    """ Return a list of incremental intervals given a larger interval """
    split_string = pdm_column.split(".")
    selected_csv = split_string[0]
    column_list = []
    start_index = None
    stop_index = None
    first_date = interval[0:10]
    last_date = interval[11:21]

    i = 0
    for column in columns:
        # print(column, selected_csv in column)

        if selected_csv in column:
            # print(column[-21:-11], column[-10:])
            if first_date == column[-21:-11]:
                start_index = i

            if last_date == column[-10:]:
                stop_index = i

        i = i + 1

    # print("start_index, stop_index ", start_index, stop_index)

    for j in range(start_index, stop_index + 1):
        column_list.append(columns[j])

    return column_list


def extract_production_info(well_prod_info, interval, selection):
    """ Return well and production information/status for a selected 
    interval for production/injection wells """
    well_type = None
    fluid = None
    start_date = None
    stop_date = None
    info = None
    plot = False

    if selection == "production":
        column = OIL_PRODUCTION_FILE + "_" + interval
        pd.set_option("display.max_columns", None)

        try:
            volume = well_prod_info[column].values[0] / 1000

            if math.isnan(volume):
                volume = None

        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()
            volume = selected_df.sum(axis=1).values

            volume = volume[0] / 1000

        if volume and volume > 0:
            well_type = "production"
            fluid = "oil"
            start_date = well_prod_info[OIL_PRODUCTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[OIL_PRODUCTION_FILE + "_Stop date"].values[0]
            
            if isinstance(stop_date,float):
                stop_date = "---"
            else:
                stop_date = str(stop_date[0:-3])
                    
            print(start_date, stop_date)
            info = (
                fluid
                + " {:.0f}".format(volume)
                + " [kSm3] Start: "
                + str(start_date[0:-3])
                + " Stop: "
                + stop_date
            )
            plot = True

    elif selection == "injection":
        column = GAS_INJECTION_FILE + "_" + interval

        try:
            volume_gas = well_prod_info[column].values[0] / 1000000

            if math.isnan(volume_gas):
                volume_gas = None

        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()
            volume_gas = selected_df.sum(axis=1).values

            volume_gas = volume_gas[0] / 1000000

        if volume_gas and volume_gas > 0:
            well_type = "injection"
            fluid = "gas"
            start_date = well_prod_info[GAS_INJECTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[GAS_INJECTION_FILE + "_Stop date"].values[0]
            info = fluid + " {:.0f}".format(volume_gas) + " [MSm3]"
            plot = True

        column = WATER_INJECTION_FILE + "_" + interval

        try:
            volume_water = well_prod_info[column].values[0] / 1000
        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()

            volume_water = selected_df.sum(axis=1).values

            volume_water = volume_water[0] / 1000

        if volume_water and volume_water > 0:
            well_type = "injection"
            fluid = "water"
            start_date = well_prod_info[WATER_INJECTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[WATER_INJECTION_FILE + "_Stop date"].values[0]
            info = fluid + " {:.0f}".format(volume_water) + " [kSm3]"
            plot = True

    if plot:
        wellbore = well_prod_info["wellbore.name"].values
        print(wellbore, info)

    return well_type, fluid, start_date, stop_date, info, plot


def make_new_well_layer(
    interval_4d,
    wells_df,
    metadata_df,
    prod_info_list,
    colors=None,
    selection=None,
    label="Drilled wells",
):
    """Make layeredmap wells layer"""
    data = []

    # print(interval_4d,wells_df,metadata_df,interval_df,prod_info_list,colors,selection,label)

    wellbores = wells_df["WELLBORE_NAME"].values
    list_set = set(wellbores)
    # convert the set to the list
    unique_wellbores = list(list_set)

    for wellbore in unique_wellbores:
        plot = True
        md_start = 0
        polyline_data = None

        well_dataframe = wells_df[wells_df["WELLBORE_NAME"] == wellbore]
        well_metadata = metadata_df[metadata_df["wellbore.rms_name"] == wellbore]

        wellbore_name = well_metadata["wellbore.name"].values[0]

        md_top_res = well_metadata["wellbore.pick_md"].values
        if selection and len(md_top_res) > 0:
            md_start = min(md_top_res)

        short_name = well_metadata["wellbore.short_name"].values
        if short_name:
            short_name = short_name[0]

        well_type = well_metadata["wellbore.type"].values
        if well_type:
            well_type = well_type[0]

        if well_type == "planned":
            # info = well_metadata["wellbore.list_name"].values
            fluid = ""
            info = ""
            start_date = None
            stop_date = None

        elif selection in ["reservoir_section", "planned"]:
            polyline_data = well.get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
                fluid,
                info,
                md_start,
                selection,
                colors,
            )
        elif not selection:
            polyline_data = well.get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
                fluid,
                info,
                md_start,
                selection,
                colors,
            )

        else:  # Production and injection layers
            plot = False
            interval = check_interval(interval_4d)

            (
                well_type,
                fluid,
                start_date,
                stop_date,
                info,
                plot,
            ) = extract_production_info(well_metadata, interval, selection)

        if plot:
            polyline_data = well.get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
                fluid,
                info,
                md_start,
                selection,
                colors,
            )

        if polyline_data:
            data.append(polyline_data)

    return {"name": label, "checked": False, "base_layer": False, "data": data}


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


def store_well_layer(well_layer, well_directory, label, interval_4d):
    well_layer_file = os.path.join(well_directory, label + interval_4d + ".pkl")

    dbfile = open(well_layer_file, "wb")
    pickle.dump(well_layer, dbfile)
    dbfile.close()
    print("Well layer stored to " + well_layer_file)


def main():
    # Main
    description = "Create well lists based on production data"
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

    update_dates = common.get_update_dates(well_directory)
    production_update = update_dates["production_last_date"]
    print("Production data update", production_update)

    try:
        settings_file = common.get_config_item(config, "settings")
        settings_file = common.get_full_path(settings_file)
        settings = common.read_config(settings_file)
        interval = common.get_config_item(config, "default_interval")
    except:
        settings_file = None
        settings = None
        interval = None

    shared_settings = config["shared_settings"]

    print("Extracting 4D intervals ...")
    metadata_file = common.get_config_item(config, "surface_metadata")
    metadata = get_metadata(shared_settings, delimiter, map_suffix, metadata_file)
    intervals_4d, incremental = get_all_intervals(metadata, "reverse")
    colors = common.get_well_colors(settings)

    print("intervals_4d")
    print(intervals_4d)

    prod_info_files = [os.path.join(prod_info_dir, OIL_PRODUCTION_FILE)]
    prod_info_files.append(os.path.join(prod_info_dir, GAS_INJECTION_FILE))
    prod_info_files.append(os.path.join(prod_info_dir, WATER_INJECTION_FILE))

    prod_info_list = []
    for prod_info_file in prod_info_files:
        print("Reading production info from file " + str(prod_info_file))
        prod_info = pd.read_csv(prod_info_file)
        prod_info.name = os.path.basename(str(prod_info_file))

        prod_info_list.append(prod_info)

    drilled_well_df, drilled_well_info, interval_df = well.load_all_wells(
        well_directory, well_suffix
    )

    drilled_well_info = add_production_volumes(drilled_well_info, prod_info_list)
    # well_info = WellDataFrame(drilled_well_info)

    wellbores = drilled_well_info["wellbore.name"].unique()

    # print("well_info.data_frame")
    # print(well_info.data_frame)

    print("Last production update", production_update)
    print("Looping through all 4D intervals ...")
    for interval_4d in intervals_4d:
        print("4D interval:", interval_4d)

        if interval_4d[0:10] <= production_update:
            well_layer = make_new_well_layer(
                interval_4d,
                drilled_well_df,
                drilled_well_info,
                prod_info_list,
                colors,
                selection="production",
                label="Producers",
            )
            label = "production_well_layer_"
            store_well_layer(well_layer, well_directory, label, interval_4d)

            well_layer = make_new_well_layer(
                interval_4d,
                drilled_well_df,
                drilled_well_info,
                prod_info_list,
                colors,
                selection="injection",
                label="Injectors",
            )

            label = "injection_well_layer_"
            store_well_layer(well_layer, well_directory, label, interval_4d)
        else:
            print("  - no production data for this time interval")


if __name__ == "__main__":
    main()
