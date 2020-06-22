#!/usr/bin/env python3
import os
import yaml
import glob
import xtgeo

from pathlib import Path


def load_well(well_path):
    return xtgeo.Well(well_path, mdlogname="MD")


def load_surface(surface_path):
    return xtgeo.RegularSurface(surface_path)


def main():
    well_dir = "/project/grane/resmod/hstruct/2019/users/ashska/r001/r001_20200106/share/coviz/planned_wells/"
    well_suffix = "*.w"
    surface_path = "/scratch/ert-grane/Petek2019/Petek2019_r001/realization-0/iter-0/share/results/maps/toplowerheimdal--depthsurface.gri"

    surface = load_surface(surface_path)

    wellfiles = glob.glob(well_dir + well_suffix)

    for wellfile in wellfiles:
        well = load_well(wellfile)
        print(well.name)

        points = well.get_surface_picks(surface)

        if hasattr(points, "dataframe"):
            print(points.dataframe)
            md_value = points.dataframe["MD"].values[0]

            well_pick_md = md_value
            pick_name = os.path.basename(surface_path)
            well_pick = {"name": pick_name, "depth": well_pick_md}

            print(well_pick)

            yaml_file = (
                os.path.dirname(wellfile) + "/." + os.path.basename(wellfile) + ".yaml"
            )
            print(yaml_file)
            yaml.dump(well_pick, yaml_file, default_flow_style=False)

            print("Metadata har been added to " + yaml_file)


if __name__ == "__main__":
    main()
