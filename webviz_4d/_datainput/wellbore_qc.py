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
    wellbores = metadata_df[metadata_df["wellbore.slot_name"] == well_name]
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
    well_name = get_well_metadata(well_info_df, wellbore, "wellbore.slot_name")
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
smda_wells_file = (
    "/private/ashska/development/webviz-4d/fields/grane_pdm/grane_smda_wells.csv"
)
rep_wells_dir = "/private/ashska/development/reper/examples/Grane"
prod_info_file = (
    "/private/ashska/development/webviz-4d/fields/grane/grane_prod_info.csv"
)
qc_file = "/private/ashska/development/webviz-4d/fields/grane/grane_qc.csv"
combined_meta_data_file = "/private/ashska/development/webviz-4d/fields/grane/grane_metadata.csv"

smda_df = pd.read_csv(smda_wells_file, sep=";")
smda = smda_df[
    [
        "unique_wellbore_identifier",
        "wellbore_purpose",
        "wellbore_status",
        "wellbore_content",
        "drill_end_date",
    ]
]

smda.rename(columns={"unique_wellbore_identifier" : "wellbore.name"},inplace=True)
print(smda)

well_info_df, interval_df = extract_wellbore_metadata(rep_wells_dir)
print(well_info_df)

combined_df = pd.merge(smda,
                 well_info_df,
                 on="wellbore.name",
                 how="left")
                                
production_df = pd.read_csv(prod_info_file)
production_df.rename(columns={"Production well" : "wellbore.name"},inplace=True)
print(production_df)

merged_df = pd.merge(combined_df,
                 production_df,
                 on="wellbore.name",
                 how="left")
merged_df.to_csv(qc_file)    

for index,row in merged_df.iterrows():
    well_name = row["Well name"]
    wellbore_type = row["wellbore.type"]
   
    if pd.isna(well_name) and (wellbore_type == "production" or wellbore_type == "injection"):
        #print(row)
        wellbore_name = row["wellbore.name"]
        well_name = get_wellname(well_info_df, wellbore_name)
        start_date = production_df[production_df["Well name"] == well_name]["Start date"].values
        stop_date = production_df[production_df["Well name"] == well_name]["Stop date"].values
        
        if start_date.any():
            start_date = start_date[0]
        else:
            start_date = ""
        
        if stop_date.any():
            stop_date = stop_date[0]
        else:
            stop_date = ""
                  
        merged_df.at[index,"Well name"] = well_name
        merged_df.at[index,"Start date"] = start_date
        merged_df.at[index,"Stop date"] = stop_date
        
        #print(wellbore_name,well_name,start_date)
                
print(merged_df)
merged_df.to_csv(combined_meta_data_file) 
                 
                 


    
