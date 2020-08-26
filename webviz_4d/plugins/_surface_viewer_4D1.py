from pathlib import Path
import json
import io
import os
from timeit import default_timer as timer
import numpy as np
import pandas as pd
import xtgeo
import dash
import pickle
import glob

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap

from webviz_4d._datainput.fmu_input import get_realizations, find_surfaces
from webviz_4d._datainput._surface import make_surface_layer, load_surface
from webviz_4d._datainput.common import (
    get_full_path,
    read_config,
    get_map_defaults,
    get_well_colors,
    get_update_dates,
    get_plot_label,
)
from webviz_4d._datainput.well import (
    load_all_wells,
    make_new_well_layer,
    filter_well_layer,
)
from webviz_4d._private_plugins.surface_selector import SurfaceSelector
from webviz_4d._private_plugins.selector import Selector
from webviz_4d._datainput._colormaps import load_custom_colormaps

from webviz_4d._datainput._metadata import (
    get_metadata,
    compose_filename,
    get_col_values,
    get_all_intervals,
    create_map_defaults,
    sort_realizations,
)


class SurfaceViewer4D1(WebvizPluginABC):
    """### SurfaceViewer4D """

    def __init__(
        self,
        app,
        wellfolder: Path = None,
        production_data: Path = None,
        map1_defaults: dict = None,
        well_suffix: str = ".w",
        map_suffix: str = ".gri",
        default_interval: str = None,
        settings: Path = None,
        delimiter: str = "--",
        surface_metadata: str = "surface_metadata.csv",
    ):

        super().__init__()
        self.shared_settings = app.webviz_settings["shared_settings"]
        self.fmu_directory = self.shared_settings["fmu_directory"]

        self.map_suffix = map_suffix
        self.delimiter = delimiter
        self.wellfolder = wellfolder
        self.observations = "observations"
        self.simulations = "results"
        self.config = None
        self.attribute_settings = {}
        self.surface_metadata = None
        self.well_base_layers = None

        #print("default_interval", default_interval)

        self.fmu_info = self.fmu_directory
        self.well_update = ""
        self.production_update = ""

        self.number_of_maps = 1

        self.metadata = get_metadata(
            self.shared_settings, map_suffix, delimiter, surface_metadata
        )
        #print("Maps metadata")
        #print(self.metadata)

        self.intervals, incremental = get_all_intervals(self.metadata, "reverse")
        #print(self.intervals)

        if default_interval is None:
            default_interval = self.intervals[-1]

        self.surface_layer = None

        if settings:
            self.configuration = settings
            self.config = read_config(self.configuration)
            # print(self.config)

            try:
                self.attribute_settings = self.config["map_settings"][
                    "attribute_settings"
                ]
            except:
                pass

            try:
                colormaps_folder = self.config["map_settings"]["colormaps_folder"]

                if colormaps_folder:
                    colormaps_folder = get_full_path(colormaps_folder)

                    print("Reading custom colormaps from:", colormaps_folder)
                    load_custom_colormaps(colormaps_folder)
            except:
                pass

            try:
                attribute_maps_file = self.config["map_settings"]["colormaps_settings"]
                attribute_maps_file = get_full_path(attribute_maps_file)
                self.surface_metadata = pd.read_csv(attribute_maps_file)
                print("Colormaps settings loaded from file", attribute_maps_file)
                #print(self.surface_metadata)
            except:
                pass

        self.map_defaults = []

        if map1_defaults is not None:
            map1_defaults["interval"] = default_interval
            self.map_defaults.append(map1_defaults)

        print("Default interval", default_interval)
        #print("Map 1 defaults:")
        #print(map1_defaults)


        if map1_defaults is None:
            self.map_defaults = create_map_defaults(
                self.metadata, default_interval, self.observations, self.simulations
            )
        else:
            self.map_defaults = []
            self.map_defaults.append(map1_defaults)

        #print("map_defaults", self.map_defaults)
        self.selected_interval = default_interval

        self.selected_name = None
        self.selected_attribute = None
        self.selected_ensemble = None
        self.selected_realization = None
        self.wellsuffix = ".w"

        self.well_base_layers = []
        self.colors = get_well_colors(self.config)

        if wellfolder and os.path.isdir(wellfolder):
            self.wellfolder = wellfolder
            update_dates = get_update_dates(wellfolder)
            self.well_update = update_dates["well_update_date"]
            self.production_update = update_dates["production_last_date"]

            (
                self.drilled_well_df,
                self.drilled_well_info,
                self.interval_df,
            ) = load_all_wells(wellfolder, self.wellsuffix)

            if self.drilled_well_df is not None:

                self.well_base_layers.append(
                    make_new_well_layer(
                        self.selected_interval,
                        self.drilled_well_df,
                        self.drilled_well_info,
                    )
                )

                self.well_base_layers.append(
                    make_new_well_layer(
                        self.selected_interval,
                        self.drilled_well_df,
                        self.drilled_well_info,
                        colors=self.colors,
                        selection="reservoir_section",
                        label="Reservoir sections",
                    )
                )

            planned_wells_dir = [f.path for f in os.scandir(wellfolder) if f.is_dir()]

            for folder in planned_wells_dir:
                planned_well_df, planned_well_info, dummy_df = load_all_wells(
                    folder, self.wellsuffix
                )

                if planned_well_df is not None:
                    self.well_base_layers.append(
                        make_new_well_layer(
                            self.selected_interval,
                            planned_well_df,
                            planned_well_info,
                            self.colors,
                            selection="planned",
                            label=os.path.basename(folder),
                        )
                    )
        elif wellfolder and not os.path.isdir(wellfolder):
            print("ERROR: Folder", wellfolder, "doesn't exist. No wells loaded")

        self.selector = SurfaceSelector(
            app, self.metadata, self.intervals, self.map_defaults[0]
        )

        self.set_callbacks(app)

    @property
    def ensembles(self):
        try:
            return get_col_values(self.metadata, "fmu_id.ensemble")
        except:
            return get_col_values(self.metadata, "fmu_id.iteration")   

    def realizations(self, ensemble):
        sorted_realizations = sort_realizations(
            get_col_values(self.metadata, "fmu_id.realization")
        )
        return sorted_realizations

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": ("Dashboard to compare surfaces from a FMU ensemble. "),
            },
            {
                "id": self.uuid("settings-view1"),
                "content": ("Settings for the first map view"),
            },
        ]

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def ensemble_layout(
        self,
        map_number,
        ensemble_id,
        ens_prev_id,
        ens_next_id,
        real_id,
        real_prev_id,
        real_next_id,
    ):
        return wcc.FlexBox(
            children=[
                html.Div(
                    [
                        html.Label(
                            "Ensemble / Iteration",
                            style={"fontSize": 15, "fontWeight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.map_defaults[map_number]["ensemble"],
                                    id=ensemble_id,
                                    clearable=False,
                                    style={"fontSize": 15, "fontWeight": "normal",},
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=ens_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=ens_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label(
                            "Realization / Statistic",
                            style={"fontSize": 15, "fontWeight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.map_defaults[map_number]["realization"],
                                    id=real_id,
                                    clearable=False,
                                    style={"fontSize": 15, "fontWeight": "normal"},
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_prev_id,
                                    children="⬅",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "2rem",
                                        "paddingLeft": "5px",
                                        "paddingRight": "5px",
                                    },
                                    id=real_next_id,
                                    children="➡",
                                ),
                            ],
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            id=self.uuid("layout"),
            children=[
                html.H3("WebViz-4D " + self.fmu_info),
                html.H6("Well data update: " + self.well_update),
                html.H6("Production data update: " + self.production_update),
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            id=self.uuid("settings-view1"),
                            style={"margin": "10px", "flex": 4},
                            children=[
                                self.selector.layout,
                                self.ensemble_layout(
                                    0,
                                    ensemble_id=self.uuid("ensemble"),
                                    ens_prev_id=self.uuid("ensemble-prev"),
                                    ens_next_id=self.uuid("ensemble-next"),
                                    real_id=self.uuid("realization"),
                                    real_prev_id=self.uuid("realization-prev"),
                                    real_next_id=self.uuid("realization-next"),
                                ),
                            ],
                        ),
                    ]        
                ),
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                html.Div(
                                    id=self.uuid("heading1"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 20,
                                        "fontWeight": "bold",
                                    },
                                ),
                                html.Div(
                                    id=self.uuid("sim_info1"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 15,
                                        "fontWeight": "bold",
                                    },
                                ),
                                LayeredMap(
                                    #sync_ids=[self.uuid("map2"), self.uuid("map3")],
                                    id=self.uuid("map"),
                                    height=1000,
                                    layers=[],
                                    hillShading=False,
                                ),
                                html.Div(
                                    id=self.uuid("interval-label1"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 20,
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                        ),
                        dcc.Store(
                            id=self.uuid("attribute-settings"),
                            data=json.dumps(self.attribute_settings),
                        ),
                    ],
                ),
            ],
        )

    def get_real_runpath(self, data, ensemble, real, map_type):

        filepath = compose_filename(
            self.shared_settings,
            real,
            ensemble,
            map_type,
            data["name"],
            data["attr"],
            data["date"],
            self.delimiter,
        )

        # print('filepath: ',filepath)
        return filepath

    def get_heading(self, map_ind, observation_type):
        if self.map_defaults[map_ind]["map_type"] == observation_type:
            txt = "Observed map: "
            info = "-"
        else:
            txt = "Simulated map: "
            info = (
                self.selected_ensemble
                + " "
                + self.selected_realization
            )

        heading = (
            txt
            + self.selected_attribute
            + " ("
            + self.selected_name
            + ")"
        )

        sim_info = info
        label = get_plot_label(self.config, self.selected_interval)

        return heading, sim_info, label

    def make_map(self, data, ensemble, real, attribute_settings, map_idx):
        # print(data, ensemble, real, attribute_settings, map_idx)
        start = timer()
        data = json.loads(data)
        attribute_settings = json.loads(attribute_settings)
        map_type = self.map_defaults[map_idx]["map_type"]

        surface_file = self.get_real_runpath(data, ensemble, real, map_type)

        if os.path.isfile(surface_file):
            surface = load_surface(surface_file)
            # print(surface)

            #print("self.surface_metadata")
            #print(self.surface_metadata)
            if self.surface_metadata is not None:
                m_data = self.surface_metadata.loc[
                    self.surface_metadata["map type"] == map_type
                ]

                a_data = m_data.loc[m_data["attribute"] == data["attr"]]

                interval = (
                    data["date"][0:4]
                    + data["date"][5:7]
                    + data["date"][8:10]
                    + "_"
                    + data["date"][11:15]
                    + data["date"][16:18]
                    + data["date"][19:21]
                )
                i_data = a_data.loc[a_data["interval"] == interval]
                metadata = i_data[["lower_limit", "upper_limit"]]

                #print("interval", interval)
                #print(a_data)
                #print(i_data)
            else:
                metadata = None
            #print("metadata", metadata)

            surface_layers = [
                make_surface_layer(
                    surface,
                    name=data["attr"],
                    color=attribute_settings.get(data["attr"], {}).get(
                        "color", "inferno"
                    ),
                    min_val=attribute_settings.get(data["attr"], {}).get("min", None),
                    max_val=attribute_settings.get(data["attr"], {}).get("max", None),
                    unit=attribute_settings.get(data["attr"], {}).get("unit", ""),
                    hillshading=False,
                    min_max_df=metadata,
                )
            ]

            # print(f"make surface layer {timer()-start}")
            self.selected_interval = data["date"]

            if self.well_base_layers:
                for well_layer in self.well_base_layers:
                    # print(well_layer["name"])
                    surface_layers.append(well_layer)

                try:
                    interval_file = os.path.join(
                        self.wellfolder,
                        "production_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    interval_layer = pickle.load(open(interval_file, "rb"))
                    surface_layers.append(interval_layer)
                    
                    #filtered_well_layer = filter_well_layer(interval_layer,84)
                    #surface_layers.append(filtered_well_layer)
                    
                    prod_start_file = os.path.join(
                        self.wellfolder,
                        "production_start_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    prod_start_layer = pickle.load(open(prod_start_file, "rb"))
                    surface_layers.append(prod_start_layer)
                    
                    prod_completed_file = os.path.join(
                        self.wellfolder,
                        "production_completed_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    prod_completed_layer = pickle.load(open(prod_completed_file, "rb"))
                    surface_layers.append(prod_completed_layer)

                    interval_file = os.path.join(
                        self.wellfolder,
                        "injection_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    interval_layer = pickle.load(open(interval_file, "rb"))
                    surface_layers.append(interval_layer)
                    
                    inject_start_file = os.path.join(
                        self.wellfolder,
                        "injection_start_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    inject_start_layer = pickle.load(open(inject_start_file, "rb"))
                    surface_layers.append(inject_start_layer)
                    
                    inject_completed_file = os.path.join(
                        self.wellfolder,
                        "injection_completed_well_layer_"
                        + self.selected_interval
                        + ".pkl",
                    )
                    inject_completed_layer = pickle.load(open(inject_completed_file, "rb"))
                    surface_layers.append(inject_completed_layer)
                    
                    search_txt = os.path.join(
                        self.wellfolder,
                        "active_well_layer_*")   
                    search = glob.glob(search_txt)  
                    active_file = search[0]   
                    active_layer = pickle.load(open(active_file, "rb"))
                    surface_layers.append(active_layer)
                except Exception as e:
                    if hasattr(e, 'message'):
                        print(e.message)
                    else:
                        print(e)

            self.selected_name = data["name"]
            self.selected_attribute = data["attr"]
            self.selected_ensemble = ensemble
            self.selected_realization = real

            heading, sim_info, label = self.get_heading(map_idx, self.observations)
        else:
            print("WARNING: File", surface_file, "doesn't exist")
            heading = "Selected map doesn't exist"
            sim_info = "-"
            surface_layers = []
            label = "-"

        return (
            heading,
            sim_info,
            surface_layers,
            label,
        )

    def set_callbacks(self, app):
        # First map
        @app.callback(
            [
                Output(self.uuid("heading1"), "children"),
                Output(self.uuid("sim_info1"), "children"),
                Output(self.uuid("map"), "layers"),
                Output(self.uuid("interval-label1"), "children"),
            ],
            [
                Input(self.selector.storage_id, "children"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realization"), "value"),
                Input(self.uuid("attribute-settings"), "data"),
            ],
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_base_layer(
            data, ensemble, real, attribute_settings,
        ):

            return self.make_map(data, ensemble, real, attribute_settings, 0)


        def _update_from_btn(_n_prev, _n_next, current_value, options):
            """Updates dropdown value if previous/next btn is clicked"""
            options = [opt["value"] for opt in options]
            ctx = dash.callback_context.triggered
            if not ctx or current_value is None:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if "-prev" in callback:
                return prev_value(current_value, options)
            if "-next" in callback:
                return next_value(current_value, options)
            return current_value

        for btn_name in [
            "ensemble",
            "realization",
            "ensemble2",
            "realization2",
            "ensemble3",
            "realization3",
        ]:
            app.callback(
                Output(self.uuid(f"{btn_name}"), "value"),
                [
                    Input(self.uuid(f"{btn_name}-prev"), "n_clicks"),
                    Input(self.uuid(f"{btn_name}-next"), "n_clicks"),
                ],
                [
                    State(self.uuid(f"{btn_name}"), "value"),
                    State(self.uuid(f"{btn_name}"), "options"),
                ],
            )(_update_from_btn)

    def add_webvizstore(self):
        store_functions = [
            (
                find_surfaces,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "suffix": "*.gri",
                        "delimiter": "--",
                    }
                ],
            )
        ]

        filenames = []
        # Generate all file names
        for attr, values in self.surfaceconfig.items():
            for name in values["names"]:
                for date in values["dates"]:
                    filename = f"{name}--{attr}"
                    if date is not None:
                        filename += f"--{date}"
                    filename += f".gri"
                    filenames.append(filename)

        # Copy all realization files
        for runpath in self.ens_df["RUNPATH"].unique():
            for filename in filenames:
                path = Path(runpath) / "share" / "results" / "maps" / filename
                if path.exists():
                    store_functions.append((get_path, [{"path": str(path)}]))

        # Calculate and store statistics
        for _, ens_df in self.ens_df.groupby("ENSEMBLE"):
            runpaths = list(ens_df["RUNPATH"].unique())
            for filename in filenames:
                paths = [
                    str(Path(runpath) / "share" / "results" / "maps" / filename)
                    for runpath in runpaths
                ]
                for statistic in ["Mean", "StdDev", "Min", "Max"]:
                    store_functions.append(
                        (save_surface, [{"fns": paths, "statistic": statistic}])
                    )
        if self.wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self.wellfolder, "suffix": self.wellsuffix}])
            )
        if self.wellfiles is not None:
            store_functions.extend(
                [(get_path, [{"path": fn}]) for fn in self.wellfiles]
            )
        store_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        return store_functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface(fns, statistic):
    return surface_from_json(json.load(save_surface(fns, statistic)))


def surface_to_json(surface):
    return json.dumps(
        {
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xori": surface.xori,
            "yori": surface.yori,
            "rotation": surface.rotation,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
            "values": surface.values.copy().filled(np.nan).tolist(),
        }
    )


def surface_from_json(surfaceobj):
    return xtgeo.RegularSurface(**surfaceobj)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    return xtgeo.surface.surfaces.Surfaces(fns)


@webvizstore
def get_path(path) -> Path:
    return Path(path)


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]

    except ValueError:
        return current_value


def surfacedf_to_dict(df):
    return {
        attr: {
            "names": list(dframe["name"].unique()),
            "dates": list(dframe["date"].unique())
            if "date" in dframe.columns
            else None,
        }
        for attr, dframe in df.groupby("attribute")
    }


@webvizstore
def find_files(folder, suffix) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )


def make_fmu_filename(data):
    filename = f"{data['name']}--{data['attr']}"
    if data["date"] is not None:
        filename += f"--{data['date']}"
    return filename
