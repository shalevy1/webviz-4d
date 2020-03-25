import io
import glob
import xtgeo
import json
import pandas as pd
import yaml
from pandas.io.json import json_normalize
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(well_path):
    return xtgeo.Well(well_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layer(well, name="well", zmin=0):
    """Make LayeredMap well polyline"""
    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
    positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": name,
        "checked": True,
        "base_layer": False,
        "data": [
            {
                "type": "polyline",
                "color": "red",
                "positions": positions,
                "tooltip": name,
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layers(wellfiles, zmin=0, max_points=100, color="black", checked=True):
    """Make layeredmap wells layer"""
    data = []
    for wellfile in wellfiles:
        try:
            well = load_well(wellfile)
        except ValueError:
            continue
        well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
        while len(well.dataframe.values) > max_points:
            well.downsample()
        positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
        data.append(
            {
                "type": "polyline",
                "color": color,
                "positions": positions,
                "tooltip": well.name,
            }
        )
    return {"name": "Wells", "checked": checked, "base_layer": False, "data": data}


def find_files(folder, suffix) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )


def extract_well_metadata(directory):
    well_info = []
    interval_info = []

    print(str(directory))
    yaml_files = glob.glob(str(directory) + "/**/.*.yaml", recursive=True)

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


def load_all_wells(wellfolder, wellsuffix):
    all_wells_list = []

    wellfiles = (
        json.load(find_files(wellfolder, wellsuffix))
        if wellfolder is not None
        else None
    )

    print("Loading wells ...")
    for wellfile in wellfiles:
        # print(wellfile)
        try:
            well = load_well(wellfile)
        except ValueError:
            continue
        well.dataframe = well.dataframe[["X_UTME", "Y_UTMN", "Z_TVDSS", "MD"]]
        well.dataframe["WELLBORE_NAME"] = well.name
        all_wells_list.append(well.dataframe)

    all_wells_df = pd.concat(all_wells_list)

    well_info, interval_df = extract_well_metadata(wellfolder)

    return (all_wells_df, well_info, interval_df)


def get_position_data(well_dataframe, md_start):
    well_dataframe = well_dataframe[well_dataframe["MD"] > md_start]
    positions = well_dataframe[["X_UTME", "Y_UTMN"]].values

    return positions


def get_well_polyline(
    wellbore, well_dataframe, well_type, fluids, md_start, selection, colors
):
    color = "black"
    if colors:
        color = colors["default"]

    if not well_type == "planned":
        wellbore = wellbore.replace("_", "/", 1)
        wellbore = wellbore.replace("_", " ")

    tooltip = wellbore + " : " + well_type

    status = False

    if fluids:
        tooltip = tooltip + " (" + fluids + ")"

    if selection:
        if (
            ("reservoir" in selection or "completed" in selection)
            and fluids
            and md_start > 0
        ):
            positions = get_position_data(well_dataframe, md_start)
            status = True

        elif well_type == selection and fluids and md_start > 0:
            ind = fluids.find(",")

            if ind > 0:
                fluid = "mixed"
            else:
                fluid = fluids

            if colors:
                color = colors[fluid + "_" + selection]

            positions = get_position_data(well_dataframe, md_start)
            status = True

        elif selection == "planned" and well_type == selection:
            if colors:
                color = colors[selection]

            positions = get_position_data(well_dataframe, md_start)
            status = True
    else:
        positions = get_position_data(well_dataframe, md_start)
        status = True

    if status:
        return {
            "type": "polyline",
            "color": color,
            "positions": positions,
            "tooltip": tooltip,
        }
    else:
        return None


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_new_well_layer(
    wells_df,
    metadata_df,
    interval_df,
    colors=None,
    selection=None,
    label="Drilled wells",
):
    """Make layeredmap wells layer"""
    data = []
    if not colors:
        color = "black"

    wellbores = wells_df["WELLBORE_NAME"].values
    list_set = set(wellbores)
    # convert the set to the list
    unique_wellbores = list(list_set)
    # unique_wellbores = [
    #    "25_11-G-38_AY2T3",
    #    "25_11-G-38_AY3",
    #    "25_11-G-4_T2",
    #    "25_11-G-20_A",
    #    "25_11-G-24_A",
    #    "25_11-G-32",
    #   "25_11-G-36",
    #    "25_11-G-14",
    #    "25_11-G-23_A",
    # ]

    pd.set_option("display.max_rows", None)

    print("Number of wellbores: ", len(unique_wellbores))

    for wellbore in unique_wellbores:
        # print('wellbore ',wellbore)
        md_start = 0

        well_dataframe = wells_df[wells_df["WELLBORE_NAME"] == wellbore]

        if selection:
            uwi = "NO " + wellbore.replace("_", "/", 1)
            uwi = uwi.replace("_", " ")
            well_intervals = interval_df[interval_df["interval.wellbore"] == uwi]
            md_tops = well_intervals["interval.mdTop"].values

            if len(md_tops) > 0:
                md_start = min(md_tops)

        well_metadata = metadata_df[metadata_df["wellbore.rms_name"] == wellbore]

        well_type = well_metadata["wellbore.type"].values[0]
        fluids = well_metadata["wellbore.fluids"].values[0]

        polyline_data = get_well_polyline(
            wellbore, well_dataframe, well_type, fluids, md_start, selection, colors
        )

        if polyline_data:
            data.append(polyline_data)

    return {"name": label, "checked": False, "base_layer": False, "data": data}
