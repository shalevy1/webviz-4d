""" Collection of common functions """

import os
import io
import glob
import re
from pathlib import Path
import json
import yaml
import pandas as pd
from pandas.io.json import json_normalize
import xtgeo


def read_config(config_file):
    """ Return the content of a configuration file as a dict """
    config_dict = {}

    with open(config_file, "r") as stream:
        config_dict = yaml.safe_load(stream)

    return config_dict


def _find_number(surfacepath, txt):
    """ Return the first number found in a part of a filename (surface) """
    filename = str(surfacepath)
    number = None
    index = str(filename).find(txt)

    if index > 0:
        i = index + len(txt) + 1
        j = filename[i:].find("/")
        number = filename[i : i + j]

    return number


def find_files(folder, suffix) -> io.BytesIO:
    """ Return a sorted list of all files in a folder with a specified suffix  """
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in Path(folder).glob(f"*{suffix}")])
        ).encode()
    )


def load_well(well_path):
    """ Return a well object (xtgeo) for a given file (RMS ascii format) """
    return xtgeo.Well(well_path)


def load_all_wells(wellfolder, wellsuffix):
    """ For all wells in a folder return
        - a list of dataframes with the well trajectories
        - dataframe with metadata for all the wells 
        - a dataframe with production/injection depths (screens or perforated) """
    all_wells_list = []

    print("Loading wells from " + str(wellfolder) + " ...")

    wellfiles = (
        json.load(find_files(wellfolder, wellsuffix))
        if wellfolder is not None
        else None
    )

    if not wellfiles:
        raise Exception("No wellfiles found")

    for wellfile in wellfiles:
        # print(wellfile + " ...")
        try:
            well = load_well(wellfile)
            # print("    - loaded")
        except ValueError:
            continue
        well.dataframe = well.dataframe[["X_UTME", "Y_UTMN", "Z_TVDSS", "MD"]]
        well.dataframe["WELLBORE_NAME"] = well.name
        all_wells_list.append(well.dataframe)

    all_wells_df = pd.concat(all_wells_list)

    _well_info, depths_df = extract_well_metadata(wellfolder)
    metadata_file = os.path.join(wellfolder, "wellbore_info.csv")
    metadata = pd.read_csv(metadata_file)
    # print('load_all_wells ',metadata)

    return (all_wells_df, metadata, depths_df)


def extract_well_metadata(directory):
    """ Compile all metadata for wells in a given folder (+ sub-folders) """
    well_info = []
    depth_info = []

    yaml_files = glob.glob(str(directory) + "/**/.*.yaml", recursive=True)

    for yaml_file in yaml_files:
        with open(yaml_file, "r") as stream:
            data = yaml.safe_load(stream)
            # print('data',data)

            well_info.append(data[0])

            if len(data) > 1 and data[1]:
                for item in data[1:]:
                    depth_info.append(item)

    well_info_df = json_normalize(well_info)

    depth_df = json_normalize(depth_info)

    if not depth_df.empty:
        depth_df.sort_values(by=["interval.wellbore", "interval.mdTop"], inplace=True)

    return well_info_df, depth_df


def get_metadata(directory, defaults, delimiter):
    """ Return metadata and the unique dates for all 
    surfaces in a given folder by decoding of the file names """
    filename = compose_filename(
        directory,
        defaults["realization"],
        defaults["ensemble"],
        defaults["map_type"],
        defaults["name"],
        defaults["attribute"],
        defaults["interval"],
        delimiter,
    )
    # print('filename ' ,filename)

    surfacepath = str(filename)
    realizations = []
    iterations = []
    map_types = []
    names = []
    attributes = []
    times1 = []
    times2 = []
    filenames = []
    headers = [
        "fmu_id.realization",
        "fmu_id.iteration",
        "map_type",
        "data.name",
        "data.content",
        "data.time.t1",
        "data.time.t2",
        "filename",
    ]

    all_dates = []

    index = surfacepath.find("realization")
    directory = os.path.join(surfacepath[:index])

    files = glob.glob(directory + "/**/*.gri", recursive=True)

    for filename in files:
        (
            directory,
            realization,
            iteration,
            map_type,
            name,
            attribute,
            dates,
        ) = decode_filename(filename, delimiter)

        if dates[0] and dates[1]:
            all_dates.append(dates[0])
            all_dates.append(dates[1])

            realizations.append(realization)
            iterations.append(iteration)
            map_types.append(map_type)
            names.append(name)
            attributes.append(attribute)
            times1.append(dates[0])
            times2.append(dates[1])
            filenames.append(filename)

    zipped_list = list(
        zip(
            realizations,
            iterations,
            map_types,
            names,
            attributes,
            times1,
            times2,
            filenames,
        )
    )

    metadata_df = pd.DataFrame(zipped_list, columns=headers)
    metadata_df.fillna(value=pd.np.nan, inplace=True)

    list_set = set(all_dates)
    unique_list = list(list_set)
    unique_dates = sorted(unique_list)

    return metadata_df, unique_dates


def compose_filename(
    directory, real, iteration, map_type, name, attribute, interval, delimiter
):
    """ Return expected filename based on given metadata """
    surfacepath = None

    if isinstance(real,int):
        realization = "realization-" + str(real)
    else:
        realization = real

    # if '-' in dates[0]:
    #    dates = convert_date(dates[0]) + "_" + convert_date(dates[1])

    interval_string = interval.replace("-", "")
    datestring = interval_string[:8] + "_" + interval_string[8:]
    # print(directory, realization, iteration, map_type, name, attribute, datestring)

    filename = name + delimiter + attribute + delimiter + datestring + ".gri"
    # print(filename)

    index = directory.find("realization")
    if map_type == "results":
        surfacepath = os.path.join(
            directory[:index],
            realization,
            iteration,
            "share",
            map_type,
            "maps",
            filename,
        )
    elif map_type == "observations":
        surfacepath = os.path.join(
            directory[:index],
            realization,
            iteration,
            "share",
            map_type,
            "maps",
            filename,
        )

    # print('surfacepath ',surfacepath)
    return surfacepath


def decode_filename(file_path, delimiter):
    """ Create metadata from surface file name """
    surfacepath = str(file_path)
    ind = []
    number = None
    directory = None
    map_type = None
    iteration = None
    realization = None
    name = None
    attribute = None
    dates = [None, None]

    directory = os.path.dirname(surfacepath)

    if "observations" in str(surfacepath):
        map_type = "observations"

    if "results" in str(surfacepath):
        map_type = "results"

        number = _find_number(surfacepath, "realization")

        if number:
            realization = "realization-" + number
            number = None

            if realization:
                number = _find_number(surfacepath, "iter")

                if number:
                    iteration = "iter-" + number

    for m in re.finditer(delimiter, str(surfacepath)):
        ind.append(m.start())

    k = str(surfacepath).rfind("/")

    if len(ind) > 1:
        name = str(surfacepath)[k + 1 : ind[0]]
        attribute = str(surfacepath)[ind[0] + 2 : ind[1]]
        # print(surfacepath,name,attribute)

        if len(ind) == 2 and len(str(surfacepath)) > ind[1] + 19:
            date = str(surfacepath)[ind[1] + 2 : ind[1] + 10]
            dates[0] = convert_date(date)

            date = str(surfacepath)[ind[1] + 11 : ind[1] + 19]
            dates[1] = convert_date(date)

    # print('decode ', realization, iteration, map_type, name, attribute, dates)
    return directory, realization, iteration, map_type, name, attribute, dates


def get_map_defaults(configuration, n_maps):
    """ Return default settings for maps (extracted from configuration file) """
    map_defaults = []

    interval = configuration["map_settings"]["default_interval"]

    if not "-" in interval[0:8]:
        date1 = interval[0:4] + "-" + interval[4:6] + "-" + interval[6:8]
        date2 = interval[9:13] + "-" + interval[13:15] + "-" + interval[15:17]
        interval = date1 + "-" + date2
    # print(interval)

    for i in range(0, n_maps):
        key = "map" + str(i + 1) + "_defaults"
        defaults = configuration["map_settings"][key]
        defaults["interval"] = interval
        # print(map_def)
        map_defaults.append(defaults)

    return map_defaults


def convert_date(date):
    """ Convert between dates with or without hyphen """
    date_string = date

    if len(date) == 8:
        date_string = date[0:4] + "-" + date[4:6] + "-" + date[6:8]

    if "-" in date:
        date_string = date[0:4] + date[5:7] + date[8:10]

    return date_string


def all_interval_dates(directory, delimiter, suffix):
    """ Return all 4D intervals in surface files in a FMU directory """
    all_dates = []

    files = glob.glob(directory + "/**/*" + suffix, recursive=True)

    for filename in files:
        (
            directory,
            _realization,
            _iteration,
            _map_type,
            _name,
            _attribute,
            dates,
        ) = decode_filename(filename, delimiter)

        if dates[0] and dates[1]:
            all_dates.append(dates[0])
            all_dates.append(dates[1])

    list_set = set(all_dates)
    unique_list = list(list_set)
    unique_dates = sorted(unique_list)
    return unique_dates


def get_well_colors(configuration):
    """ Return well colors from a configuration """
    return configuration["well_colors"]


def get_all_intervals(metadata_df):
    """ Return all 4D intervals from a metadata dateframe """
    intervals = metadata_df[["data.time.t1", "data.time.t2"]].values
    # print('get_all_intervals ',intervals)

    interval_list = []
    for interval in intervals:
        interval_list.append(interval[0] + "-" + interval[1])

    list_set = set(interval_list)
    unique_list = list(list_set)
    interval_list = sorted(unique_list)
    # print(interval_list)

    return interval_list


def extract_wellbore_metadata(directory):
    """ Return all well metadata found in yaml files in a given folder """
    well_info = []
    interval_info = []

    print(str(directory))
    yaml_files = glob.glob(str(directory) + "/.*yaml", recursive=True)

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
    """ Return selected metadata for a selected wellbore """
    value = None

    well_metadata = metadata_df[metadata_df["wellbore.name"] == wellbore_name]

    if not well_metadata.empty:
        value = well_metadata[item].values[0]

    return value


def get_wellbores(metadata_df, well_name):
    """ Return all possible wellbores for a selected well """
    wellbores = metadata_df[metadata_df["wellbore.slot_name"] == well_name]
    wellbore_names = wellbores["wellbore.name"].values

    return sorted(wellbore_names)


def get_mother_wells(metadata_df, well_name):
    """ Don't understand """
    mother_wells = [well_name]

    wellbores = get_wellbores(metadata_df, well_name)
    # print('wellbores ',wellbores)

    mother_well = well_name
    for wellbore in wellbores:
        if not wellbore == mother_well and not wellbore[-2] == "T":
            if wellbore[-1] in "123456789":
                last = len(wellbore) - 1
            else:
                last = len(wellbore)
            name = wellbore[:last]

            if not name == mother_well:
                mother_well = name
                mother_wells.append(mother_well)

    list_set = set(mother_wells)
    unique_list = sorted(list(list_set))

    return unique_list


def get_branches(well_info_df, mother_well):
    """ Obsolete? """
    branches = []
    i = mother_well.rfind(" ")

    possible_branches = well_info_df[
        well_info_df["wellbore.name"].str.contains(mother_well, regex=False)
    ]["wellbore.name"].values

    for branch in possible_branches:
        i_branch = branch.rfind(" ")
        last = len(branch)

        if (
            branch == mother_well or branch[: last - 1] == mother_well + " T"
        ):  # Sidetracked mother wells
            branches.append(branch)

        elif mother_well[:i] == branch[:i_branch] and not i == 2:
            branches.append(branch)

    return sorted(branches)


def get_wellname(well_info_df, wellbore):
    """ Return well name for a selected wellbore """
    well_name = get_well_metadata(well_info_df, wellbore, "wellbore.slot_name")

    if well_name:
        mother_wells = get_mother_wells(well_info_df, well_name)
        # print(mother_wells)

        for mother_well in mother_wells:
            branches = get_branches(well_info_df, mother_well)
            # print(branches)

            for branch in branches:
                if branch == wellbore:
                    return mother_well

    return None


def sort_wellbores(well_names):
    """ Return a sorted list of wellbore names given a list of well names """
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

    new_df = pd.DataFrame(
        zip(well_names, block_names, slot_names, slot_numbers, branch_names),
        columns=["Well_name", "Block_name", "Slot_name", "Slot_number", "Branch_name"],
    )

    # pd.set_option('display.max_rows', None)
    new_df.sort_values(
        by=["Block_name", "Slot_name", "Slot_number", "Branch_name"], inplace=True
    )
    sorted_wellbores = new_df["Well_name"].values

    return sorted_wellbores


def is_nan(string):
    return string != string


def get_position_data(well_dataframe, md_start):
    """ Return x- and y-values for a well after a given depth """
    well_dataframe = well_dataframe[well_dataframe["MD"] > md_start]
    positions = well_dataframe[["X_UTME", "Y_UTMN"]].values

    return positions
