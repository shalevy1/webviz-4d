""" Script that extracts trajectories, well logs and some
    metadata for alldrilled wellbores in the REP database """
import sys
import os
import glob
import argparse
import math
import datetime
import pandas as pd
from pandas import json_normalize
import yaml
import numpy as np
from reper import wrappers
from webviz_4d._datainput.well import load_well


def write_rms_wellbore(wellbore_name, wellbore_df, rkb, export_dir):
    """ Write the wellbore trajectory and log values to a file (RMS Aascii format) """
    MISSING_VALUE = -999

    wellbore_df.fillna(MISSING_VALUE, inplace=True)
    # print(well_df)

    name = wellbore_name.replace("/", "_").replace("NO ", "").replace(" ", "_")
    xutm = wellbore_df["EASTING"].values[0]
    yutm = wellbore_df["NORTHING"].values[0]

    if not os.path.exists(export_dir):
        os.mkdir(export_dir)

    outfile = os.path.join(export_dir, name + ".w")

    file_object = open(outfile, "w")
    file_object.write("1.0\n")
    file_object.write("LOCATION\n")
    file_object.write("%-15s %10.2f %12.2f %5.2f\n" % (name, xutm, yutm, rkb))

    n_columns = len(wellbore_df.columns)
    n_logs = n_columns - 3
    file_object.write(str(n_logs) + "\n")

    columns = wellbore_df.columns

    file_object.write(columns[0] + "   UNK    lin\n")  # MD column (first "log")

    for i in range(4, n_columns):
        file_object.write("%10s" % (columns[i] + "   UNK    lin\n"))

    for _index, row in wellbore_df.iterrows():

        file_object.write("%12.2f" % (row[2]))  # XUTM
        file_object.write("%12.2f" % (row[3]))  # YUTM
        file_object.write("%12.2f" % (row[1]))  # TVDMSL
        file_object.write("%12.2f" % (row[0]))  # MD

        for i in range(4, len(wellbore_df.columns)):
            file_object.write("%12.2f" % (row[i]))

        file_object.write("\n")

    file_object.close()

    # print("Well data exported to ", outfile)


def write_metadata(
    export_dir,
    wellbore_name,
    short_name,
    slot_name,
    field,
    wellbore_type,
    rkb,
    end_date,
    fluids,
    intervals,
):
    """ Write the extracted metadata for the wellbore to a yaml file """
    if not os.path.isdir(export_dir):
        os.mkdir(export_dir)

    rms_name = wellbore_name.replace("/", "_").replace("NO ", "").replace(" ", "_")
    outfile = os.path.join(export_dir, "." + rms_name + ".w.yaml")

    file_object = open(outfile, "w")
    file_object.write("- wellbore:\n")
    file_object.write("   name: " + wellbore_name + "\n")
    file_object.write("   rms_name: " + rms_name + "\n")
    file_object.write("   short_name: " + short_name + "\n")
    file_object.write("   slot_name: " + slot_name + "\n")
    file_object.write("   field: " + field + "\n")
    file_object.write("   type: " + wellbore_type + "\n")
    file_object.write("   rkb: " + str(rkb) + "\n")
    file_object.write("   drilling_end_date: " + end_date + "\n")
    file_object.write("   fluids: " + fluids + "\n")
    file_object.close()

    if intervals:
        with open(outfile, "a") as yamlfile:
            yaml.dump(intervals, yamlfile, default_flow_style=False)


# Main program
def main():
    """ Extracts trajectories, well logs and some metadata for all
    drilled wellbores in the REP database. Each wellbore is stored
    as an RMS ascii well (.w) in a folder named ../<field> and the
    metadata is also stored in the same folder. The metadata is stored
    as .<rms_name>.w.yaml and contains the following information (if available):
    - wellbore:
       name: NO 25/11-G-9
       rms_name: 25_11-G-9
       short_name: G-9
       slot_name: NO 25/11-G-9
       field: Grane
       type: production
       rkb: 69.9
       drilling_end_date: 2004-05-18T00:00:00
       fluids: oil
    - interval:
       equipment: Screen
       mdBottom: 3428.414
       mdTop: 2234.13
       wellbore: NO 25/11-G-9

    Parameters
    ----------
    field : str
        The name of the field  
    md_inc : int, optional
        Measured depth increment (default=50)

    Returns
    -------
    """

    parser = argparse.ArgumentParser(
        description="Extract well data from the REP database"
    )
    parser.add_argument("field", help="Enter name of field")
    parser.add_argument(
        "--md_inc",
        help="Enter wanted depth (MD) increment, 0=> no interpolation",
        type=int,
        default=0,
    )

    args = parser.parse_args()

    field = args.field
    md_inc = args.md_inc

    print(field, "Depth increment:", md_inc)

    EQUIPMENT_NAMES = ["Screen", "Perforations"]

    export_dir = field.lower().replace(" ", "_") + "/well_data/"

    if os.path.isdir(export_dir):
        print("Wells will be stored in", export_dir)
    else:
        export_dir = "./well_data/"

        if os.path.isdir(export_dir):
            print("Well data will be stored in", export_dir)
        else:
            print("ERROR: Well directory", export_dir, "not found")
            sys.exit()

    # Remove existing wells (not planned wells) and all metadata
    if os.path.isdir(export_dir):
        files = glob.glob(export_dir + "*.w")

        for file_object in files:
            os.remove(file_object)

        files = glob.glob(export_dir + ".*.yaml", recursive=True)

        for file_object in files:
            os.remove(file_object)

    wellbores = sorted(wrappers.Field(field).get_wellbore_names())

    i = 1
    for wellbore in wellbores:
        trajectory = wrappers.Wellbore(field, wellbore).get_wellbore_pos_log()
        df_trajectory = json_normalize(trajectory)

        rkb = wrappers.Wellbore(field, wellbore).get_depth_reference_elevation()
        df_trajectory["md"] = df_trajectory["md"].values + rkb

        end_date = wrappers.Wellbore(field, wellbore).get_wellbore_end_date()
        if end_date is None:
            end_date = ""

        wellbore_type = wrappers.Wellbore(field, wellbore).get_wellbore_type()
        if wellbore_type is None:
            wellbore_type = ""

        facility = wrappers.Wellbore(field, wellbore).get_wellbore_drilling_facility()
        if facility is None:
            facility = ""

        slot_name = wrappers.Wellbore(field, wellbore).get_well_identifier()
        if slot_name is None:
            slot_name = ""

        fluids = wrappers.Wellbore(field, wellbore).get_wellbore_fluids()
        if fluids is None:
            fluids = ""

        completion_list = wrappers.Wellbore(
            field, wellbore
        ).get_wellbore_completion_data()

        completions = []

        if completion_list:
            for item in completion_list:
                for equipment in EQUIPMENT_NAMES:
                    if equipment in item["symbolName"]:
                        completion = {
                            "wellbore": wellbore,
                            "equipment": item["symbolName"],
                            "mdTop": item["mdTop"] + rkb,
                            "mdBottom": item["mdBottom"] + rkb,
                        }
                        completion_dict = {"interval": completion}
                        completions.append(completion_dict)

        md_wellbore = df_trajectory["md"]
        tvd_wellbore = df_trajectory["tvd"]
        easting = df_trajectory["easting"]
        northing = df_trajectory["northing"]
        total_depth = md_wellbore.values[-1]

        # Resample well trajectory if wanted
        if md_inc > 0:
            start_md = md_wellbore[0]
            end_md = math.floor(total_depth)

            md_reg = np.arange(start_md, end_md, md_inc)

            tvd_reg = np.interp(md_reg, md_wellbore, tvd_wellbore)
            easting_reg = np.interp(md_reg, md_wellbore, easting)
            northing_reg = np.interp(md_reg, md_wellbore, northing)

            md_reg = np.append(md_reg, md_wellbore.values[-1])
            tvd_reg = np.append(tvd_reg, tvd_wellbore.values[-1])
            easting_reg = np.append(easting_reg, easting.values[-1])
            northing_reg = np.append(northing_reg, northing.values[-1])
        else:
            md_reg = md_wellbore
            tvd_reg = tvd_wellbore
            easting_reg = easting
            northing_reg = northing

        print(i, wellbore)

        well_df = pd.DataFrame()
        well_df["MD"] = md_reg
        well_df["TVDMSL"] = tvd_reg
        well_df["EASTING"] = easting_reg
        well_df["NORTHING"] = northing_reg

        # print(df)

        name = wellbore.replace("/", "_").replace("NO ", "").replace(" ", "_")

        write_rms_wellbore(wellbore, well_df, rkb, export_dir)
        rms_file = name + ".w"

        xtgeo_wellbore = load_well(os.path.join(export_dir, rms_file))
        wellbore_short_name = xtgeo_wellbore.shortwellname
        # print(xtgeo_well)

        write_metadata(
            export_dir,
            wellbore,
            wellbore_short_name,
            slot_name,
            field,
            wellbore_type,
            rkb,
            end_date,
            fluids,
            completions,
        )
        i = i + 1

    now = datetime.datetime.now()
    print("Update time", now.strftime("%Y-%m-%d %H:%M:%S"))

    outfile = os.path.join(export_dir, ".welldata_update.yaml")
    file_object = open(outfile, "w")
    file_object.write("- welldata:\n")
    file_object.write("   update_time: " + now.strftime("%Y-%m-%d %H:%M:%S") + "\n")
    file_object.close()

    print("Wellbores exported to", export_dir)
    print("Metadata exported to file", outfile)


if __name__ == "__main__":
    main()
