""" Collection of common functions """

import os
import io
import glob
import re
from pathlib import Path
import json
import yaml
import numpy as np
import pandas as pd
from pandas import json_normalize
import xtgeo

defaults = {"well_suffix" : ".w", "map_suffix" : ".gri", "delimiter" : "--", "surface_metadata" : "surface_metadata.csv"}


def get_config_item(config,key):
    value = None
    
    pages = config["pages"]  
    
    for page in pages:     
        content = page["content"]
        #print("content")
        #print(content[0])
        #print(content[0].values()) 
        
        try:
            surface_viewer4d = content[0]["SurfaceViewer4D"] 
            value = surface_viewer4d[key]
            return value
        except:
            try:
                value = defaults[key]       
            except:
                pass             
    
    return value
    
    
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
    
    
def get_dates(interval):
    date1 = interval[0:10]
    date2 = interval[11:21]
    
    return date1, date2    


def find_files(folder, suffix) -> io.BytesIO:
    """ Return a sorted list of all files in a folder with a specified suffix  """
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in Path(folder).glob(f"*{suffix}")])
        ).encode()
    )


def load_well(well_path):
    """ Return a well object (xtgeo) for a given file (RMS ascii format) """
    return xtgeo.Well(well_path,mdlogname = "MD")


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
    

def decode_filename(file_path, delimiter):
    """ Create metadata from surface file name """
    surfacepath = str(file_path)
    ind = []
    number = None
    directory = None
    map_type = None
    ensemble = None
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
                    ensemble = "iter-" + number

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

    # print('decode ', realization, ensemble, map_type, name, attribute, dates)
    return directory, realization, ensemble, map_type, name, attribute, dates


def get_map_defaults(configuration, n_maps):
    """ Return default settings for maps (extracted from configuration file) """
    map_defaults = []
    
    settings_file = configuration["settings"]
    settings_file = get_full_path(settings_file)
    settings = read_config(settings_file)

    interval = settings["map_settings"]["default_interval"]

    if not "-" in interval[0:8]:
        date1 = interval[0:4] + "-" + interval[4:6] + "-" + interval[6:8]
        date2 = interval[9:13] + "-" + interval[13:15] + "-" + interval[15:17]
        interval = date1 + "-" + date2

    for i in range(0, n_maps):
        key = "map" + str(i + 1) + "_defaults"
        defaults = configuration[key]
        defaults["interval"] = interval       
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


def get_well_colors(settings):
    """ Return well colors from a configuration """   

    return settings["well_colors"]


def extract_wellbore_metadata(directory):
    """ Return all well metadata found in yaml files in a given folder """
    well_info = []
    interval_info = []

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


def get_mother_wells(metadata_df, slot_name):
    """ Returns a list of possible mother wells - excluding sidetracks"""
    mother_well = slot_name
    mother_wells = [slot_name]

    wellbores = get_wellbores(metadata_df, slot_name) # All wellbores with same slot

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
    """ Get all branches for a well """
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
    slot_name = get_well_metadata(well_info_df, wellbore, "wellbore.slot_name")

    if slot_name:
        mother_wells = get_mother_wells(well_info_df, slot_name)

        for mother_well in mother_wells:
            branches = get_branches(well_info_df, mother_well)

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
    
    
def get_full_path(item):
    path = item 
    full_path = item   

    directory = os.getcwd()       
    
    if path[0:3] == "../":
        path = path[3:]
        full_path = os.path.join(directory,path)  
    elif path[0:2] == "./":
        path = path[2:]                 
        full_path = os.path.join(directory,"configurations",path)  
        
    if not os.path.exists(full_path):
        print("ERROR: Configuration must contain absolute paths for", item)
        full_path = None    
        
    return full_path 
    
    
def main():
    # read_config
    config_file = "./examples/reek_4d.yaml"
    config = read_config(config_file)
    
    settings_file = get_config_item(config, "settings_file")
    print("settings_file", settings_file)
    
    settings_file = get_full_path(settings_file)
    print("full_path", settings_file)
    
    settings = read_config(settings_file)
    csv_file = settings["map_settings"]["colormaps_settings"]
    print("csv_file",csv_file)
    
    csv_file = get_full_path(csv_file)
    print("full_path",csv_file)
    
    
    #get_dates
    interval = "2005-07-01-1993-01-01" 
    date1,date2 = get_dates(interval)
    print("date1,date2")
    print(date1,date2)
    
    
    #get_config_item
    config_file = "configurations/config_template.yaml"
    config = read_config(config_file)
       
    surface_metadata = get_config_item(config, "surface_metadata")
    print("surface_metadata = ", surface_metadata)     
    
    delimiter = get_config_item(config, "delimiter")
    print("delimiter = ", delimiter)  
        
    dummy = get_config_item(config, "dummy")
    print("dummy = ", dummy)  


if __name__ == "__main__":
    main()


    
    

