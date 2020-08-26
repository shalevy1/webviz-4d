#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from time import strptime
from datetime import date
import calendar
import argparse
import numpy as np
import pandas as pd
from webviz_4d._datainput import common, _metadata


def get_prod_dates(well_prod_data):
    """ Get first and last production dates """
    first_date = well_prod_data["DATEPRD"].values.min()
    last_date = well_prod_data["DATEPRD"].values.max()

    return first_date, last_date


def get_start_stop_dates(well_prod_data, prod_file_update, volume_code):
    """ Get start and stop production dates """
    well_prod_data.replace(" 00:00:00", "", regex=True, inplace=True)
    # print("prod_file_update", prod_file_update)

    start_date = well_prod_data.loc[well_prod_data[volume_code] > 0, "DATEPRD"].min()
    stop_date = well_prod_data.loc[well_prod_data[volume_code] > 0, "DATEPRD"].max()

    if not common.is_nan(start_date):
        stop_utc_time = strptime(stop_date, "%Y-%m-%d")
        epoch_time = calendar.timegm(stop_utc_time)
        # print(stop_date,prod_file_update - epoch_time)

        if prod_file_update - epoch_time < 87000 * 3:
            stop_date = np.nan

    return start_date, stop_date


def check_production_wells(sorted_production_wells, well_info, pdm_names_file):
    """ Check if a the name of a production well is included in the well list from REP """
    well_names = []

    # print(sorted_production_wells)

    for pdm_well in sorted_production_wells:
        well_name = common.get_wellname(well_info, pdm_well)

        if not well_name:
            print("WARNING: " + pdm_well + " not found in REP database")

            try:
                pdm_names = pd.read_csv(pdm_names_file)
                row = pdm_names[pdm_names["PDM well name"] == pdm_well]
                correct_name = row["Well name"][0]
                well_name = common.get_wellname(well_info, correct_name)
                print("   - Alias name found in " + pdm_names_file, pdm_well, well_name)
            except:
                print("ERROR: Alias should be defined in " + pdm_names_file)
                well_name = None

        well_names.append(well_name)

    return well_names


## Main program
def main():
    """ Compile production data """
    description = "Compile production data"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config_file", help="Enter path to the WebViz-4D configuration file"
    )

    args = parser.parse_args()

    print(description)
    print(args)

    WELLBORE_INFO_FILE = "wellbore_info.csv"

    today = date.today()
    today_str = str(today)

    config_file = args.config_file
    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]

    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")

    try:
        production_data = common.get_config_item(config, "production_data")
        production_data = common.get_full_path(production_data)
    except:
        production_data = None

    try:
        well_directory = common.get_config_item(config, "wellfolder")
        well_directory = common.get_full_path(well_directory)
    except:
        well_directory = None

    if production_data:
        production_file = os.path.join(production_data, "prod_data.csv")

        surface_metadata = _metadata.get_metadata(
            shared_settings, map_suffix, delimiter, metadata_file
        )
        # print(surface_metadata)

        prod_data = pd.read_csv(production_file)
        prod_file_update = os.path.getmtime(production_file)
        first_date, last_date = get_prod_dates(prod_data)

        # print(prod_data)
        prod_data_wells = prod_data["WELL_BORE_CODE"].unique()

        sorted_production_wells = common.sort_wellbores(prod_data_wells)

        well_info_file = os.path.join(well_directory, WELLBORE_INFO_FILE)
        well_info = pd.read_csv(well_info_file)

        pdm_names_file = os.path.join(well_directory, "wrong_pdm_well_names.csv")

        all_well_names = check_production_wells(
            sorted_production_wells, well_info, pdm_names_file
        )

        _all_4d, incremental_4d = _metadata.get_all_intervals(
            surface_metadata, "normal"
        )
        incremental_4d.sort()

        actual_intervals = []
        for interval in incremental_4d:
            date1, date2 = common.get_dates(interval)

            if date2 < today_str:
                actual_intervals.append(interval)

        volume_codes = [
            "BORE_OIL_VOL",
            "BORE_GAS_VOL",
            "BORE_WAT_VOL",
            "BORE_GI_VOL",
            "BORE_WI_VOL",
        ]

        for volume_code in volume_codes:
            pdm_names = []
            well_names = []
            start_dates = []
            stop_dates = []
            intervals = []
            volumes = np.zeros(
                (len(sorted_production_wells), len(actual_intervals) + 2)
            )

            print(volume_code)
            volume_df = pd.DataFrame()

            index = 0
            for pdm_well in sorted_production_wells:
                well_prod_data = prod_data[prod_data["WELL_BORE_CODE"] == pdm_well]
                well_prod_data = well_prod_data[
                    ["WELL_BORE_CODE", "DATEPRD", volume_code]
                ]

                start_date, stop_date = get_start_stop_dates(
                    well_prod_data, prod_file_update, volume_code
                )

                pdm_names.append(pdm_well)
                well_names.append(all_well_names[index])
                start_dates.append(start_date)
                stop_dates.append(stop_date)

                for i in range(0, len(actual_intervals)):
                    intervals.append(actual_intervals[i])
                    date1, date2 = common.get_dates(actual_intervals[i])

                    volumes[index, i] = well_prod_data.loc[
                        (well_prod_data["DATEPRD"] >= date1)
                        & (well_prod_data["DATEPRD"] < date2),
                        volume_code,
                    ].sum()
                
                # Add a last incremental interval - from last to now     
                last_interval = date2 + "-now"
                intervals.append(last_interval)
                volumes[index, i+1] = well_prod_data.loc[
                        (well_prod_data["DATEPRD"] >= date2),
                        volume_code,
                ].sum()
                
                # Add a column with accumulated total production
                date1_first, _date2_first = common.get_dates(actual_intervals[0])
                total = date1_first + "-now"
                intervals.append(total)
                volumes[index, i + 2] = well_prod_data.loc[
                    (well_prod_data["DATEPRD"] >= date1_first), volume_code,
                ].sum()

                index = index + 1
                

            volume_df["PDM well name"] = pdm_names
            volume_df["Well name"] = well_names
            volume_df["Start date"] = start_dates
            volume_df["Stop date"] = stop_dates

            pd.set_option("display.max_columns", None)
            pd.set_option("display.max_rows", None)

            for i in range(0, len(actual_intervals) + 2):
                volume_df[intervals[i]] = volumes[:, i]
                print(intervals[i])

            volume_df_actual = volume_df[volume_df[total] > 0]

            csv_file = os.path.join(production_data, volume_code + ".csv")
            volume_df_actual.to_csv(csv_file, index=False, float_format="%.0f")
            print("Data exported to file " + csv_file)

            print("Production start and last date:", first_date, last_date)

            outfile = os.path.join(well_directory, ".production_update.yaml")
            file_object = open(outfile, "w")
            file_object.write("- production:\n")
            file_object.write("   start_date: " + first_date[0:10] + "\n")
            file_object.write("   last_date: " + last_date[0:10] + "\n")
            file_object.close()

            print("Metadata exported to file " + outfile)
    else:
        print("No production information found in configuration file")


if __name__ == "__main__":
    main()
