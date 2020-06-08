import os
import glob
import numpy as np
import argparse
from xtgeo import RegularSurface
import pandas as pd
from webviz_4d._datainput import common


def load_surface(surface_path):
    return RegularSurface(surface_path)


def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    z.filled(np.nan)
    return [x, y, z]


def main():
    parser = argparse.ArgumentParser(description="Extract min-/max-values for all maps")
    parser.add_argument("config_file", help="Enter path to the WebViz-4D configuration file")

    args = parser.parse_args()  
    config_file = args.config_file

    sens_run = common.read_config(config_file)["shared_settings"]["scratch_ensembles"]["sens_run"] 
    index = sens_run.index("realization")
    main_directory = sens_run[0:index]
    print(main_directory)

    data_dirs = ["observations", "results"]
    
    config_dir = os.path.dirname(config_file)
    csv_file = os.path.join(config_dir,"attribute_maps.csv")
    print(csv_file)

    map_types = []
    surface_names = []
    attributes = []
    intervals = []
    map_files = []
    min_values = []
    max_values = []

    headers = [
        "map type",
        "name",
        "attribute",
        "interval",
        "minimum value",
        "maximum value",
        "lower_limit",
        "upper_limit",
         "file path"
    ]
    map_df = pd.DataFrame()

    realizations = glob.glob(main_directory + "/realization-*")
    
    for realization in realizations:
        iterations = glob.glob(realization + "/iter-*")
        
        if os.path.isdir(os.path.join(realization,"pred")):
            iterations.append("pred")
         
        print(realization, iterations)
    
        for data_dir in data_dirs:
            for iteration in iterations:
                surface_files = glob.glob(iteration + "/share/" + data_dir + "/maps/*.gri")
                map_type = data_dir

                for surface_file in surface_files:
                    if surface_file[-13] == "_":
                        print(surface_file)
                        surface = load_surface(surface_file)
                        basename = os.path.basename(surface_file)
                        items = basename.split("--")
                        name = items[0]
                        attribute = items[1]
                        interval = items[2][:-4]

                        map_types.append(map_type)
                        surface_names.append(name)
                        attributes.append(attribute)
                        intervals.append(interval)

                        zvalues = get_surface_arr(surface)[2]
                        min_val = np.nanmin(zvalues)
                        max_val = np.nanmax(zvalues)

                        min_values.append(min_val)
                        max_values.append(max_val)
                        map_files.append(surface_file)

    map_df[headers[0]] = map_types
    map_df[headers[1]] = surface_names
    map_df[headers[2]] = attributes
    map_df[headers[3]] = intervals
    map_df[headers[4]] = min_values
    map_df[headers[5]] = max_values
    map_df[headers[6]] = np.nan
    map_df[headers[7]] = np.nan
    map_df[headers[8]] = map_files

    print(map_df)
    map_df.to_csv(csv_file, index=False)
    print("Data saved to ", csv_file)


if __name__ == "__main__":
    main()
