#!/usr/bin/env python3
import os
import sys
import glob
import re
import ruamel.yaml
from ruamel import yaml
from .._datainput._well import load_well
import calendar


def read_config(config_file, node, key, *args):
    items = None

    if not os.path.isfile(config_file):
        print("ERROR: Configuration file: " + config_file + " not found")
        return items

    with open(config_file, "r") as f:
        common_config = yaml.load(f, Loader=ruamel.yaml.RoundTripLoader)

    if not key == "*":
        try:
            items = common_config[node][key]
        except:
            print("WARNING: node or key not found: " + node + " " + key)
    else:
        try:
            items = common_config[node]
        except:
            print("WARNING: node not found: " + node)

    return items


def get_field_name(config_file):
    node = "field"
    key = "name"
    try:
        name = read_config(config_file, node, key)
    except:
        name = ""

    return name


def read_date_labels(config_file):
    node = "date_labels"
    labels_dict = {}

    labels = read_config(config_file, node, "*")

    if labels:
        for label in labels:
            date = read_config(config_file, node, label)
            labels_dict[str(date)] = label

    return labels_dict


def get_filenames(config_file, node):
    key = "directory"

    directory = read_config(config_file, node, key)

    return glob.glob(os.path.join(directory, "*.gri"))


def decode_filename(surfacepath):
    attribute_name = None
    dates = []
    interval = None

    ind = []

    for m in re.finditer("--", surfacepath):
        ind.append(m.start())

    # print('decode_filename',surfacepath,ind)

    if len(ind) == 2 and len(surfacepath) > ind[1] + 19:
        attribute_name = surfacepath[ind[0] + 2 : ind[1]]
        dates.append(surfacepath[ind[1] + 2 : ind[1] + 10])
        dates.append(surfacepath[ind[1] + 11 : ind[1] + 19])
        interval = surfacepath[ind[1] + 2 : ind[1] + 19]
    elif len(ind) == 3 and surfacepath[ind[1] + 11 : ind[1] + 12] in "123":
        # elif len(ind) == 3:
        # print(surfacepath, ind)
        # print(surfacepath[ind[1]+11:ind[1]+12])
        attribute_name = surfacepath[ind[0] + 2 : ind[1]]
        dates.append(surfacepath[ind[1] + 2 : ind[1] + 10])
        dates.append(surfacepath[ind[1] + 11 : ind[2]])
        interval = surfacepath[ind[1] + 2 : ind[2]]

    # print(interval)
    return attribute_name, dates, interval


def read_attributes(config_file, node):
    key = "directory"

    directory = read_config(config_file, node, key)
    files = glob.glob(os.path.join(directory, "*.gri"))

    all_dates = []
    intervals = []
    attributes = []

    for file_name in files:
        attribute_name, dates, interval = decode_filename(file_name)

        if attribute_name and attribute_name not in attributes:
            attributes.append(attribute_name)

        for date in dates:
            if date and date not in all_dates:
                all_dates.append(date)

        if interval and interval not in intervals:
            intervals.append(interval)

    # print("read_attributes", sorted(intervals))

    return sorted(attributes), sorted(all_dates), sorted(intervals, reverse=True)


def get_directory(config_file, node):
    key = "directory"
    directory = read_config(config_file, node, key)

    return directory


def get_intervals(config_file, node):
    attributes, dates, intervals = read_attributes(config_file, node)

    return intervals


def get_file_path(config_file, map_id, attribute, interval):
    start_txt = read_config(config_file, "map1", "default_prefix")
    end_txt = read_config(config_file, "map1", "default_postfix")

    if end_txt:
        end_txt = "--" + end_txt
    else:
        end_txt = ""

    # print("get_file_path", start_txt, end_txt)
    ext = ".gri"

    return os.path.join(
        get_directory(config_file, map_id),
        start_txt + "--" + attribute + "--" + interval + end_txt + ext,
    )


def read_wells(config_file):
    node = "wells"
    key = "directory"

    wells_directory = read_config(config_file, node, key)
    well_files = glob.glob(os.path.join(wells_directory, "*.w"))

    wells = []

    for well_file in well_files:
        well = load_well(well_file)
        wells.append(well)

    return wells


def get_plot_label(config_file, interval):
    labels_dict = read_date_labels(config_file)

    dates = interval.split("_")
    labels = []

    for date in dates:
        if str(date) in labels_dict:
            label = labels_dict[date]
        else:
            label = date[:4]

        labels.append(label)

    label = labels[0] + " - " + labels[1]

    return label


def get_field_bounds(config_file):
    node = "field_bounds"
    keys = ["xmin", "xmax", "ymin", "ymax"]

    coordinates = []

    for key in keys:
        coordinates.append(read_config(config_file, node, key))

    return [[coordinates[0], coordinates[2]], [coordinates[1], coordinates[3]]]


def get_colormap(config_file, surfacepath):
    colormap = read_config(config_file, "map_settings", "default_colormap")
    minval = None
    maxval = None

    attribute, dates, interval = decode_filename(surfacepath)

    try:
        colormap = read_config(config_file, attribute, "colormap")
        minval = read_config(config_file, attribute, "min_value")
        maxval = read_config(config_file, attribute, "max_value")

    except:
        colormap = read_config(config_file, "map_settings", "default_colormap")
        minval = None
        maxval = None

    return colormap, minval, maxval


def get_slider_tags(config_file):
    attributes, dates, intervals = read_attributes(config_file, "map1")

    tags = {}
    i = 1
    for date in dates:
        year = date[:4]
        month_ind = date[4:6].replace("0", "")
        # print(date,year,month_ind)
        month = calendar.month_abbr[int(month_ind)]
        tags[i] = month + "-" + year
        i = i + 1

    return tags, dates


def get_map_info(config_file, map_id):
    map_dir = read_config(config_file, map_id, "directory")
    map_label = read_config(config_file, map_id, "label")
    attribute = read_config(config_file, map_id, "default_attribute")

    return map_dir, map_label, attribute


def get_attribute(config_file, map_id):
    return read_config(config_file, map_id, "default_attribute")


def get_selected_interval(config_file, map_id, dates, indices):
    # print(dates, indices)
    difference = read_config(config_file, map_id, "difference")

    if not difference:
        difference = "reverse"

    if difference == "reverse":
        start_date = dates[indices[1] - 1]
        end_date = dates[indices[0] - 1]
    elif difference == "normal":
        start_date = dates[indices[0] - 1]
        end_date = dates[indices[1] - 1]

    return start_date + "_" + end_date


def get_default_tag_indices(config_file):
    attributes, dates, intervals = read_attributes(config_file, "map1")
    difference = read_config(config_file, "map1", "difference")

    if not difference:
        difference = "reverse"

    time1 = read_config(config_file, "defaults", "time1")
    time2 = read_config(config_file, "defaults", "time2")
    print(time1, time2)

    ind = [None, None]

    if time1 and time2:
        interval = str(time1) + "-" + str(time2)
        # print(interval)
        first_date = interval[:8]
        second_date = interval[9:]

        # print("Default interval: ", first_date, second_date)

        i = 0

        for date in dates:
            if date == first_date and difference == "reverse":
                ind[1] = i + 1
            elif date == first_date and difference == "normal":
                ind[0] = i + 1

            if date == second_date and difference == "reverse":
                ind[0] = i + 1
            elif date == second_date and difference == "normal":
                ind[1] = i + 1

            i = i + 1
    else:
        ind = [len(dates) - 1, len(dates)]

    return ind
