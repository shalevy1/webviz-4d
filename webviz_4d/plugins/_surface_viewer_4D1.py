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
)
from webviz_4d._private_plugins.surface_selector import SurfaceSelector
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
        self.attribute_settings = attribute_settings if attribute_settings else {}

        # Find FMU directory
        keys = list(self.ens_paths.keys())
        path = self.ens_paths[keys[0]]
        # print(path)

        self.directory = os.path.dirname(path).replace("*", "0")
        self.fmu_info = os.path.dirname(self.directory)
        # print(directory)

        self.number_of_maps = 1
        self.configuration = configuration
        self.config = read_config(self.configuration)
        default_interval = self.config["map_settings"]["default_interval"]
        self.selected_intervals = [default_interval, default_interval, default_interval]
        # print(self.config)
        self.map_defaults = get_map_defaults(self.config, self.number_of_maps)
        # print('self.map_defaults ',self.map_defaults)

        self.metadata, self.dates = get_metadata(
            self.directory, self.map_defaults[0], self.delimiter
        )
        # print(self.metadata)
        # print("")

        self.intervals = get_all_intervals(self.metadata)
        # print("self.intervals ", self.intervals)

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

        self.well_base_layer = []
        self.well_base_layer.append(
            make_new_well_layer(
                self.selected_intervals[0],
                self.drilled_well_df,
                self.drilled_well_info,
                self.interval_df,
            )
        )
        self.well_base_layer.append(
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
            self.well_base_layer.append(
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
                                    sync_ids=[],
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
        print("self.selected_intervals[map_ind] ", self.selected_intervals[map_ind])
        print("self.config ", self.config)
        label = get_plot_label(self.config, self.selected_intervals[map_ind])

        return heading, sim_info, label

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
            print("data ", data)
            start = timer()
            data = json.loads(data)
            attribute_settings = json.loads(attribute_settings)
            map_type1 = self.map_defaults[0]["map_type"]

            print(f"loading data {timer()-start}")
            start = timer()
            surface = load_surface(
                self.get_real_runpath(data, ensemble, real, map_type1)
            )
            print(f"loading surface {timer()-start}")
            start = timer()
            surface_layers = [
                make_surface_layer(
                    surface,
                    name="surface",
                    color=attribute_settings.get(data["attr"], {}).get(
                        "color", "viridis"
                    ),
                    min_val=attribute_settings.get(data["attr"], {}).get("min", None),
                    max_val=attribute_settings.get(data["attr"], {}).get("max", None),
                    unit=attribute_settings.get(data["attr"], {}).get("unit", ""),
                    hillshading=False,
                )
            ]
            print(f"make surface layer {timer()-start}")
            self.selected_intervals[0] = data["date"]

            start2 = timer()
            well_layers = self.well_base_layer.copy()
            print(f"copy well layer {timer()-start2}")
            well_layers.append(
                make_new_well_layer(
                    self.selected_intervals[0],
                    self.drilled_well_df,
                    self.drilled_well_info,
                    self.interval_df,
                    self.colors,
                    selection="production",
                    label="Producers",
                )
            )
            well_layers.append(
                make_new_well_layer(
                    self.selected_intervals[0],
                    self.drilled_well_df,
                    self.drilled_well_info,
                    self.interval_df,
                    self.colors,
                    selection="injection",
                    label="Injectors",
                )
            )

            for well_layer in well_layers:
                surface_layers.append(well_layer)
            print(f"Well data {timer()-start}")

            self.selected_names[0] = data["name"]
            self.selected_attributes[0] = data["attr"]
            self.selected_ensembles[0] = ensemble
            self.selected_realizations[0] = real

            map_ind = 0
            heading, sim_info, label = self.get_heading(map_ind, self.observation)
            print(heading, sim_info, label)
            print(f"remaining {timer()-start}")
            return (
                heading,
                sim_info,
                surface_layers,
                label,
            )

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
