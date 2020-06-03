import os
import glob
import numpy as np
from xtgeo import RegularSurface
import pandas as pd


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
    main_directory = (
        "/scratch/ert-grane/Petek2019/Petek2019_r001/realization-0/iter-0/share"
    )
    data_dirs = ["observations", "results"]

    csv_file = "/private/ashska/development/webviz-4d/data_preparation/Grane/attribute_maps.csv"

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

    for data_dir in data_dirs:
        surface_path = os.path.join(main_directory, data_dir, "maps/*.gri")
        surface_files = glob.glob(surface_path)
        map_type = data_dir

        for surface_file in surface_files:
            if surface_file[-13] == "_":
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
