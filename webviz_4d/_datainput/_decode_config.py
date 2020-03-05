#!/usr/bin/env python3
import os
import glob
import sys
import pandas as pd
from pandas.io.json import json_normalize
import yaml
from pathlib import Path


class ConfigReader:
    def __init__(self, config_file):
        self.config_file = config_file
        self.map_dirs = []
        self.delimiter = "--"
        self.format = ".gri"
        self.default_realizations = []
        self.default_iterations = []
        self.sub_dirs = []
        self.default_data_names = []
        self.default_aggregation_types = []
        self.default_attributes = []
        self.map_labels = []

        self.default_colormap = None
        self.default_colormaps = []
        self.labels_dict = {}
        self.default_interval = None

        try:
            status = os.path.isfile(str(config_file))
            print("Configuration file: ", str(config_file), str(status))
        except:
            sys.exit(Exception)

        with open(config_file, "r") as stream:
            configuration = yaml.safe_load(stream)

        # print(configuration)
        pages = configuration.get("pages")
        contents = pages[1].get("content")
        # print(contents)

        for content in contents:
            surface_viewer = content.get("SurfaceViewer")

            self.field = surface_viewer.get("field")
            self.well_dir = surface_viewer.get("well_dir")

            i = 0

            for key in surface_viewer.keys():
                if key[:3] == "map":
                    self.map_dirs.append(surface_viewer.get(key).get("directory"))

                    self.default_realizations.append(
                        surface_viewer.get(key).get("default_realization")
                    )

                    self.default_iterations.append(
                        surface_viewer.get(key).get("default_iteration")
                    )

                    self.sub_dirs.append(surface_viewer.get(key).get("sub_dir"))
                    self.default_data_names.append(
                        surface_viewer.get(key).get("default_data_name")
                    )

                    self.default_aggregation_types.append(
                        surface_viewer.get(key).get("default_aggregation_type")
                    )

                    self.map_labels.append(surface_viewer.get(key).get("map_label"))

                    self.default_attributes.append(
                        surface_viewer.get(key).get("default_attribute")
                    )

                    try:
                        self.default_delimiter = surface_viewer.get(
                            "SurfaceViewer"
                        ).get("delimiter")
                    except Exception:
                        pass

                    try:
                        self.default_format = surface_viewer.get("SurfaceViewer").get(
                            "format"
                        )
                    except Exception:
                        pass

                    try:
                        self.default_colormap = surface_viewer.get("default_colormap")
                    except Exception:
                        pass

                    try:
                        self.default_colormaps.append(
                            surface_viewer.get(key).get("default_colormap")
                        )
                    except Exception:
                        pass

                    i = i + 1

                try:
                    time1 = surface_viewer.get("default_time1")
                    time2 = surface_viewer.get("default_time2")
                    self.default_interval = str(time1) + "_" + str(time2)

                except Exception:
                    pass

            try:
                date_keys = content.get("SurfaceViewer").get("date_labels").keys()

                for key in date_keys:
                    date = content.get("SurfaceViewer").get("date_labels").get(key)
                    self.labels_dict[str(date)] = key
            except Exception:
                pass

    def get_default_map(self, map_ind):
        ind = map_ind - 1
        map_dir = self.map_dirs[ind]
        delimiter = self.delimiter
        format = self.format
        sub_dir = self.sub_dirs[ind]
        data_name = self.default_data_names[ind]
        interval = self.default_interval

        if self.default_aggregation_types[ind]:
            aggregation_type = delimiter + self.default_aggregation_types[ind]
        else:
            aggregation_type = ""

        try:
            number = int(self.default_realizations[ind])
            realization = "realization-" + str(number)
        except:
            realization = ""

        try:
            number = int(self.default_iterations[ind])
            iteration = "iter-" + str(number)
        except:
            iteration = ""

        attribute = self.default_attributes[ind]

        file_name = (
            data_name
            + delimiter
            + attribute
            + delimiter
            + interval
            + aggregation_type
            + format
        )

        return os.path.join(map_dir, realization, iteration, sub_dir, file_name)


def main():
    config = ConfigReader("./examples/reek_example.yaml")
    print(config.field)
    print(config.get_default_map(1))
    print(config.get_default_map(2))
    print(config.get_default_map(3))

    if os.path.exists(config.get_default_map(1)):
        print("Filepath OK")

    config = ConfigReader(".//fields/js_config_new.yaml")
    print(config.field)
    print(config.get_default_map(1))
    print(config.get_default_map(2))
    print(config.get_default_map(3))
    if os.path.exists(config.get_default_map(1)):
        print("Filepath OK")


if __name__ == "__main__":
    main()
