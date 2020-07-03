import os
import glob
import numpy as np
import argparse
from xtgeo import RegularSurface
import pandas as pd
from webviz_4d._datainput import common
from webviz_4d._datainput import _metadata


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
    
    
def get_plot_limits(df, map_type, surface_name, attribute, interval):
    if df is not None:                   
        selected_rows = df.loc[
            (df["map type"] == map_type)
            & (df["name"] == surface_name)
            & (df["attribute"] == attribute)
            & (df["interval"] == interval)
        ]
        if not selected_rows.empty:
            lower_limit = float(selected_rows["lower_limit"])
            upper_limit = float(selected_rows["upper_limit"])
        else:
            lower_limit = np.nan
            upper_limit = np.nan
    else:
        lower_limit = np.nan
        upper_limit = np.nan  
        
    return lower_limit, upper_limit    


def main():
    parser = argparse.ArgumentParser(description="Extract min-/max-values for all maps")
    parser.add_argument(
        "config_file", help="Enter path to the WebViz-4D configuration file"
    )
    parser.add_argument(
        "--mode",
        help="Full=> all maps, Standard (default)=> only one realization and iteration",
        default="Standard",
    )

    args = parser.parse_args()
    config_file = args.config_file
    mode = args.mode

    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]
    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")
    settings_file = common.get_config_item(config, "settings")
    settings_file = common.get_full_path(settings_file)
    settings = common.read_config(settings_file)
    csv_file = settings["map_settings"]["colormaps_settings"]
    csv_file = common.get_full_path(csv_file)
    print(csv_file)

    if csv_file is not None and os.path.isfile(csv_file):
        old_map_df = pd.read_csv(csv_file)
        print(" - file loaded")
        print(old_map_df)
    else:
        old_map_df = None    
        
    csv_file = settings["map_settings"]["colormaps_settings"]    

    surface_metadata = _metadata.get_metadata(
        shared_settings, map_suffix, delimiter, metadata_file
    )
    print(surface_metadata)

    surface_types = ["observations", "results"]
    mapping_dict = {"observations": "observed", "results": "simulated"}

    results_map_dir = mapping_dict["results"] + "_maps"

    if results_map_dir is not None:
        map_settings = shared_settings[results_map_dir]
        realization_names = map_settings["realization_names"]
        iteration_names = map_settings["iteration_names"]
        selected_realization = realization_names[0].replace("*", "0")
        selected_iteration = iteration_names[0].replace("*", "0")

    map_types = []
    surface_names = []
    attributes = []
    intervals = []
    map_files = []
    min_values = []
    max_values = []
    lower_limits = []
    upper_limits = []

    headers = [
        "map type",
        "name",
        "attribute",
        "interval",
        "minimum value",
        "maximum value",
        "lower_limit",
        "upper_limit",
        "file_path",
    ]
    map_df = pd.DataFrame()

    surface_files = surface_metadata["filename"]
    surface_files = surface_files.replace("/.", "/").replace(".yaml", "")

    for index, row in surface_metadata.iterrows():
        # print(row)
        map_type = row["map_type"]
        surface_name = row["data.name"]
        attribute = row["data.content"]
        interval = (
            row["data.time.t2"].replace("-", "")
            + "_"
            + row["data.time.t1"].replace("-", "")
        )
        surface_file = row["filename"]
        surface_file = surface_file.replace("/.", "/").replace(".yaml", "")
        #print(surface_file)
        print(map_type,surface_name,attribute,interval)

        if not mode == "Full":
            realization = row["fmu_id.realization"]
            iteration = row["fmu_id.iteration"]
            #print(realization, iteration)
            
            if map_type == "results":
                if realization == selected_realization and iteration == selected_iteration:
                    surface = load_surface(surface_file)

                    map_types.append(map_type)
                    surface_names.append(surface_name)
                    attributes.append(attribute)
                    intervals.append(interval)

                    zvalues = get_surface_arr(surface)[2]
                    min_val = np.nanmin(zvalues)
                    max_val = np.nanmax(zvalues)

                    min_values.append(min_val)
                    max_values.append(max_val)
                    map_files.append(surface_file)
                    
                    lower_limit, upper_limit = get_plot_limits(old_map_df, map_type, surface_name, attribute, interval)     
                        
                    lower_limits.append(lower_limit)
                    upper_limits.append(upper_limit)        
            else:  
                surface = load_surface(surface_file)

                map_types.append(map_type)
                surface_names.append(surface_name)
                attributes.append(attribute)
                intervals.append(interval)

                zvalues = get_surface_arr(surface)[2]
                min_val = np.nanmin(zvalues)
                max_val = np.nanmax(zvalues)

                min_values.append(min_val)
                max_values.append(max_val)
                map_files.append(surface_file) 
                
                lower_limit, upper_limit = get_plot_limits(old_map_df, map_type, surface_name, attribute, interval) 
                
                lower_limits.append(lower_limit)
                upper_limits.append(upper_limit)         
             
        else:
            surface = load_surface(surface_file)

            map_types.append(map_type)
            surface_names.append(surface_name)
            attributes.append(attribute)
            intervals.append(interval)

            zvalues = get_surface_arr(surface)[2]
            min_val = np.nanmin(zvalues)
            max_val = np.nanmax(zvalues)

            min_values.append(min_val)
            max_values.append(max_val)
            map_files.append(surface_file)               
        
            lower_limit, upper_limit = get_plot_limits(old_map_df, map_type, surface_name, attribute, interval) 
            
            lower_limits.append(lower_limit)
            upper_limits.append(upper_limit)         
            
    map_df[headers[0]] = map_types
    map_df[headers[1]] = surface_names
    map_df[headers[2]] = attributes
    map_df[headers[3]] = intervals
    map_df[headers[4]] = min_values
    map_df[headers[5]] = max_values
    map_df[headers[6]] = lower_limits
    map_df[headers[7]] = upper_limits
    map_df[headers[8]] = map_files

    print(map_df)
    map_df.to_csv(csv_file, index=False)
    print("Data saved to ", csv_file)


if __name__ == "__main__":
    main()
