#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import sys
import os
import datetime as dt
from datetime import datetime, timedelta
import calendar
import yaml
import glob
from pandas.io.json import json_normalize


def extract_wellbore_metadata(directory):
    well_info = []
    interval_info = []

    print(str(directory))
    yaml_files = glob.glob(str(directory) + "/**/.*.yaml", recursive=True)

    for yaml_file in yaml_files:
        with open(yaml_file, "r") as stream:
            data = yaml.safe_load(stream)
            # print('data',data)

            well_info.append(data[0])

            if len(data) > 1 and data[1]:
                for item in data[1:]:
                    interval_info.append(item)

    well_info_df = json_normalize(well_info)

    interval_df = json_normalize(interval_info)

    if not interval_df.empty:
        interval_df.sort_values(
            by=["interval.wellbore", "interval.mdTop"], inplace=True
        )

    return well_info_df, interval_df


def get_well_metadata(metadata_df, wellbore_name, item):
    value = None

    well_metadata = metadata_df[metadata_df["wellbore.name"] == wellbore_name]
    value = well_metadata[item].values[0]

    return value


def get_wellbores(metadata_df, well_name):
    wellbores = metadata_df[metadata_df["wellbore.well_name"] == well_name]
    wellbore_names = wellbores["wellbore.name"].values

    return sorted(wellbore_names)


def get_mother_wells(metadata_df, well_name):
    mother_wells = [well_name]

    wellbores = get_wellbores(metadata_df, well_name)
    # print('wellbores ',wellbores)

    mother_well = well_name
    for wellbore in wellbores:
        if not wellbore == mother_well and not wellbore[-2] == "T":
            if wellbore[-1] in "123456789":
                l = len(wellbore) - 1
            else:
                l = len(wellbore)
            name = wellbore[:l]

            if not name == mother_well:
                mother_well = name
                mother_wells.append(mother_well)

    list_set = set(mother_wells)
    unique_list = sorted(list(list_set))

    return unique_list


def get_branches(well_info_df, mother_well):
    branches = []
    i = mother_well.rfind(" ")

    possible_branches = well_info_df[
        well_info_df["wellbore.name"].str.contains(mother_well, regex=False)
    ]["wellbore.name"].values

    for branch in possible_branches:
        ib = branch.rfind(" ")
        l = len(branch)

        if (
            branch == mother_well or branch[: l - 1] == mother_well + " T"
        ):  # Sidetracked mother wells
            branches.append(branch)

        elif mother_well[:i] == branch[:ib] and not i == 2:  # Avoid ii == i
            # print(i,mother_well[:i],branch[:ib])
            branches.append(branch)

    return sorted(branches)


def get_wellname(metadata_df, wellbore):
    # print(wellbore)
    well_name = get_well_metadata(well_info_df, wellbore, "wellbore.well_name")
    # print('wellbore,well_name ',wellbore,well_name)
    mother_wells = get_mother_wells(metadata_df, well_name)
    # print(mother_wells)

    for mother_well in mother_wells:
        branches = get_branches(well_info_df, mother_well)
        # print(branches)

        for branch in branches:
            if branch == wellbore:
                return mother_well

    return None


def sort_wellbores(well_names):
    block_names = []
    slot_names = []
    slot_numbers = []
    branch_names = []

    for well_name in well_names:
        # print(well_name)
        slot_number = ""
        branch_name = ""

        index1 = well_name.find("-")
        index2 = well_name[index1 + 1 :].find("-") + index1 + 1

        if index2 > index1 + 1:
            slot_name = well_name[index1 + 1 : index2]
            ind = well_name[3:].find(" ")

            if ind > 0:
                slot_number = int(well_name[index2 + 1 : ind + 4])
            else:
                slot_number = int(well_name[index2 + 1 :])
        else:
            ind = well_name[3:].find(" ")
            if ind > 0:
                slot_name = well_name[index1 + 1 : ind + 4]
            else:
                slot_name = well_name[index1 + 1 :]

        if ind > 0:
            branch_name = well_name[ind + 3 :]

        block_name = well_name[:index1]

        block_names.append(block_name)
        slot_names.append(slot_name)
        slot_numbers.append(slot_number)
        branch_names.append(branch_name)

    df = pd.DataFrame(
        zip(well_names, block_names, slot_names, slot_numbers, branch_names),
        columns=["Well_name", "Block_name", "Slot_name", "Slot_number", "Branch_name"],
    )

    # pd.set_option('display.max_rows', None)
    df.sort_values(
        by=["Block_name", "Slot_name", "Slot_number", "Branch_name"], inplace=True
    )
    sorted_wellbores = df["Well_name"].values

    return sorted_wellbores


def get_dates(well_df, txt):
    start = "--------"
    stop = "--------"

    rows = well_df.loc[well_df[txt] > 0]

    if not rows.empty:
        start = rows["DATEPRD"].values[0][:10]
        stop = rows["DATEPRD"].values[-1][:10]

    return start, stop


def convert_date(date_orig):
    year = date_orig[-4:]
    month_int = list(calendar.month_abbr).index(date_orig[3:6])

    if month_int < 10:
        month = "0" + str(month_int)
    else:
        month = str(month_int)

    day = date_orig[:2]
    return year + "-" + month + "-" + day + " 00:00:00"


def get_date(dates_list, option):
    start_dates = []
    stop_dates = []

    for dates in dates_list:
        start_date = dates[0]

        if start_date != "--------":
            start_dates.append(start_date)

        stop_date = dates[1]

        if stop_date != "--------":
            stop_dates.append(stop_date)

    if option == "first":
        date = min(start_dates)
    elif option == "last":
        date = max(stop_dates)
        yesterday = (datetime.now() - timedelta(1)).strftime("%Y-%m-%d")
        if date == yesterday:
            date = "--------"

    return date


## Main program

wells_dir = "/private/ashska/development/Grane"
prod_data_file = (
    "/private/ashska/development/webviz-4d/fields/grane_pdm/grane_prod_data.csv"
)
prod_info_file = (
    "/private/ashska/development/webviz-4d/fields/grane/grane_prod_info.csv"
)

well_info_df, interval_df = extract_wellbore_metadata(wells_dir)
well_info_df.sort_values(by=["wellbore.name"], inplace=True)
print(well_info_df)

prod_data = pd.read_csv(prod_data_file)
prod_data.sort_values(by=["WELL_BORE_CODE", "DATEPRD"], inplace=True)

prod_data_wells = prod_data["WELL_BORE_CODE"].unique()
print("prod_data_wells", len(prod_data_wells))
print(prod_data_wells)

well_names = []
for index, row in well_info_df.iterrows():
    wellbore_name = row["wellbore.name"]
    well_name = get_well_metadata(well_info_df, wellbore_name, "wellbore.well_name")
    well_names.append(well_name)
    wellbore_names = get_wellbores(well_info_df, well_name)

list_set = set(well_names)
well_names = sorted(list(list_set))

i = 0
all_wellbores = []

for well_name in well_names:
    # print(well_name)

    mother_wells = get_mother_wells(well_info_df, well_name)
    for mother_well in mother_wells:
        # print("- ", mother_well)

        wellbores = get_branches(well_info_df, mother_well)
        for wellbore in wellbores:
            all_wellbores.append(wellbore)
            # print(" - ", wellbore, i)
            i = i + 1
    # print("")

print(len(all_wellbores))

wellbores = well_info_df["wellbore.name"].values

for wellbore in wellbores:
    indices = [i for i, x in enumerate(all_wellbores) if x == wellbore]

    if not indices:
        print("ERROR: " + wellbore + " not found in list")

sorted_wellbores = sort_wellbores(wellbores)
sorted_production_wells = sort_wellbores(prod_data_wells)

well_names = []
start_dates = []
stop_dates = []
oil_prod_volumes = []
gas_prod_volumes = []
water_prod_volumes = []
gas_inject_volumes = []
water_inject_volumes = []

for wellbore in sorted_production_wells:
    well_df = prod_data[prod_data["WELL_BORE_CODE"] == wellbore]
    oil_prod_dates = get_dates(well_df, "BORE_OIL_VOL")
    gas_prod_dates = get_dates(well_df, "BORE_GAS_VOL")
    water_prod_dates = get_dates(well_df, "BORE_WAT_VOL")
    gas_inject_dates = get_dates(well_df, "BORE_GI_VOL")
    water_inject_dates = get_dates(well_df, "BORE_WI_VOL")
    sum_df = well_df.sum(numeric_only=True)
    well_oil_volumes = sum_df["BORE_OIL_VOL"]
    well_gas_volumes = sum_df["BORE_GAS_VOL"]
    well_water_volumes = sum_df["BORE_WAT_VOL"]
    well_gas_inject_volumes = sum_df["BORE_GI_VOL"]
    well_water_inject_volumes = sum_df["BORE_WI_VOL"]

    if wellbore == "NO 25/11-G-22 BY 1":
        wellbore = "NO 25/11-G-22 BY1"
    well_name = get_wellname(well_info_df, wellbore)
    well_names.append(well_name)

    start_date = get_date(
        [
            oil_prod_dates,
            gas_prod_dates,
            water_prod_dates,
            gas_inject_dates,
            water_inject_dates,
        ],
        "first",
    )
    stop_date = get_date(
        [
            oil_prod_dates,
            gas_prod_dates,
            water_prod_dates,
            gas_inject_dates,
            water_inject_dates,
        ],
        "last",
    )
    start_dates.append(start_date)
    stop_dates.append(stop_date)

    oil_prod_volumes.append(well_oil_volumes)
    gas_prod_volumes.append(well_gas_volumes)
    water_prod_volumes.append(well_water_volumes)
    gas_inject_volumes.append(well_gas_inject_volumes)
    water_inject_volumes.append(well_water_inject_volumes)

    print(wellbore)
    # print(" Oil produduction ", oil_prod_dates, well_oil_volumes)
    # print(" Gas produduction ", gas_prod_dates, well_gas_volumes)
    # print(" Water produduction ", water_prod_dates, well_water_volumes)
    # print(" Gas injection ", gas_inject_dates, well_gas_inject_volumes)
    # print(" Water injection ", water_inject_dates, well_water_inject_volumes)

    indices = [i for i, x in enumerate(all_wellbores) if x == wellbore]

    if not indices:
        print("ERROR: " + wellbore + " not found in list")

prod_df = pd.DataFrame(
    zip(
        sorted_production_wells,
        well_names,
        start_dates,
        stop_dates,
        oil_prod_volumes,
        gas_prod_volumes,
        water_prod_volumes,
        gas_inject_volumes,
        water_inject_volumes,
    ),
    columns=[
        "Production well",
        "Well name",
        "Start date",
        "Stop date",
        "Oil volume",
        "Gas volume",
        "Water volume",
        "Injected gas",
        "Injected water",
    ],
)

print(prod_df)
print("Number of production wellbores: ", len(prod_df["Production well"].unique()))
print("Number of production wells: ", len(prod_df["Well name"].unique()))

prod_df.to_csv(prod_info_file,index=False)
