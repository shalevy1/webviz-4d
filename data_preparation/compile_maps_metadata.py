import os
import glob
import numpy as np
import argparse
from xtgeo import RegularSurface
import pandas as pd
from webviz_4d._datainput import common
from webviz_4d._datainput._metadata import (
    get_metadata,
    compose_filename,
    get_col_values,
    get_all_intervals,
)


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
    parser = argparse.ArgumentParser(description="Compile metadata for all maps")
    parser.add_argument(
        "config_file", help="Enter path to the WebViz-4D configuration file"
    )

    args = parser.parse_args()
    config_file = args.config_file
    config = common.read_config(config_file)
    shared_settings = config["shared_settings"]
    fmu_directory = shared_settings["fmu_directory"]

    surface_metadata = common.get_config_item(config, "surface_metadata")
    metadata_file = os.path.join(fmu_directory, surface_metadata)
    print("Maps metadata file: ", metadata_file)

    if os.path.isfile(metadata_file):
        os.remove(metadata_file)
        print("  - file removed")

    map_suffix = common.get_config_item(config, "map_suffix")
    delimiter = common.get_config_item(config, "delimiter")
    metadata_file = common.get_config_item(config, "surface_metadata")

    metadata = get_metadata(shared_settings, map_suffix, delimiter, metadata_file)
    print(metadata)


if __name__ == "__main__":
    main()
