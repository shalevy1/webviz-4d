#!/usr/bin/env python3
import os
import glob
import yaml
import pandas as pd
from pandas.io.json import json_normalize
import xtgeo
import argparse
from webviz_4d._datainput import common


def load_surface(surface_path):
    return xtgeo.RegularSurface(surface_path)


def load_wellbore(well_path):
    return xtgeo.Well(well_path, mdlogname="MD")


def extract_metadata(directory):
    well_info = []
    interval_info = []

    print(directory)
    yaml_files = glob.glob(directory + "/.*.yaml", recursive=True)

    for yaml_file in yaml_files:
        print(yaml_file)
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


def compile_data(surface, well_directory, wellbore_info, well_suffix):
    rms_names = []
    well_names = []
    short_names = []
    depth_surfaces = []
    depth_picks = []

    print(wellbore_info)

    pick_name = surface.name

    if not wellbore_info.empty:
        for index, item in wellbore_info.iterrows():
            wellbore_name = item["wellbore.name"]
            print(wellbore_name)
            rms_name = (
                wellbore_name.replace("/", "_").replace("NO ", "").replace(" ", "_")
            )
            well_name = common.get_wellname(wellbore_info, wellbore_name)
            well_names.append(well_name)
            print(well_name)

            wellbore_file = os.path.join(well_directory, rms_name) + well_suffix
            wellbore = load_wellbore(wellbore_file)
            short_name = wellbore.shortwellname

            points = wellbore.get_surface_picks(surface)
            wellbore_pick_md = None

            if hasattr(points, "dataframe"):
                print(points.dataframe)
                wellbore_pick_md = points.dataframe["MD"].values[0]

            rms_names.append(rms_name)
            short_names.append(short_name)
            depth_surfaces.append(pick_name)
            depth_picks.append(wellbore_pick_md)

    else:  # Planned wells
        wellbore_names = []
        wellbore_types = []
        wellbore_fluids = []
        wellbore_files = glob.glob(str(well_directory) + "/*.w")
        print("wellbore_files", wellbore_files)

        for wellbore_file in wellbore_files:
            wellbore = load_wellbore(wellbore_file)
            wellbore_name = wellbore.name.split("/")[0]
            wellbore_names.append(wellbore_name)
            well_names.append(wellbore_name)
            short_names.append(wellbore_name)
            rms_names.append(wellbore_name)
            wellbore_types.append("planned")
            wellbore_fluids.append("")

            points = wellbore.get_surface_picks(surface)
            wellbore_pick_md = None

            if hasattr(points, "dataframe"):
                print(points.dataframe)
                wellbore_pick_md = points.dataframe["MD"].values[0]

            depth_surfaces.append(pick_name)
            depth_picks.append(wellbore_pick_md)

        wellbore_info["wellbore.name"] = well_names
        wellbore_info["wellbore.type"] = wellbore_types
        wellbore_info["wellbore.fluids"] = wellbore_fluids

    wellbore_info["wellbore.well_name"] = well_names
    wellbore_info["wellbore.rms_name"] = rms_names
    wellbore_info["wellbore.short_name"] = short_names
    wellbore_info["wellbore.rms_name"] = rms_names
    wellbore_info["wellbore.pick_name"] = depth_surfaces
    wellbore_info["wellbore.pick_md"] = depth_picks

    return wellbore_info


def main():
    parser = argparse.ArgumentParser(
        description="Compile metadata from all wells and extract top reservoir depths"
    )
    parser.add_argument("well_directory", help="Enter path to the main well folder")
    parser.add_argument("surface_file", help="Enter path to the top reservoir surface")
    parser.add_argument("--well_suffix", help="Enter wellfile suffix", default=".w")

    args = parser.parse_args()

    well_directory = args.well_directory
    surface_file = args.surface_file
    well_suffix = args.well_suffix

    print(well_directory, surface_file, well_suffix)

    WELLBORE_INFO_FILE = "wellbore_info.csv"
    INTERVALS_FILE = "intervals.csv"

    wellbore_info, intervals = extract_metadata(well_directory)
    surface = load_surface(surface_file)

    wellbore_info = compile_data(surface, well_directory, wellbore_info, well_suffix)

    wellbore_info.to_csv(os.path.join(well_directory, WELLBORE_INFO_FILE))
    intervals.to_csv(os.path.join(well_directory, INTERVALS_FILE))

    # print(intervals)
    pd.set_option("display.max_rows", None)
    print(wellbore_info)
    print("Metadata stored to " + os.path.join(well_directory, WELLBORE_INFO_FILE))
    print(
        "Completion intervals stored to " + os.path.join(well_directory, INTERVALS_FILE)
    )

    planned_wells_dir = [f.path for f in os.scandir(well_directory) if f.is_dir()]

    for folder in planned_wells_dir:
        wellbore_info = pd.DataFrame()
        wellbore_info = compile_data(surface, folder, wellbore_info, well_suffix)

        wellbore_info.to_csv(os.path.join(folder, WELLBORE_INFO_FILE))
        print(wellbore_info)
        print("Metadata stored to " + os.path.join(folder, WELLBORE_INFO_FILE))


if __name__ == "__main__":
    main()
