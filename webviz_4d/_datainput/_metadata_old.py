#!/usr/bin/env python3
import os
import glob
import sys
import pandas as pd
from pandas.io.json import json_normalize
import yaml
import re


def extract_metadata(map_file):
    meta_data = []
    index = map_file.find("realization")

    yaml_files = glob.glob(map_file[:index] + "/**/.*.yaml", recursive=True)

    for yaml_file in yaml_files:
        with open(yaml_file, "r") as stream:
            data = yaml.safe_load(stream)
            meta_data.append(data)

    df = json_normalize(meta_data)
    df["filename"] = yaml_files

    # df.to_csv('index.csv')
    # df = pd.read_csv("index.csv")

    new_df = df[
        [
            "fmu_id.case",
            "fmu_id.revision_sub",
            "fmu_id.revision_main",
            "fmu_id.iteration",
            "fmu_id.realization",
            "fmu_id.user",
            "data.name",
            "data.unit",
            "data.content",
            "data.domain",
            "data.subdomain",
            "data.time.t1",
            "data.time.t2",
            "visual_settings.display_name",
            "visual_settings.subtitle",
            "visual_settings.colors.colormap",
            "visual_settings.colors.display_min",
            "visual_settings.colors.display_max",
            "filename",
        ]
    ].copy()

    df_timelapse = new_df[new_df["data.time.t2"].notnull()]
    iterations = df_timelapse["fmu_id.iteration"].unique()
    realizations = df_timelapse["fmu_id.realization"].unique()
    names = df_timelapse["data.name"].unique()
    attributes = df_timelapse["data.content"].unique()

    time1 = df_timelapse["data.time.t1"].unique()
    time2 = df_timelapse["data.time.t2"].unique()

    times = list(time1)
    times.extend(time2)

    list_set = set(times)
    unique_list = list(list_set)
    dates = sorted(unique_list)

    # default_yaml_file = directory + '/.' + file_name + '.yaml'
    # default_values = df_timelapse[df_timelapse["map_file"] == default_yaml_file]

    return times, df_timelapse


def find_number(surfacepath, txt):
    number = None
    index = surfacepath.find(txt)

    if index > 0:
        i = index + len(txt) + 1
        j = surfacepath[i:].find("/")
        number = surfacepath[i : i + j]

    return number


def convert_date(date):
    if len(date) == 8:
        return date[0:4] + "-" + date[4:6] + "-" + date[6:8]

    if "-" in date:
        return date[0:4] + date[5:7] + date[8:10]


def decode_filename(surfacepath, delimiter):
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

    number = find_number(surfacepath, "realization")

    if number:
        realization = "realization-" + number
        number = None

        if realization:
            number = find_number(surfacepath, "iter")

            if number:
                iteration = "iter-" + number

                if "observations" in surfacepath:
                    map_type = "Observed"

                if "results" in surfacepath:
                    map_type = "Simulated"

                for m in re.finditer(delimiter, surfacepath):
                    ind.append(m.start())

                k = surfacepath.rfind("/")

                if len(ind) > 1:
                    name = surfacepath[k + 1 : ind[0]]
                    attribute = surfacepath[ind[0] + 2 : ind[1]]
                    # print(surfacepath,name,attribute)

                    if len(ind) == 2 and len(surfacepath) > ind[1] + 19:
                        date = surfacepath[ind[1] + 2 : ind[1] + 10]
                        dates[0] = convert_date(date)

                        date = surfacepath[ind[1] + 11 : ind[1] + 19]
                        dates[1] = convert_date(date)

    return directory, realization, iteration, map_type, name, attribute, dates


def compose_filename(
    directory, realization, iteration, map_type, name, attribute, dates, delimiter
):
    index = directory.find("realization")
    converted_dates = convert_date(dates[0]) + "-" + convert_date(dates[1])
    filename = name + delimiter + attribute + delimiter + converted_dates + ".gri"
    return os.path.join(
        directory[:index], realization, iteration, "share", map_type, "maps", filename
    )


def create_metadata(map_file):
    delimeter = "--"
    directory = os.path.dirname(map_file)

    attributes = []
    dates = []

    #    with open(config_file, "r") as stream:
    #            configuration = yaml.safe_load(stream)

    realizations = get_realizations(file_name)

    for realization in realizations:
        print(realization)

        iterations = get_iterations(file_name, realization)
        print(iterations)

        for iteration in iterations:
            map_types = get_map_types(file_name, realization, iteration)
            print(map_types)

            for map_type in map_types:
                names = get_map_names(
                    file_name, realization, iteration, map_type, delimiter
                )
                print(names)

                for name in names:
                    attributes = get_attributes(
                        file_name, realization, iteration, map_type, name, delimiter
                    )
                    print(attributes)

    grid_files = glob.glob(os.path.join(directory, "*.gri"))

    for grid_file in grid_files:
        iteration, realization, name, attribute, file_dates = decode_filename(grid_file)

        attributes.append(attribute)

        for date in file_dates:
            dates.append(date)

    list_set = set(attributes)
    unique_list = list(list_set)
    unique_attributes = sorted(unique_list)

    return iteration, realization, name, attribute, dates


def get_realizations(surfacepath):
    realizations = []

    index = surfacepath.find("realization")

    directory = surfacepath[:index]

    sub_dirs = [f.name for f in os.scandir(directory) if f.is_dir()]

    for sub_dir in sub_dirs:
        if "realization" in sub_dir:
            realizations.append(sub_dir)

    return sorted(realizations)


def get_iterations(surfacepath, realization):
    iterations = []

    index = surfacepath.find("realization")

    directory = surfacepath[:index] + str(realization)
    # print(directory)

    iterations = [f.name for f in os.scandir(directory) if f.is_dir()]

    return sorted(iterations)


def get_map_types(surfacepath, realization, iteration):
    map_types = []

    index = surfacepath.find("realization")

    directory = os.path.join(surfacepath[:index], realization, iteration, "share/")

    sub_dirs = [f.name for f in os.scandir(directory)]

    for sub_dir in sub_dirs:
        if sub_dir == "results":
            map_types.append("results")

        if sub_dir == "observations":
            map_types.append("observations")

    return map_types


def get_map_names(surfacepath, realization, iteration, map_type, delimiter):
    ind = []
    names = []

    index = surfacepath.find("realization")
    directory = os.path.join(
        surfacepath[:index], realization, iteration, "share", map_type, "maps"
    )

    files = glob.glob(os.path.join(directory, "*.gri"))

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
        if name and dates:
            names.append(name)

    list_set = set(names)
    unique_list = list(list_set)
    unique_names = sorted(unique_list)
    return unique_names


def get_attributes(surfacepath, realization, iteration, map_type, name, delimiter):
    ind = []
    attributes = []

    index = surfacepath.find("realization")
    directory = os.path.join(
        surfacepath[:index], realization, iteration, "share", map_type, "maps"
    )

    files = glob.glob(os.path.join(directory, "*.gri"))

    for filename in files:
        if name in filename:
            (
                directory,
                realization,
                iteration,
                map_type,
                name,
                attribute,
                dates,
            ) = decode_filename(filename, delimiter)
            if attribute and dates:
                attributes.append(attribute)

    list_set = set(attributes)
    unique_list = list(list_set)
    unique_attributes = sorted(unique_list)
    return unique_attributes


def get_metadata(surfacepath, delimiter):
    realizations = []
    iterations = []
    map_types = []
    names = []
    attributes = []
    times1 = []
    times2 = []
    filenames = []
    headers = [
        "realization",
        "iteration",
        "map_type",
        "name",
        "attribute",
        "t1",
        "t2",
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

    df = pd.DataFrame(zipped_list, columns=headers)

    list_set = set(all_dates)
    unique_list = list(list_set)
    unique_dates = sorted(unique_list)
    return df, unique_dates


def main():
    delimiter = "--"
    file_name = "/private/ashska/development/webviz-subsurface-testdata/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--amplitude_max--20030101_20000101.gri"
    # directory, realization, iteration, map_type, name, attribute, dates = decode_filename(file_name,delimiter)

    print(file_name)
    # print(directory)
    # print(realization)
    # print(iteration)
    # print(map_type)
    # print(name)
    # print(attribute)
    # print(dates)

    df, all_dates = get_metadata(file_name, delimiter)
    print(all_dates)
    print(df)
    print(df[df["filename"] == file_name])
    print("")

    file_name = "/scratch/ert-grane/Petek2019/Petek2019_r001/realization-0/iter-0/share/results/maps/all--maxpos--20190915_20190515.gri"
    (
        directory,
        realization,
        iteration,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(file_name, delimiter)

    df, all_dates = get_metadata(file_name, delimiter)
    print(file_name)
    print(all_dates)
    print(df)
    print(df[df["filename"] == file_name])
    print("")

    file_name = compose_filename(
        directory,
        realization,
        iteration,
        map_type,
        name,
        attribute,
        [all_dates[-1], all_dates[-2]],
        delimiter,
    )
    print(file_name)
    print("")

    file_name = "/scratch/johan_sverdrup2/jsorb/2020a_b006p2p0_yaml/realization-0/pred/share/maps/recoverables/total--average_pressure--20190101_20250101.gri"
    df, all_dates = extract_metadata(file_name)
    print(all_dates)
    print(df)
    print(df[df["filename"] == file_name])


if __name__ == "__main__":
    main()
