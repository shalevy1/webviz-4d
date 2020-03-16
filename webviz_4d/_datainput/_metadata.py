#!/usr/bin/env python3
import os
import glob
import sys
import pandas as pd
from pandas.io.json import json_normalize
import yaml
import re
import calendar


def get_map_defaults(configuration):
    map_defaults = []
    
    defaults = {
        "attribute": "maxpos",
        "name": "all",
        "interval": "20190915-20190515",
        "map_type": "observations",
        "ensemble": "iter-0",
        "realization": "realization-0",
    }
    map_defaults.append(defaults)
    defaults = {
        "attribute": "maxpos",
        "name": "all",
        "interval": "20190915-20190515",
        "map_type": "results",
        "ensemble": "iter-0",
        "realization": "realization-0",
    }
    map_defaults.append(defaults)
    defaults = {
        "attribute": "oilthickness",
        "name": "all",
        "interval": "20190915-20190515",
        "map_type": "results",
        "ensemble": "iter-0",
        "realization": "realization-0",
    }
    map_defaults.append(defaults)
    
    return map_defaults


def check_yaml_file(surfacepath):
    mapfile_name = str(surfacepath)
    
    yaml_file = os.path.dirname(mapfile_name) + "/." + os.path.basename(mapfile_name) + ".yaml"
    status = os.path.isfile(yaml_file)
    
    return status


def extract_metadata(map_file):
    meta_data = []
    index = map_file.find("realization")

    yaml_files = glob.glob(map_file[:index] + "/**/.*.yaml", recursive=True)

    for yaml_file in yaml_files:
        with open(yaml_file, "r") as stream:
            data = yaml.safe_load(stream)
            meta_data.append(data)

    df = json_normalize(meta_data)
    df["yaml_file"] = yaml_files

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
            "yaml_file",
        ]
    ].copy()

    df_timelapse = new_df[new_df["data.time.t2"].notnull()]

    time1 = df_timelapse["data.time.t1"].unique()
    time2 = df_timelapse["data.time.t2"].unique()

    times = list(time1)
    times.extend(time2)

    list_set = set(times)
    unique_list = list(list_set)
    times = sorted(unique_list)

    return df_timelapse, times


def find_number(surfacepath, txt):
    filename = str(surfacepath)
    number = None
    index = str(filename).find(txt)

    if index > 0:
        i = index + len(txt) + 1
        j = filename[i:].find("/")
        number = filename[i : i + j]

    return number


def convert_date(date):
    if len(date) == 8:
        return date[0:4] + "-" + date[4:6] + "-" + date[6:8]

    if "-" in date:
        return date[0:4] + date[5:7] + date[8:10]
        
        
def get_all_intervals(df):
    intervals = df[['data.time.t1','data.time.t2']].values
    #print('get_all_intervals ',intervals)
    
    interval_list = []
    for interval in intervals:
        interval_list.append(interval[0] + '-' + interval[1])
    
    list_set = set(interval_list)
    unique_list = list(list_set)
    interval_list = sorted(unique_list)
    #print(interval_list)

    return interval_list 


def get_difference_mode(surfacepath, delimiter):
    (
        directory,
        realization,
        iteration,
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

        number = find_number(surfacepath, "realization")

        if number:
            realization = "realization-" + number
            number = None

            if realization:
                number = find_number(surfacepath, "iter")

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


def get_metadata(directory,defaults, delimiter):
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
    #print('filename ' ,filename)

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

    df = pd.DataFrame(zipped_list, columns=headers)
    df.fillna(value=pd.np.nan, inplace=True)

    list_set = set(all_dates)
    unique_list = list(list_set)
    unique_dates = sorted(unique_list)
    return df, unique_dates


def unique_values(list_values):
    clean_list = [value for value in list_values if str(value) != "nan"]
    list_set = set(clean_list)
    unique_list = list(list_set)

    return sorted(unique_list)


def get_col_values(df, col_name):
    return unique_values(df[col_name].values)


def compose_filename(
    directory, real, iteration, map_type, name, attribute, interval, delimiter
):
    #print('compose_filename ',directory, real, iteration, map_type, name, attribute, interval, delimiter)
    surfacepath = None
    
    if type(real) == int:
        realization = 'realization-' + str(real)
    else:    
        realization = real

    #if '-' in dates[0]:
    #    dates = convert_date(dates[0]) + "_" + convert_date(dates[1])
        
    interval_string = interval.replace('-','')
    datestring = interval_string[:8] + '_' + interval_string[8:]
    #print(directory, realization, iteration, map_type, name, attribute, datestring)    
        
    filename = name + delimiter + attribute + delimiter + datestring + ".gri"
    #print(filename)
    
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
        surfacepath = os.path.join(directory[:index],realization,iteration, "share", map_type, "maps", filename)

    #print('surfacepath ',surfacepath)
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
    #print(dates)
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
        iteration,
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
        iteration,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(str(surfacepath), delimiter)
    # print(realization, iteration, map_type, name, attribute, dates)
    map_dir = directory

    if map_type == "observations":
        map_label = "Observed 4D attribute"
    else:
        map_label = "Simulated 4D attribute"

    return map_dir, map_label, attribute


def get_plot_label(configuration, interval, difference_mode):     
    labels = []

    dates = interval.split("_")

    for date in dates:
        date = convert_date(date)
        try:       
            labels_dict = configuration["date_labels"]    
            label = labels_dict[int(date)]
        except:
            label = date[:4]

        labels.append(label)

    if difference_mode == "normal":
        label = labels[0] + " - " + labels[1]
    else:
        label = labels[1] + " - " + labels[0]

    return label


def read_config(config_file):

    config_dict = {}

    with open(config_file, "r") as stream:
        config_dict = yaml.safe_load(stream)

    #print(config_dict)
    return config_dict


def get_colormap(configuration, attribute):
    colormap = None
    minval = None
    maxval = None

    try:
        attribute_dict = configuration[attribute]
        #print("attribute_dict", attribute_dict)
        colormap = attribute_dict["colormap"]
        minval = attribute_dict["min_value"]
        minval = attribute_dict["max_value"]
    except:
        try:
            map_settings = configuration("map_settings")
            colormap = map_settings("default_colormap")
        except:
            print("No default colormaps found for ", attribute)

    return colormap, minval, maxval


def main():
    delimiter = "--"
    file_name = "/scratch/ert-grane/Petek2019/Petek2019_r001/realization-0/iter-0/share/results/maps/all--maxpos--20190915_20190515.gri"
    config_file: "../../webviz-4d/fields/grane_mvp_config.yaml"
    configuration = read_config(config_file)

    map_file = "/scratch/johan_sverdrup2/jsorb/2020a_b006p2p0_yaml/realization-0/pred/share/maps/recoverables/total--average_pressure--20190101_20250101.gri"
    print(check_yaml_file(map_file))
    df ,dates = extract_metadata(map_file)

    print(df)
    print(dates)
    df.to_csv('js.csv')

    file_name = "/private/ashska/development/webviz-subsurface-testdata/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--amplitude_max--20030101_20000101.gri"
    (
        directory,
        realization,
        iteration,
        map_type,
        name,
        attribute,
        dates,
    ) = decode_filename(file_name, delimiter)
    print(file_name)
    print(directory, realization, iteration, map_type, name, attribute, dates)

    reek_df, reek_dates = get_metadata(file_name, delimiter)
    print(reek_dates)
    print(reek_df)
    print("Realizations: ", get_col_values(reek_df, "fmu_id.realization"))
    print(reek_df[reek_df["filename"] == file_name])

    print(
        "Default indices: ", get_default_tag_indices(reek_dates, file_name, delimiter)
    )
    default_tag_indices = get_default_tag_indices(reek_dates, file_name, delimiter)
    print("Selected interval: ", get_selected_interval(reek_dates, default_tag_indices))

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

    grane_df, grane_dates = get_metadata(file_name, delimiter)
    print(file_name)
    print(grane_dates)
    print(grane_df)
    print(grane_df[grane_df["filename"] == file_name])

    print(
        "Default indices: ", get_default_tag_indices(grane_dates, file_name, delimiter)
    )
    print("")

    file_name = compose_filename(
        directory,
        realization,
        iteration,
        map_type,
        name,
        attribute,
        [grane_dates[-1], grane_dates[-2]],
        delimiter,
    )
    print(file_name, os.path.isfile(file_name))
    print("")

    file_name = "/scratch/johan_sverdrup2/jsorb/2020a_b006p2p0_yaml/realization-0/pred/share/maps/recoverables/total--average_pressure--20190101_20250101.gri"
    directory = os.path.dirname(file_name)
    name = os.path.basename(file_name)
    yaml_file = directory + "/." + name + ".yaml"
    print(file_name)
    print(yaml_file)

    js_df, js_dates = extract_metadata(file_name)
    print(type(js_df))
    print(js_dates)
    print(js_df)

    print(js_df[js_df["yaml_file"] == yaml_file])


if __name__ == "__main__":
    main()
