import os
import argparse

from webviz_4d._datainput import common
from webviz_4d._datainput._metadata import get_metadata


def main():
    """ Compile metadata for all timelapse maps """
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
