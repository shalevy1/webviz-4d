import os
import glob
import sys
import pandas as pd
import numpy as np
from pandas import json_normalize
import yaml
import re
import calendar


def get_map_defaults(configuration, n):
    map_defaults = []

    interval = configuration["map_settings"]["default_interval"]

    if not "-" in interval[0:8]:
        date1 = interval[0:4] + "-" + interval[4:6] + "-" + interval[6:8]
        date2 = interval[9:13] + "-" + interval[13:15] + "-" + interval[15:17]
        interval = date1 + "-" + date2
    # print(interval)

    for i in range(0, n):
        key = "map" + str(i + 1) + "_defaults"
        defaults = configuration["map_settings"][key]
        defaults["interval"] = interval
        # print(map_def)
        map_defaults.append(defaults)

    return map_defaults


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
    print("observed_attributes", observed_attributes)
    observed_names = get_names(metadata_df, observations)

    simulated_attributes = get_attributes(metadata_df, simulations)
    print("simulated_attributes", simulated_attributes)
    simulated_names = get_names(metadata_df, simulations)
    realizations = get_realizations(metadata_df, simulations)
    ensembles = get_ensembles(metadata_df, simulations)

    ensemble = ensembles[0]
    realization = realizations[0]

    map_defaults = []

    if observed_attributes:
        rows = metadata_df.loc[
            (metadata_df["data.time.t1"] == default_interval[0:10])
            & (metadata_df["data.time.t2"] == default_interval[11:])
        ]
        #print(rows)
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
                (metadata_df["data.time.t1"] == default_interval[0:10])
                & (metadata_df["data.time.t2"] == default_interval[11:])
            ]
            print(rows)
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
                (metadata_df["data.time.t1"] == default_interval[0:10])
                & (metadata_df["data.time.t2"] == default_interval[11:])
            ]
        #print(rows)
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


def get_well_colors(configuration):
    try:
        well_colors = configuration["well_colors"]
    except:
        well_colors = None

    return well_colors


def check_yaml_file(surfacepath):
    mapfile_name = str(surfacepath)

    yaml_file = (
        os.path.dirname(mapfile_name) + "/." + os.path.basename(mapfile_name) + ".yaml"
    )
    status = os.path.isfile(yaml_file)

    return status


def extract_metadata(fmu_folder):
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
    interval_df = df[["data.time.t1", "data.time.t2"]]
    new_df = interval_df.drop_duplicates()
    sorted_df = new_df.sort_values(
        by=["data.time.t1", "data.time.t2"], ascending=[True, False]
    )

    incremental_list = []
    additional_list = []

    previous_value = None
    for index, row in sorted_df.iterrows():
        interval = row["data.time.t1"] + "-" + row["data.time.t2"]

        if index == 0:
            incremental_list.append(interval)
            previous_value = row["data.time.t1"]
        else:
            if not row["data.time.t1"] == previous_value:
                incremental_list.append(interval)
                previous_value = row["data.time.t1"]
            else:
                additional_list.append(interval)
                previous_value = row["data.time.t1"]

    incremental_list.extend(additional_list)

    return incremental_list


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
    folder = None
    map_type = None
    iteration = None
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
            
    if "pred" in surfacepath:
        iteration = "pred"        

    #print('decode ', surfacepath,realization, iteration, map_type, name, attribute, dates)
    return folder, realization, iteration, map_type, name, attribute, dates


def get_metadata(directory, delimiter):
    metadata_file = os.path.join(directory, "surface_metadata.csv")
    
    if os.path.isfile(metadata_file):
        metadata = pd.read_csv(metadata_file)
        print("Reading surface metadata ...")
    else:    
        print("Compiling surface metadata ...")
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

        files = glob.glob(directory + "/**/*.gri", recursive=True)

        for filename in files:
            (
                folder,
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

        metadata = pd.DataFrame(zipped_list, columns=headers)
        metadata.fillna(value=np.nan, inplace=True)

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
    directory, real, iteration, map_type, name, attribute, interval, delimiter
):
    # print('compose_filename ',directory, real, iteration, map_type, name, attribute, interval, delimiter)
    surfacepath = None

    if type(real) == int:
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


def get_plot_label(configuration, interval):
    difference_mode = "normal"
    labels = []

    dates = [
        interval[:4] + interval[5:7] + interval[8:10],
        interval[11:15] + interval[16:18] + interval[19:21],
    ]

    for date in dates:
        # date = convert_date(date)
        try:
            labels_dict = configuration["date_labels"]
            label = labels_dict[int(date)]
        except:
            label = date[:4] + "-" + date[4:6] + "-" + date[6:8]

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

    # print(config_dict)
    return config_dict


def get_colormap(configuration, attribute):
    colormap = None
    minval = None
    maxval = None

    try:
        attribute_dict = configuration[attribute]
        # print("attribute_dict", attribute_dict)
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
    
    
def get_update_dates(wellfolder):
    update_dates = {}
    
    try:
        well_date_file = os.path.join(wellfolder,".welldata_update.yaml")

        with open(well_date_file, "r") as stream:
            well_meta_data = yaml.safe_load(stream)
            
        well_update = well_meta_data[0]["welldata"]["update_time"]
        update_dates["well_update_date"] = well_update.strftime("%Y-%m-%d %H:%M:%S")
    except:
        update_dates["well_update_date"] = ''
    
    try:
        prod_date_file = os.path.join(wellfolder,".production_update.yaml")

        with open(prod_date_file, "r") as stream:
            production_meta_data = yaml.safe_load(stream)
          
        print(production_meta_data)
        first_date = production_meta_data[0]["production"]["start_date"].strftime("%Y-%m-%d")
        last_date = production_meta_data[0]["production"]["last_date"].strftime("%Y-%m-%d")
        
        update_dates["production_first_date"] = first_date           
        update_dates["production_last_date"] = last_date   
    except:  
        update_dates["production_first_date"] = ''           
        update_dates["production_last_date"] = ''  
        
    #print("Update dates", update_dates)        
    
    return update_dates    


def main():
    delimiter = "--"
    folder = "/scratch/ert-grane/Petek2019/gra19_r002_One2One_320real_PredReal0"
    folder = "/private/ashska/tmp/"

    pd.set_option('display.max_rows', None)
    metadata = get_metadata(folder,delimiter)

    print(metadata)


if __name__ == "__main__":
    main()
