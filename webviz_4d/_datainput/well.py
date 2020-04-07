import io
import glob
import xtgeo
import json
import pandas as pd
import yaml
import os
from pandas.io.json import json_normalize
from webviz_config.common_cache import CACHE
from pathlib import Path


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(well_path):
    return xtgeo.Well(well_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_well_layers(wellfiles, zmin=0, max_points=100, color="black", checked=True):
    """Make layeredmap wells layer"""
    data = []
    for wellfile in wellfiles:
        try:
            well = load_well(wellfile, mdlogname="MD")
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
            sorted([str(filename) for filename in Path(folder).glob(f"*{suffix}")])
        ).encode()
    )


def extract_well_metadata(directory):
    well_info = []
    interval_info = []

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

    print("Loading wells from " + str(wellfolder) + " ...")
    for wellfile in wellfiles:
        try:
            well = load_well(wellfile)
        except ValueError:
            continue
        well.dataframe = well.dataframe[["X_UTME", "Y_UTMN", "Z_TVDSS", "MD"]]
        well.dataframe["WELLBORE_NAME"] = well.name
        all_wells_list.append(well.dataframe)

    all_wells_df = pd.concat(all_wells_list)

    well_info, interval_df = extract_well_metadata(wellfolder)
    metadata_file = os.path.join(wellfolder,"wellbore_info.csv")
    metadata = pd.read_csv(metadata_file)
    #print('load_all_wells ',metadata)

    return (all_wells_df, metadata, interval_df)


def get_position_data(well_dataframe, md_start):
    well_dataframe = well_dataframe[well_dataframe["MD"] > md_start]
    positions = well_dataframe[["X_UTME", "Y_UTMN"]].values

    return positions


def get_well_polyline(
    wellbore, short_name, well_dataframe, well_type, info, md_start, selection, colors
):
    color = "black"
    if colors:
        color = colors["default"]

    # if not well_type == "planned":
    #    wellbore = wellbore.replace("_", "/", 1)
    #    wellbore = wellbore.replace("_", " ")
    #print(short_name, well_type)
    tooltip = str(short_name) + " : " + well_type

    status = False

    if info == "not applicable":
        info = None    

    if info and not pd.isna(info):
        tooltip = tooltip + " (" + info + ")"

    # print(tooltip)

    if selection:
        if (
            ("reservoir" in selection or "completed" in selection)
            and not pd.isna(info)
            and md_start > 0
        ):
            positions = get_position_data(well_dataframe, md_start)
            status = True
            
        elif selection == "planned" and well_type == selection:
            if colors:
                color = colors[selection]

            positions = get_position_data(well_dataframe, md_start)
            status = True    

        elif well_type == selection and not pd.isna(info) and md_start > 0:
            ind = info.find(",")

            if ind > 0:
                info = "mixed"

            if colors:
                color = colors[info + "_" + selection]

            positions = get_position_data(well_dataframe, md_start)
            status = True
            
        elif pd.isna(info):
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
    interval,
    wells_df,
    metadata_df,
    interval_df,
    colors=None,
    selection=None,
    label="Drilled wells",
):
    """Make layeredmap wells layer"""
    from timeit import default_timer as timer
    start = timer()
    data = []
    if not colors:
        color = "black"

    wellbores = wells_df["WELLBORE_NAME"].values
    list_set = set(wellbores)
    # convert the set to the list
    unique_wellbores = list(list_set)
    #unique_wellbores = [
    #   "25_11-G-38_AY2T3",
    #   "25_11-G-38_AY3",
    #   "25_11-G-4_T2",
    #   "25_11-G-20_A",
    #   "25_11-G-24_A",
    #   "25_11-G-32",
    #   "25_11-G-36",
    #   "25_11-G-14",
    #   "25_11-G-23_A",
    #]

    pd.set_option("display.max_rows", None)

    #print("Number of wellbores: ", len(unique_wellbores))
    #print(selection)

    for wellbore in unique_wellbores:
        # print('wellbore ',wellbore)
        md_start = 0
        polyline_data = None

        well_dataframe = wells_df[wells_df["WELLBORE_NAME"] == wellbore]
        well_metadata = metadata_df[metadata_df["wellbore.rms_name"] == wellbore]
        #print(well_metadata)
        
        md_top_res = well_metadata["wellbore.pick_md"].values
        if selection and len(md_top_res) > 0:
            md_start = min(md_top_res)
        
        short_name = well_metadata["wellbore.short_name"].values
        if short_name:
            short_name = short_name[0]
        
        well_type = well_metadata["wellbore.type"].values
        if well_type:
            well_type = well_type[0]
        
        if well_type == "planned":
            info = well_metadata["wellbore.list_name"].values
            start_date = None
            stop_date = None
        else:
            info = well_metadata["wellbore.fluids"].values
            start_date = well_metadata["Start date"].values
            if start_date :
                start_date = start_date[0]
                    
            stop_date = well_metadata["Stop date"].values
            if stop_date :
                stop_date = stop_date[0]
            
        if info:
            info = info[0] 
            
        plot = False
        if selection and well_type == selection and (selection == "production" or selection == "injection"):                   
            if interval and not pd.isna(start_date) and not pd.isna(stop_date):  
                interval_start = interval[0:4] + interval[5:7] + interval[8:10]
                interval_stop = interval[11:15] + interval[16:18] + interval[19:21]
                           
                if interval_start >= start_date and interval_start <= stop_date:
                    plot = True
                   
                elif interval_stop >= start_date and interval_stop <= stop_date: 
                    plot = True  
                    
                if plot:    
                           
                    polyline_data = get_well_polyline(
                            wellbore,
                            short_name,
                            well_dataframe,
                            well_type,
                            info,
                            md_start,
                            selection,
                            colors,
                        )       
        elif selection == "reservoir_section" or selection == "planned": 
            polyline_data = get_well_polyline(
                    wellbore,
                    short_name,
                    well_dataframe,
                    well_type,
                    info,
                    md_start,
                    selection,
                    colors,
                )        
        elif not selection:
            polyline_data = get_well_polyline(
                    wellbore,
                    short_name,
                    well_dataframe,
                    well_type,
                    info,
                    md_start,
                    selection,
                    colors,
                )
                  
        if polyline_data:
            data.append(polyline_data)
    print(f"Well function{timer()-start}")
    return {"name": label, "checked": False, "base_layer": False, "data": data}
