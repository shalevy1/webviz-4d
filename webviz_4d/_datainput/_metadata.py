import os
import glob
import sys
import pandas as pd
import numpy as np
from pandas import json_normalize
import yaml
import re
import calendar
from pathlib import Path
from webviz_4d._datainput import common


def create_map_settings(
    attribute, name, map_type, ensemble, realization, default_interval
):

    map_dict = {
        "attribute": attribute,
        "name": name,
        "map_type": map_type,
        "ensemble": ensemble,
        "realization": realization,
        "interval": default_interval,
    }

    return map_dict


def create_map_defaults(metadata_df, default_interval, observations, simulations):
    observed_attributes = get_attributes(metadata_df, observations)
    # print("observed_attributes", observed_attributes)
    observed_names = get_names(metadata_df, observations)

    simulated_attributes = get_attributes(metadata_df, simulations)
    # print("simulated_attributes", simulated_attributes)
    simulated_names = get_names(metadata_df, simulations)
    realizations = get_realizations(metadata_df, simulations)
    ensembles = get_ensembles(metadata_df, simulations)

    ensemble = ensembles[0]
    realization = realizations[0]

    map_defaults = []

    if observed_attributes:
        rows = metadata_df.loc[
            (metadata_df["data.time.t2"] == default_interval[0:10])
            & (metadata_df["data.time.t1"] == default_interval[11:])
        ]
        observed_attribute = observed_attributes[0]
        observed_name = rows["data.name"].values[0]

        map_default = create_map_settings(
            observed_attribute,
            observed_name,
            observations,
            ensemble,
            realization,
            default_interval,
        )
        map_defaults.append(map_default)

        if simulated_attributes:
            rows = metadata_df.loc[
                (metadata_df["data.time.t2"] == default_interval[0:10])
                & (metadata_df["data.time.t1"] == default_interval[11:])
            ]

            simulated_attribute = rows["data.content"].values[0]
            simulated_name = rows["data.name"].values[0]

            map_default = create_map_settings(
                simulated_attribute,
                simulated_name,
                simulations,
                ensemble,
                realization,
                default_interval,
            )
            map_defaults.append(map_default)
            map_defaults.append(map_default)

    elif simulated_attributes:
        rows = metadata_df.loc[
            (metadata_df["data.time.t2"] == default_interval[0:10])
            & (metadata_df["data.time.t1"] == default_interval[11:])
        ]

        simulated_attribute = rows["data.content"].values[0]
        simulated_name = rows["data.name"].values[0]

        map_default = create_map_settings(
            simulated_attribute,
            simulated_name,
            simulations,
            ensemble,
            realization,
            default_interval,
        )
        map_defaults.append(map_default)
        map_defaults.append(map_default)
        map_defaults.append(map_default)

    return map_defaults


def check_yaml_file(surfacepath):
    mapfile_name = str(surfacepath)

    yaml_file = (
        os.path.dirname(mapfile_name) + "/." + os.path.basename(mapfile_name) + ".yaml"
    )
    status = os.path.isfile(yaml_file)

    return status


def extract_metadata(shared_settings, metadata_file):
    fmu_directory = shared_settings["fmu_directory"]
    meta_data = []
    metadata_df = None

    map_types = ["observed", "results"]
    mapping_dict = {"observed": "observed", "results": "simulated"}

    for map_type in map_types:
        if mapping_dict[map_type] + "_maps" in shared_settings:
            map_settings = shared_settings[mapping_dict[map_type] + "_maps"]
            realization_names = map_settings["realization_names"]
            ensemble_names = map_settings["ensemble_names"]
            map_directories = map_settings["map_directories"]

            for realization_name in realization_names:
                for ensemble_name in ensemble_names:
                    for map_directory in map_directories:
                        yaml_files = glob.glob(
                            os.path.join(
                                fmu_directory,
                                realization_name,
                                ensemble_name,
                                map_directory + "/.*.yaml",
                            )
                        )

                        if yaml_files is not None:
                            for yaml_file in yaml_files:
                                with open(yaml_file, "r") as stream:
                                    data_stream = yaml.safe_load(stream)
                                    data = data_stream["data"]

                                    if "time" in data:
                                        time = data["time"]

                                        if "t2" in time:
                                            data_stream["map_type"] = map_type
                                            real_number = data_stream["fmu_id"][
                                                "realization"
                                            ]
                                            data_stream["fmu_id"][
                                                "realization"
                                            ] = "realization-" + str(real_number)

                                            sub_domain = data_stream["data"][
                                                "subdomain"
                                            ]
                                            if sub_domain == "rf":
                                                data_stream["data"]["content"] = (
                                                    data_stream["data"]["content"]
                                                    + "_"
                                                    + sub_domain
                                                )

                                            data_stream["filename"] = yaml_file
                                            meta_data.append(data_stream)
                        else:
                            maps_dir = None
                            print("WARNING: no maps found for", map_type)

    if meta_data:
        metadata_df = json_normalize(meta_data)

    # print(metadata_df)
    return metadata_df


def get_all_intervals(df, mode):
    all_intervals_list = []
    incremental_list = []

    interval_df = df[["data.time.t1", "data.time.t2"]]
    new_df = interval_df.drop_duplicates()

    if mode == "reverse":
        all_intervals = new_df.sort_values(
            by=["data.time.t2", "data.time.t1"], ascending=[True, False]
        )
    else:
        all_intervals = new_df.sort_values(
            by=["data.time.t1", "data.time.t2"], ascending=[True, False]
        )

    for index, row in all_intervals.iterrows():
        if mode == "reverse":
            all_intervals_list.append(row["data.time.t2"] + "-" + row["data.time.t1"])
        else:
            all_intervals_list.append(row["data.time.t1"] + "-" + row["data.time.t2"])

    t1_list = df["data.time.t1"].drop_duplicates().sort_values().tolist()
    t2_list = df["data.time.t2"].drop_duplicates().sort_values().tolist()
    all_list = t1_list + t2_list

    unique_list = list(set(all_list))
    unique_list.sort()

    incremental_list = []

    for i in range(1, len(unique_list)):
        if mode == "reverse":
            interval = unique_list[i] + "-" + unique_list[i - 1]
        else:
            interval = unique_list[i - 1] + "-" + unique_list[i]

        if interval in all_intervals_list:
            incremental_list.append(interval)

    return all_intervals_list, incremental_list


def get_difference_mode(surfacepath, delimiter):
    (
        directory,
        realization,
        ensemble,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(surfacepath, delimiter)

    if dates[0] > dates[1]:
        difference_mode = "reverse"
    else:
        difference_mode = "normal"

    return difference_mode


def decode_filename(file_path, delimiter):
    surfacepath = str(file_path)
    ind = []
    number = None
    folder = None
    map_type = None
    ensemble = None
    realization = None
    name = None
    attribute = None
    dates = [None, None]

    folder = os.path.dirname(surfacepath)

    if "observations" in str(surfacepath):
        map_type = "observations"

    if "results" in str(surfacepath):
        map_type = "results"

        number = find_number(surfacepath, "realization")

        if number:
            realization = "realization-" + number
            number = None

            if realization:
                number = find_number(surfacepath, "iter")

                if number:
                    ensemble = "iter-" + number

    if "pred" in surfacepath:
        ensemble = "pred"

    for m in re.finditer(delimiter, str(surfacepath)):
        ind.append(m.start())

    k = str(surfacepath).rfind("/")

    if len(ind) > 1:
        name = str(surfacepath)[k + 1 : ind[0]]
        attribute = str(surfacepath)[ind[0] + 2 : ind[1]]
        # print(surfacepath,name,attribute)

        if len(ind) == 2 and len(str(surfacepath)) > ind[1] + 19:
            date1 = str(surfacepath)[ind[1] + 2 : ind[1] + 10]
            date2 = str(surfacepath)[ind[1] + 11 : ind[1] + 19]

            if common.check_number(date1) and common.check_number(date2):
                dates[0] = convert_date(date1)
                dates[1] = convert_date(date2)
            else:
                dates = [None, None]

    # print('decode ', surfacepath,realization, ensemble, map_type, name, attribute, dates)
    return folder, realization, ensemble, map_type, name, attribute, dates


def get_metadata(shared_settings, extension, delimiter, filename):
    fmu_directory = shared_settings["fmu_directory"]

    metadata_file = os.path.join(fmu_directory, filename)

    if os.path.isfile(metadata_file):
        print("Reading surface metadata file", metadata_file)
        metadata = pd.read_csv(metadata_file)
    else:
        print("Checking if individual metadata files exist ...")

        metadata = extract_metadata(shared_settings, metadata_file)

        if metadata is None:
            print("No individual metadata files found")

            print("Creating surface metadata ...")
            realizations = []
            ensembles = []
            map_types = []
            names = []
            attributes = []
            times1 = []
            times2 = []
            filenames = []
            headers = [
                "fmu_id.realization",
                "fmu_id.ensemble",
                "map_type",
                "data.name",
                "data.content",
                "data.time.t1",
                "data.time.t2",
                "filename",
            ]

            surface_types = ["observations", "results"]
            mapping_dict = {"observations": "observed", "results": "simulated"}

            for surface_type in surface_types:
                map_dir = mapping_dict[surface_type] + "_maps"

                if map_dir in shared_settings:
                    map_settings = shared_settings[map_dir]
                    realization_names = map_settings["realization_names"]
                    ensemble_names = map_settings["ensemble_names"]
                    map_directories = map_settings["map_directories"]

                    for realization_name in realization_names:
                        for ensemble_name in ensemble_names:
                            for map_directory in map_directories:
                                map_files = glob.glob(
                                    os.path.join(
                                        fmu_directory,
                                        realization_name,
                                        ensemble_name,
                                        map_directory + "/*" + extension,
                                    )
                                )
                                for map_file in map_files:
                                    (
                                        folder,
                                        realization,
                                        ensemble,
                                        map_type,
                                        name,
                                        attribute,
                                        dates,
                                    ) = decode_filename(map_file, delimiter)

                                    if dates[0] and dates[1]:
                                        realizations.append(realization)
                                        ensembles.append(ensemble)
                                        map_types.append(map_type)
                                        names.append(name)
                                        attributes.append(attribute)
                                        times1.append(dates[1])
                                        times2.append(dates[0])
                                        filenames.append(map_file)
                else:
                    print("No maps found for", surface_type)

            zipped_list = list(
                zip(
                    realizations,
                    ensembles,
                    map_types,
                    names,
                    attributes,
                    times1,
                    times2,
                    filenames,
                )
            )

            metadata = pd.DataFrame(zipped_list, columns=headers)
            metadata.fillna(value=np.nan, inplace=True)

    if not os.path.isfile(metadata_file) and not metadata.empty:
        metadata.to_csv(metadata_file, index=False)
        print("Surface metadata saved to:", metadata_file)

    return metadata


def unique_values(list_values):
    clean_list = [value for value in list_values if str(value) != "nan"]
    list_set = set(clean_list)
    unique_list = list(list_set)

    return sorted(unique_list)


def get_col_values(df, col_name):
    return unique_values(df[col_name].values)


def compose_filename(
    shared_settings, real, ensemble, map_type, name, attribute, interval, delimiter
):
    surfacepath = None

    fmu_directory = shared_settings["fmu_directory"]

    if type(real) == int:
        realization = "realization-" + str(real)
    else:
        realization = real

    # if '-' in dates[0]:
    #    dates = convert_date(dates[0]) + "_" + convert_date(dates[1])

    interval_string = interval.replace("-", "")
    datestring = interval_string[:8] + "_" + interval_string[8:]
    print(
        "compose_filename",
        fmu_directory,
        realization,
        ensemble,
        map_type,
        name,
        attribute,
        interval,
        datestring,
    )

    filename = name + delimiter + attribute + delimiter + datestring + ".gri"
    filename = filename.lower()
    # print(filename)

    if map_type == "results":
        map_directories = shared_settings["simulated_maps"]["map_directories"]

    elif map_type == "observations":
        map_directories = shared_settings["observed_maps"]["map_directories"]

    for map_directory in map_directories:
        surfacepath = os.path.join(
            fmu_directory, real, ensemble, map_directory, filename
        )
        print("surfacepath ", surfacepath)

        if os.path.exists(surfacepath):
            return surfacepath

    return surfacepath


def get_selected_metadata(df, surfacepath):
    metadata = None

    try:
        metadata = df[df["filename"] == surfacepath]
    except:
        yaml_file = None
        metadata = None

    return metadata


def get_surfacepath(metadata):
    surfacepath = None

    return metadata


def get_slider_tags(dates):
    # print(dates)
    tags = {}
    i = 1
    for date in dates:
        year = date[:4]
        month_ind = date[5:7].replace("0", "")
        # print(date,year,month_ind)
        month = calendar.month_abbr[int(month_ind)]
        tags[i] = month + "-" + year
        i = i + 1

    return tags


def get_default_tag_indices(all_dates, surfacepath, delimiter):
    (
        directory,
        realization,
        ensemble,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(surfacepath, delimiter)

    if dates[0] > dates[1]:
        difference = "reverse"
    else:
        difference = "normal"

    time1 = dates[0]
    time2 = dates[1]

    ind = [None, None]

    i = 0

    for date in all_dates:
        if date == time1 and difference == "reverse":
            ind[1] = i + 1
        elif date == time1 and difference == "normal":
            ind[0] = i + 1

        if date == time2 and difference == "reverse":
            ind[0] = i + 1
        elif date == time2 and difference == "normal":
            ind[1] = i + 1

        i = i + 1

    return ind


def get_selected_interval(dates, indices):

    if indices[0] > indices[1]:
        difference = "reverse"
    else:
        difference = "normal"

    if difference == "reverse":
        start_date = dates[indices[1] - 1]
        end_date = dates[indices[0] - 1]
    elif difference == "normal":
        start_date = dates[indices[0] - 1]
        end_date = dates[indices[1] - 1]

    return start_date + "_" + end_date


def get_map_info(surfacepath, delimiter):
    # print('get_map_info ',surfacepath)
    (
        directory,
        realization,
        ensemble,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(str(surfacepath), delimiter)
    # print(realization, ensemble, map_type, name, attribute, dates)
    map_dir = directory

    if map_type == "observations":
        map_label = "Observed 4D attribute"
    else:
        map_label = "Simulated 4D attribute"

    return map_dir, map_label, attribute


def sort_realizations(realizations):
    numbers = []
    sorted_list = []

    for realization in realizations:
        ind = realization.find("-")
        numbers.append(int(realization[ind + 1 :]))

    numbers.sort()

    for number in numbers:
        sorted_list.append("realization-" + str(number))

    return sorted_list


def get_attributes(metadata, map_type):
    attributes = []
    selected_type = metadata.loc[metadata["map_type"] == map_type]

    if not selected_type.empty:
        attribute_list = selected_type["data.content"].values
        attributes = list(set(attribute_list))

    return sorted(attributes)


def get_names(metadata, map_type):
    names = []
    selected_type = metadata.loc[metadata["map_type"] == map_type]

    if not selected_type.empty:
        names_list = selected_type["data.name"].values
        names = list(set(names_list))

    return sorted(names)


def get_realizations(metadata, map_type):
    realizations = []
    selected_type = metadata.loc[metadata["map_type"] == map_type]

    if not selected_type.empty:
        realizations_list = selected_type["fmu_id.realization"].values
        realizations = list(set(realizations_list))

    return sorted(realizations)


def get_ensembles(metadata, map_type):
    ensembles = []
    selected_type = metadata.loc[metadata["map_type"] == map_type]

    if not selected_type.empty:
        ensembles_list = selected_type["fmu_id.iteration"].values
        ensembles = list(set(ensembles_list))

    return sorted(ensembles)


def main():
    # Reek data
    print("Reek")
    config_file = "./examples/reek_4d.yaml"
    config = common.read_config(config_file)

    print(config_file)
    print(config)

    wellfolder = common.get_config_item(config, "wellfolder")
    print("wellfolder", wellfolder)

    settings_file = common.get_config_item(config, "settings_file")
    print("settings_file", settings_file)
    settings_file = common.get_full_path(settings_file)
    print("settings_file", settings_file)
    print("")

    # Johan Sverdrup (Eli/Tonje)
    print("Johan Sverdrup - synthetic 4D maps")
    config_file = "configurations/js_test_eli_v2.yaml"
    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]
    print(config_file)
    print(config)

    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")

    metadata = get_metadata(shared_settings, map_suffix, delimiter, metadata_file)
    print(metadata)

    all_intervals, incremental_intervals = get_all_intervals(metadata, "reverse")
    print("incremental_intervals")
    print(incremental_intervals)
    print("all_intervals")
    print(all_intervals)
    print("")

    # Johan Sverdrup (Simulation model)
    print("Johan Sverdrup - simulation model")
    config_file = "configurations/js_test.yaml"
    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]
    print(config_file)
    print(config)

    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")

    metadata = get_metadata(shared_settings, map_suffix, delimiter, metadata_file)
    print(metadata)

    all_intervals, incremental_intervals = get_all_intervals(metadata, "reverse")
    print("incremental_intervals")
    print(incremental_intervals)
    print("all_intervals")
    print(all_intervals)
    print("")

    # Grane
    print("Grane")
    config_file = "configurations/config_template.yaml"
    print(config_file)
    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]

    map_suffix = common.get_config_item(config, "map_suffix")
    print("map_suffix", map_suffix)

    delimiter = common.get_config_item(config, "delimiter")
    print("delimiter", delimiter)

    metadata_file = common.get_config_item(config, "surface_metadata")
    print("metadata_file", metadata_file)

    metadata = get_metadata(shared_settings, map_suffix, delimiter, metadata_file)
    print(metadata)

    all_intervals, incremental_intervals = get_all_intervals(metadata, "reverse")
    print("incremental_intervals")
    print(incremental_intervals)
    print("all_intervals")
    print(all_intervals)


if __name__ == "__main__":
    main()
