""" Create well layers for production and injection files """

from pathlib import Path
import os
import pickle
import math
import yaml
import pandas as pd
import common


OIL_PRODUCTION_FILE = "BORE_OIL_VOL.csv"
GAS_INJECTION_FILE = "BORE_GI_VOL.csv"
WATER_INJECTION_FILE = "BORE_WI_VOL.csv"


def get_well_polyline(
    wellbore, short_name, well_dataframe, well_type, fluid, md_start, selection, colors
):
    """ Extract polyline data - well trajectory, color and tooltip """
    color = "black"
    if colors:
        color = colors["default"]

    tooltip = str(short_name) + " : " + well_type

    status = False

    if fluid and not pd.isna(fluid):
        tooltip = tooltip + " (" + fluid + ")"

    if selection:
        if (
            ("reservoir" in selection or "completed" in selection)
            and not pd.isna(fluid)
            and md_start > 0
        ):
            positions = common.get_position_data(well_dataframe, md_start)
            status = True

        elif selection == "planned" and well_type == selection:
            if colors:
                color = colors[selection]

            positions = common.get_position_data(well_dataframe, md_start)
            status = True

        elif well_type == selection and not pd.isna(fluid) and md_start > 0:
            ind = fluid.find(",")

            if ind > 0:
                fluid = "mixed"

            if colors:
                color = colors[fluid + "_" + selection]

            positions = common.get_position_data(well_dataframe, md_start)
            status = True

        elif pd.isna(fluid):
            positions = common.get_position_data(well_dataframe, md_start)
            status = True

    else:
        positions = common.get_position_data(well_dataframe, md_start)
        status = True

    if status:
        return {
            "type": "polyline",
            "color": color,
            "positions": positions,
            "tooltip": tooltip,
        }



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
    wellbore = well_prod_info["wellbore.name"].values
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
            volume = well_prod_info[column].values[0]

            if math.isnan(volume):
                volume = None

        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()
            volume = selected_df.sum(axis=1).values

            try:
                volume = volume[0]
            except:
                pass

        if volume and volume > 0:
            well_type = "production"
            fluid = "oil"
            start_date = well_prod_info[OIL_PRODUCTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[OIL_PRODUCTION_FILE + "_Stop date"].values[0]
            info = fluid
            plot = True

    elif selection == "injection":
        column = GAS_INJECTION_FILE + "_" + interval

        try:
            volume_gas = well_prod_info[column].values[0]

            if math.isnan(volume_gas):
                volume_gas = None

        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()
            volume_gas = selected_df.sum(axis=1).values

            try:
                volume_gas = volume_gas[0]
            except:
                pass

        if volume_gas and volume_gas > 0:
            well_type = "injection"
            fluid = "gas"
            start_date = well_prod_info[GAS_INJECTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[GAS_INJECTION_FILE + "_Stop date"].values[0]
            info = fluid
            plot = True

        column = WATER_INJECTION_FILE + "_" + interval

        try:
            volume_water = well_prod_info[column].values[0]
        except:
            columns = well_prod_info.columns
            selected_columns = get_column_list(columns, column, interval)
            selected_df = well_prod_info[selected_columns].copy()

            volume_water = selected_df.sum(axis=1).values

            try:
                volume_water = volume_water[0]
            except:
                pass

        if volume_water and volume_water > 0:
            well_type = "injection"
            fluid = "water"
            start_date = well_prod_info[WATER_INJECTION_FILE + "_Start date"].values[0]
            stop_date = well_prod_info[WATER_INJECTION_FILE + "_Stop date"].values[0]
            info = fluid
            plot = True

    # print(wellbore, fluid, start_date, stop_date, info, plot)
    return well_type, fluid, start_date, stop_date, info, plot


def make_new_well_layer(
    interval_4d,
    wells_df,
    metadata_df,
    interval_df,
    prod_info_list,
    colors=None,
    selection=None,
    label="Drilled wells",
):
    """Make layeredmap wells layer"""
    data = []

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
            info = well_metadata["wellbore.list_name"].values
            start_date = None
            stop_date = None

        elif selection in ["reservoir_section", "planned"]:
            polyline_data = get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
                info,
                md_start,
                selection,
                colors,
            )
        elif not selection:
            polyline_data = get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
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
            polyline_data = get_well_polyline(
                wellbore,
                short_name,
                well_dataframe,
                well_type,
                info,
                md_start,
                selection,
                colors,
            )

        if polyline_data:
            data.append(polyline_data)

    return {"name": label, "checked": False, "base_layer": False, "data": data}


def main():
    # Main
    delimiter = "--"
    config_file = "/private/ashska/development/webviz-4d/fields/grane/grane_4d.yaml"
    config = common.read_config(config_file)
    # print(config)

    # Find FMU directory
    path = config["shared_settings"]["scratch_ensembles"]["sens_run"]
    # print(path)

    # Well and production data
    wellsuffix = ".w"
    wellfolder = config["pages"][0]["content"][0]["SurfaceViewer4D"]["wellfolder"]
    wellfolder = "/private/ashska/development/webviz-4d/data_preparation/Grane"

    prod_info_dir = "/private/ashska/development/webviz-4d/data_preparation/Grane"

    directory = os.path.dirname(path).replace("*", "0")
    number_of_maps = 3
    field_config_file = (
        "/private/ashska/development/webviz-4d/fields/grane/grane_mvp_config.yaml"
    )
    field_config = common.read_config(field_config_file)
    map_defaults = common.get_map_defaults(field_config, number_of_maps)
    metadata, dates = common.get_metadata(directory, map_defaults[0], delimiter)

    print("Extracting 4D intervals ...")
    intervals_4d = common.get_all_intervals(metadata)
    colors = common.get_well_colors(field_config)

    prod_info_files = [os.path.join(prod_info_dir, OIL_PRODUCTION_FILE)]
    prod_info_files.append(os.path.join(prod_info_dir, GAS_INJECTION_FILE))
    prod_info_files.append(os.path.join(prod_info_dir, WATER_INJECTION_FILE))

    prod_info_list = []
    for prod_info_file in prod_info_files:
        print("Reading production info from file " + str(prod_info_file))
        prod_info = pd.read_csv(prod_info_file)
        prod_info.name = os.path.basename(str(prod_info_file))
        print(prod_info.name)
        print(prod_info)

        prod_info_list.append(prod_info)

    drilled_well_df, drilled_well_info, interval_df = common.load_all_wells(
        wellfolder, wellsuffix
    )
    print(drilled_well_info)

    wellbores = drilled_well_info["wellbore.name"].unique()

    names = drilled_well_info[["wellbore.name", "wellbore.well_name"]]
    # print(names)

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

                values.append(value)

            drilled_well_info[
                header
            ] = values  # Add column with volume in 4D interval to dataframe

    print("Looping through all 4D intervals ...")
    for interval_4d in intervals_4d:
        print("4D interval:", interval_4d)
        well_layers = []
        well_layers.append(
            make_new_well_layer(
                interval_4d,
                drilled_well_df,
                drilled_well_info,
                interval_df,
                prod_info_list,
                colors,
                selection="production",
                label="Producers",
            )
        )
        well_layers_file = os.path.join(
            wellfolder, "production_well_layers_" + interval_4d + ".pkl"
        )
        dbfile = open(well_layers_file, "wb")
        pickle.dump(well_layers, dbfile)
        dbfile.close()
        print("Well layers stored to " + well_layers_file)

        well_layers = []
        well_layers.append(
            make_new_well_layer(
                interval_4d,
                drilled_well_df,
                drilled_well_info,
                interval_df,
                prod_info_list,
                colors,
                selection="injection",
                label="Injectors",
            )
        )
        well_layers_file = os.path.join(
            wellfolder, "injection_well_layers_" + interval_4d + ".pkl"
        )
        dbfile = open(well_layers_file, "wb")
        pickle.dump(well_layers, dbfile)
        dbfile.close()
        print("Well layers stored to " + well_layers_file)


if __name__ == "__main__":
    main()