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
from webviz_4d._datainput.surface import make_surface_layer, load_surface
from webviz_4d._datainput.well import (
    load_all_wells,
    make_new_well_layer,
)
from webviz_4d._private_plugins.surface_selector import SurfaceSelector

from webviz_4d._datainput._colormaps import load_custom_colormaps

from webviz_4d._datainput._metadata import (
    get_metadata,
    compose_filename,
    get_col_values,
    get_all_intervals,
    get_map_defaults,
    get_well_colors,
    read_config,
    sort_realizations,
    get_plot_label,
)


class SurfaceViewer4D(WebvizPluginABC):
    """### SurfaceViewerFMU
A plugin to covisualize surfaces from an ensemble.
There are 3 separate map views. 2 views can be set independently, while
the 3rd view displays the resulting map by combining the other maps e.g.
by taking the difference or summing the values.
There is flexibility in which combinations of surfaces that are displayed
and calculated, such that surfaces can e.g. be compared across ensembles.
The available maps are gathered from the `share/results/maps/` folder
for each realization. Statistical calculations across the ensemble(s) are
done on the fly. If the ensemble or surfaces have a large size it is recommended
to run webviz in `portable` mode so that the statistical surfaces are pre-calculated
and available for instant viewing.
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `attributes`: List of surface attributes to include, if not given
                all surface attributes will be included.
* `attribute_settings`: Dictionary with setting for each attribute.
                Available settings are 'min' and 'max' to truncate colorscale,
                'color' to set the colormap (default is viridis) and `unit` as
                displayed label.
* `wellfolder`: Folder with RMS wells
* `wellsuffix`: File suffix for wells in well folder.
"""

    def __init__(
        self,
        app,
        ensembles: list,
        attributes: list = None,
        attribute_settings: dict = None,
        wellfolder: Path = None,
        configuration: Path = None,
    ):

        super().__init__()
        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.delimiter = "--"
        self.observation = "observations"
        self.wellfolder = wellfolder
        self.attribute_settings = attribute_settings if attribute_settings else {}

        # Find FMU directory
        keys = list(self.ens_paths.keys())
        path = self.ens_paths[keys[0]]
        # print(path)

        self.directory = os.path.dirname(path).replace("*", "0")
        self.fmu_info = os.path.dirname(self.directory)
        # print(directory)

        self.number_of_maps = 3
        self.configuration = configuration
        self.config = read_config(self.configuration)
        default_interval = self.config["map_settings"]["default_interval"]
        self.selected_intervals = [default_interval, default_interval, default_interval]

        # print(self.config)
        self.map_defaults = get_map_defaults(self.config, self.number_of_maps)
        colormaps_folder = self.config["map_settings"]["colormaps_folder"]
        
        load_custom_colormaps(colormaps_folder)        

        # print('self.map_defaults ',self.map_defaults)

        self.metadata, self.dates = get_metadata(
            self.directory, self.map_defaults[0], self.delimiter
        )
        # print(self.metadata)
        # print("")

        self.intervals = get_all_intervals(self.metadata)
        # print("self.intervals ", self.intervals)
        
        self.surface_metadata = pd.read_csv(os.path.join(self.wellfolder,"attribute_maps.csv"))
        print(self.surface_metadata)

        self.selected_names = [None, None, None]
        self.selected_attributes = [None, None, None]
        self.selected_ensembles = [None, None, None]
        self.selected_realizations = [None, None, None]
        self.wellsuffix = ".w"

        self.drilled_well_df, self.drilled_well_info, self.interval_df = load_all_wells(
            wellfolder, self.wellsuffix
        )
        planned_wells_dir = [f.path for f in os.scandir(wellfolder) if f.is_dir()]

        self.colors = get_well_colors(self.config)

        self.well_base_layers = []
        self.well_base_layers.append(
            make_new_well_layer(
                self.selected_intervals[0],
                self.drilled_well_df,
                self.drilled_well_info,
                self.interval_df,
            )
        )

        self.well_base_layers.append(
            make_new_well_layer(
                self.selected_intervals[0],
                self.drilled_well_df,
                self.drilled_well_info,
                self.interval_df,
                self.colors,
                selection="reservoir_section",
                label="Reservoir sections",
            )
        )

        for folder in planned_wells_dir:
            planned_well_df, planned_well_info, dummy_df = load_all_wells(
                folder, self.wellsuffix
            )
            self.well_base_layers.append(
                make_new_well_layer(
                    self.selected_intervals[0],
                    planned_well_df,
                    planned_well_info,
                    dummy_df,
                    self.colors,
                    selection="planned",
                    label=os.path.basename(folder),
                )
            )

        self.selector = SurfaceSelector(
            app, self.metadata, self.intervals, self.map_defaults[0]
        )
        self.selector2 = SurfaceSelector(
            app, self.metadata, self.intervals, self.map_defaults[1]
        )
        self.selector3 = SurfaceSelector(
            app, self.metadata, self.intervals, self.map_defaults[2]
        )

        self.set_callbacks(app)

    @property
    def ensembles(self):
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
            {
                "id": self.uuid("settings-view2"),
                "content": ("Settings for the second map view"),
            },
            {
                "id": self.uuid("settings-view3"),
                "content": ("Settings for the third map view"),
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
                            "Ensemble/Iteration",
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
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            id=self.uuid("settings-view2"),
                            children=[
                                self.selector2.layout,
                                self.ensemble_layout(
                                    1,
                                    ensemble_id=self.uuid("ensemble2"),
                                    ens_prev_id=self.uuid("ensemble2-prev"),
                                    ens_next_id=self.uuid("ensemble2-next"),
                                    real_id=self.uuid("realization2"),
                                    real_prev_id=self.uuid("realization2-prev"),
                                    real_next_id=self.uuid("realization2-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            id=self.uuid("settings-view3"),
                            children=[
                                self.selector3.layout,
                                self.ensemble_layout(
                                    2,
                                    ensemble_id=self.uuid("ensemble3"),
                                    ens_prev_id=self.uuid("ensemble3-prev"),
                                    ens_next_id=self.uuid("ensemble3-next"),
                                    real_id=self.uuid("realization3"),
                                    real_prev_id=self.uuid("realization3-prev"),
                                    real_next_id=self.uuid("realization3-next"),
                                ),
                            ],
                        ),
                    ],
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
                                    sync_ids=[self.uuid("map2"), self.uuid("map3")],
                                    id=self.uuid("map"),
                                    height=600,
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
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                html.Div(
                                    id=self.uuid("heading2"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 20,
                                        "fontWeight": "bold",
                                    },
                                ),
                                html.Div(
                                    id=self.uuid("sim_info2"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 15,
                                        "fontWeight": "bold",
                                    },
                                ),
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map3")],
                                    id=self.uuid("map2"),
                                    height=600,
                                    layers=[],
                                    hillShading=False,
                                ),
                                html.Div(
                                    id=self.uuid("interval-label2"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 20,
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                html.Div(
                                    id=self.uuid("heading3"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 20,
                                        "fontWeight": "bold",
                                    },
                                ),
                                html.Div(
                                    id=self.uuid("sim_info3"),
                                    style={
                                        "textAlign": "center",
                                        "fontSize": 15,
                                        "fontWeight": "bold",
                                    },
                                ),
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map2")],
                                    id=self.uuid("map3"),
                                    height=600,
                                    layers=[],
                                    hillShading=False,
                                ),
                                html.Div(
                                    id=self.uuid("interval-label3"),
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
        # print("get_real_runpath ", data, ensemble, real, map_type)
        # print('self.intervals',self.intervals)

        filepath = compose_filename(
            self.directory,
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

    def get_ens_runpath(self, data, ensemble, map_type):
        data = make_fmu_filename(data)
        runpaths = self.ens_df.loc[(self.ens_df["ENSEMBLE"] == ensemble)][
            "RUNPATH"
        ].unique()
        return [
            str((Path(runpath) / "share" / map_type / "maps" / f"{data}.gri"))
            for runpath in runpaths
        ]

    def get_heading(self, map_ind, observation_type):
        if self.map_defaults[map_ind]["map_type"] == observation_type:
            txt = "Observed map: "
            info = "-"
        else:
            txt = "Simulated map: "
            info = (
                self.selected_ensembles[map_ind]
                + " "
                + self.selected_realizations[map_ind]
            )

        heading = (
            txt
            + self.selected_attributes[map_ind]
            + " ("
            + self.selected_names[map_ind]
            + ")"
        )

        sim_info = info
        label = get_plot_label(self.config, self.selected_intervals[map_ind])

        return heading, sim_info, label

    def make_map(self, data, ensemble, real, attribute_settings, map_idx):
        start = timer()
        data = json.loads(data)
        attribute_settings = json.loads(attribute_settings)
        map_type = self.map_defaults[map_idx]["map_type"]

        # print(f"loading data {timer()-start}")
        surface_file = self.get_real_runpath(data, ensemble, real, map_type)
        surface = load_surface(surface_file)
        metadata = self.surface_metadata.loc[self.surface_metadata["file path"] == surface_file]
        # print(f"loading surface {timer()-start}")
        
        surface_layers = [
            make_surface_layer(
                surface,
                name=data["attr"],
                color=attribute_settings.get(data["attr"], {}).get("color", "viridis"),
                min_val=attribute_settings.get(data["attr"], {}).get("min", None),
                max_val=attribute_settings.get(data["attr"], {}).get("max", None),
                unit=attribute_settings.get(data["attr"], {}).get("unit", ""),
                hillshading=False,
                min_max_df = metadata,
            )
        ]
        # print(f"make surface layer {timer()-start}")
        self.selected_intervals[map_idx] = data["date"]

        for well_layer in self.well_base_layers:
            # print(well_layer["name"])
            surface_layers.append(well_layer)

        interval_file = os.path.join(
            self.wellfolder,
            "production_well_layers_" + self.selected_intervals[map_idx] + ".pkl",
        )
        interval_layer = pickle.load(open(interval_file, "rb"))
        surface_layers.append(interval_layer[0])
        # print(interval_layer[0]["name"])

        interval_file = os.path.join(
            self.wellfolder,
            "injection_well_layers_" + self.selected_intervals[map_idx] + ".pkl",
        )
        interval_layer = pickle.load(open(interval_file, "rb"))
        surface_layers.append(interval_layer[0])
        # print(interval_layer[0]["name"])

        self.selected_names[map_idx] = data["name"]
        self.selected_attributes[map_idx] = data["attr"]
        self.selected_ensembles[map_idx] = ensemble
        self.selected_realizations[map_idx] = real

        heading, sim_info, label = self.get_heading(map_idx, self.observation)
        # print(f"remaining {timer()-start}")
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
            # ctx = dash.callback_context.triggered
            # print(ctx)
            # print("callback 1")
            # print("data ", data)
            return self.make_map(data, ensemble, real, attribute_settings, 0)

        # Second map
        @app.callback(
            [
                Output(self.uuid("heading2"), "children"),
                Output(self.uuid("sim_info2"), "children"),
                Output(self.uuid("map2"), "layers"),
                Output(self.uuid("interval-label2"), "children"),
            ],
            [
                Input(self.selector2.storage_id, "children"),
                Input(self.uuid("ensemble2"), "value"),
                Input(self.uuid("realization2"), "value"),
                Input(self.uuid("attribute-settings"), "data"),
            ],
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_base_layer(
            data, ensemble, real, attribute_settings,
        ):
            # print("callback 2")
            # print("data2", data)
            return self.make_map(data, ensemble, real, attribute_settings, 1)

        # Third map
        @app.callback(
            [
                Output(self.uuid("heading3"), "children"),
                Output(self.uuid("sim_info3"), "children"),
                Output(self.uuid("map3"), "layers"),
                Output(self.uuid("interval-label3"), "children"),
            ],
            [
                Input(self.selector3.storage_id, "children"),
                Input(self.uuid("ensemble3"), "value"),
                Input(self.uuid("realization3"), "value"),
                Input(self.uuid("attribute-settings"), "data"),
            ],
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_base_layer(
            data, ensemble, real, attribute_settings,
        ):
            # print("data3", data)
            return self.make_map(data, ensemble, real, attribute_settings, 2)

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


@webvizstore
def save_surface(fns, statistic) -> io.BytesIO:
    surfaces = xtgeo.Surfaces(fns)
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface()
    elif statistic == "Mean":
        surface = surfaces.apply(np.nanmean, axis=0)
    elif statistic == "StdDev":
        surface = surfaces.apply(np.nanstd, axis=0)
    elif statistic == "Min":
        surface = surfaces.apply(np.nanmin, axis=0)
    elif statistic == "Max":
        surface = surfaces.apply(np.nanmax, axis=0)
    elif statistic == "P10":
        surface = surfaces.apply(np.nanpercentile, 10, axis=0)
    elif statistic == "P90":
        surface = surfaces.apply(np.nanpercentile, 90, axis=0)
    else:
        surface = xtgeo.RegularSurface()
    return io.BytesIO(surface_to_json(surface).encode())


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
