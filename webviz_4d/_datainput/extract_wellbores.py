#!/usr/bin/env python3
import os
import sys
import pandas as pd
from pandas.io.json import json_normalize
import json
import requests
import wrappers
from scipy import interpolate
import math
import numpy as np
import yaml
import xtgeo
import argparse


def load_wellbore(well_path):
    return xtgeo.Well(well_path, mdlogname="MD")


def dummy_log(md_reg):
    log = np.empty(len(md_reg))
    log[:] = np.nan

    return log


def replace_values(final_log_values, md_log, log_values, md_reg):
    md_start = md_reg[0]
    md_inc = md_reg[1] - md_reg[0]

    md_log_start = math.ceil(md_log[0])
    md_log_end = math.floor(md_log[-1])

    md_log_reg = np.arange(md_log_start, md_log_end, md_inc)
    md_array = np.array(md_log, dtype="float64")
    log_values_array = np.array(log_values, dtype="float64")

    log_reg = np.interp(md_log_reg, md_array, log_values_array)
    # print(log_reg)

    ind1 = 0
    l = -math.floor((md_start - md_log_start) / md_inc)
    ind2 = len(md_log_reg) - 1

    if ind2 + l > len(final_log_values):
        ind2 = len(final_log_values) - l

    for i in range(ind1, ind2):
        # print(i,l)
        if np.isnan(final_log_values[l]) and not np.isnan(log_reg[i]):
            final_log_values[l] = log_reg[i]

        l = l + 1

    return final_log_values


def write_rms_wellbore(wellbore_name, wellbore_df, rkb, export_dir):
    MISSING_VALUE = -999

    wellbore_df.fillna(MISSING_VALUE, inplace=True)
    # print(well_df)

    name = wellbore_name.replace("/", "_").replace("NO ", "").replace(" ", "_")
    xutm = wellbore_df["EASTING"].values[0]
    yutm = wellbore_df["NORTHING"].values[0]

    if not os.path.exists(export_dir):
        os.mkdir(export_dir)

    outfile = os.path.join(export_dir, name + ".w")

    f = open(outfile, "w")
    f.write("1.0\n")
    f.write("LOCATION\n")
    f.write("%-15s %10.2f %12.2f %5.2f\n" % (name, xutm, yutm, rkb))

    n_columns = len(wellbore_df.columns)
    n_logs = n_columns - 3
    f.write(str(n_logs) + "\n")

    columns = wellbore_df.columns

    f.write(columns[0] + "   UNK    lin\n")  # MD column (first "log")

    for i in range(4, n_columns):
        f.write("%10s" % (columns[i] + "   UNK    lin\n"))

    for index, row in wellbore_df.iterrows():

        f.write("%12.2f" % (row[2]))  # XUTM
        f.write("%12.2f" % (row[3]))  # YUTM
        f.write("%12.2f" % (row[1]))  # TVDMSL
        f.write("%12.2f" % (row[0]))  # MD

        for i in range(4, len(wellbore_df.columns)):
            f.write("%12.2f" % (row[i]))

        f.write("\n")

    f.close()

    print("Well data exported to ", outfile)
    print("")


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
    if not os.path.isdir(export_dir):
        os.mkdir(export_dir)

    rms_name = wellbore_name.replace("/", "_").replace("NO ", "").replace(" ", "_")
    outfile = os.path.join(export_dir, "." + rms_name + ".w.yaml")

    f = open(outfile, "w")
    f.write("- wellbore:\n")
    f.write("   name: " + wellbore_name + "\n")
    f.write("   rms_name: " + rms_name + "\n")
    f.write("   short_name: " + short_name + "\n")
    f.write("   slot_name: " + slot_name + "\n")
    f.write("   field: " + field + "\n")
    f.write("   type: " + wellbore_type + "\n")
    f.write("   rkb: " + str(rkb) + "\n")
    f.write("   drilling_end_date: " + end_date + "\n")
    f.write("   fluids: " + fluids + "\n")
    f.close()

    if intervals:
        with open(outfile, "a") as yamlfile:
            yaml.dump(intervals, yamlfile, default_flow_style=False)


# Main program
def main():
    parser = argparse.ArgumentParser(
        description="Extract well data from the REP database"
    )
    parser.add_argument("field", help="Enter name of field")
    parser.add_argument(
        "--md_inc", help="Enter wanted depth (MD) increment", type=int, default=50
    )
    parser.add_argument(
        "--log_curves",
        help="Enter list with wanted log curves",
        default=["GR", "RHOB", "VSH"],
    )
    parser.add_argument(
        "--search_txt", help="Limit the wells by specifying a search text", default=""
    )
    args = parser.parse_args()

    field = args.field
    md_inc = args.md_inc
    log_curves = args.log_curves
    search_txt = args.search_txt
    print(field, md_inc, log_curves, search_txt)

    EQUIPMENT_NAMES = ["Screen", "Perforations"]

    export_dir = "./" + field.replace(" ", "_")

    wellbores = sorted(wrappers.Field(field).get_wellbore_names())

    # print('Wellbore,RKB (m), TD (m)')

    for wellbore in wellbores:
        if search_txt in wellbore:
            trajectory = wrappers.Wellbore(field, wellbore).get_wellbore_pos_log()
            df_trajectory = json_normalize(trajectory)
            # print(df_trajectory)

            rkb = wrappers.Wellbore(field, wellbore).get_depth_reference_elevation()
            df_trajectory["md"] = df_trajectory["md"].values + rkb

            end_date = wrappers.Wellbore(field, wellbore).get_wellbore_end_date()
            if end_date is None:
                end_date = ""

            wellbore_type = wrappers.Wellbore(field, wellbore).get_wellbore_type()
            if wellbore_type is None:
                wellbore_type = ""

            facility = wrappers.Wellbore(
                field, wellbore
            ).get_wellbore_drilling_facility()
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
                    # print(item['mdTop'],item['mdBottom'],item['symbolName'],item['comment'])
                    # print('')
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

            # Resample well trajectory
            start_md = md_wellbore[0]
            end_md = math.floor(total_depth)

            md_reg = np.arange(start_md, end_md, md_inc)
            n = len(md_reg)

            tvd_reg = np.interp(md_reg, md_wellbore, tvd_wellbore)
            easting_reg = np.interp(md_reg, md_wellbore, easting)
            northing_reg = np.interp(md_reg, md_wellbore, northing)

            md_reg = np.append(md_reg, md_wellbore.values[-1])
            tvd_reg = np.append(tvd_reg, tvd_wellbore.values[-1])
            easting_reg = np.append(easting_reg, easting.values[-1])
            northing_reg = np.append(northing_reg, northing.values[-1])

            print(wellbore, ",", rkb, ",", total_depth, md_reg[-1])

            dummy = dummy_log(md_reg)

            df = pd.DataFrame()
            df["MD"] = md_reg
            df["TVDMSL"] = tvd_reg
            df["EASTING"] = easting_reg
            df["NORTHING"] = northing_reg

            for log_curve in log_curves:
                print(log_curve)
                curve_data = wrappers.Wellbore(field, wellbore).get_wellbore_log_data(
                    log_curve
                )
                # print(curve_data)

                if curve_data:
                    try:
                        index_unit = curve_data["indexUnit"]
                    except:
                        index_unit = "-"

                    try:
                        curve_unit = curve_data["unit"]
                    except:
                        curve_unit = "-"

                    # print('Index unit: ',index_unit)
                    # print('Curve unit: ',curve_unit)

                    data_points = wrappers.Wellbore(
                        field, wellbore
                    ).get_log_data_points(log_curve)
                    # print(data_points)

                    md_values = data_points["MD RKB"].values
                    curve_values = data_points["Value"].values

                    reg_log_values = dummy_log(md_reg)
                    reg_log_values = replace_values(
                        reg_log_values, md_values, curve_values, md_reg
                    )

                    df[log_curve] = reg_log_values
                else:
                    print("    - not found")

            # print(df)

            name = wellbore.replace("/", "_").replace("NO ", "").replace(" ", "_")
            # outfile = os.path.join(export_dir, name + ".csv")
            # df.to_csv(outfile,index=False)
            # print('Well saved to ' + outfile)

            write_rms_wellbore(wellbore, df, rkb, field)
            rms_file = field + "/" + name + ".w"
            xtgeo_wellbore = load_wellbore(rms_file)
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


if __name__ == "__main__":
    main()
