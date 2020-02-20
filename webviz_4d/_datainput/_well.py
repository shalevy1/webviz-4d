import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_well(well_path):
    return xtgeo.Well(well_path)


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
                "color": "black",
                "positions": positions,
                "tooltip": name,
            }
        ],
    }


def make_multiple_well_layer(wells, name="wells", zmin=0):
    """Make LayeredMap well polyline"""
    well_data = []

    for well in wells:
        well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
        positions = well.dataframe[["X_UTME", "Y_UTMN"]].values

        well_name = well.name.replace("25_11", "25/11")
        well_name = well_name.replace("_", " ")

        well_dict = {
            "type": "polyline",
            "color": "black",
            "positions": positions,
            "tooltip": well_name,
        }

        well_data.append(well_dict)

    return {
        "name": name,
        "checked": False,
        "base_layer": False,
        "data": well_data,
    }


def make_test_layer(bounds, name):
    """Make LayeredMap well polyline"""
    bound_data = []

    bound_dict = {
        "type": "polyline",
        "color": "black",
        "positions": bounds,
        "tooltip": name,
    }

    bound_data.append(bound_dict)

    return {
        "name": name,
        "checked": True,
        "base_layer": False,
        "data": bound_data,
    }
