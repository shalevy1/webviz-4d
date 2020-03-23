from uuid import uuid4
from pathlib import Path
from glob import glob
from typing import List
import os
import dash

from matplotlib.colors import ListedColormap
from matplotlib.colors import LinearSegmentedColormap
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore

from .._datainput._surface import load_surface, make_surface_layer
from .._datainput._well import (
    read_wells,
    load_well,
    make_multiple_well_layer,
    make_test_layer,
)
from .._datainput._decode_config import ConfigReader
from .._datainput._metadata_backup import (
    extract_metadata,
    get_metadata,
    decode_filename,
    compose_filename,
    get_col_values,
    get_slider_tags,
    get_default_tag_indices,
    get_selected_interval,
    get_map_info,
    get_plot_label,
    get_colormap,
    convert_date,
    get_difference_mode,
    read_config,
    check_yaml_file,
)


class SurfaceViewer(WebvizPluginABC):
    """### SurfaceViewer
    Loads irap bin surfaces and visualizes as image in Leaflet

* `surfacefiles`: List of file paths to Irap binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `wellfiles`: List of file paths to RMS wells
* `zunit`: z-unit for display

"""

    def __init__(
        self,
        app,
        field_name,
        well_dir: Path = None,
        map1: Path = None,
        map2: Path = None,
        map3: Path = None,
        config_file: Path = None,
    ):
        super().__init__()

        self.delimiter = "--"
        self.format = ".gri"
        self.field = field_name
        self.well_dir = Path(well_dir)
        self.dataframes = []
        self.realizations = []
        self.iterations = []
        self.config_file = config_file
        self.map_dict = {}
        self.map_types = ["observations", "results"]

        # print(self.well_dir)

        yaml_status = check_yaml_file(eval("map1"))

        n_maps = 3

        for i in range(1, n_maps + 1):
            map_file = "map" + str(i)
            file_path = str(eval(map_file))
            self.map_dict[map_file] = file_path

            if yaml_status:
                df, self.dates = extract_metadata(file_path)
                print(self.dates)
            else:
                df, self.dates = get_metadata(file_path, self.delimiter)

            self.dataframes.append(df)

        self.tags = get_slider_tags(self.dates)
        # print('self.tags ',self.tags)
        self.maxmarks = len(self.tags)
        self.marks = {}

        for i in range(1, self.maxmarks + 1):
            label_dict = {
                "label": self.tags[i],
                "style": {"font-size": 18, "font-weight": "bold"},
            }
            self.marks[str(i)] = label_dict

        # print('self.marks ',self.marks)

        self.default_tag_indices = get_default_tag_indices(
            self.dates, self.map_dict["map1"], self.delimiter
        )
        self.selected_interval = get_selected_interval(
            self.dates, self.default_tag_indices
        )

        self.names = get_col_values(df, "data.name")
        # print('self.names ',self.names)

        for df in self.dataframes:
            if not self.realizations:
                self.realizations = get_col_values(df, "fmu_id.realization")
                self.iterations = get_col_values(df, "fmu_id.iteration")
                self.simulated_attributes = get_col_values(df, "data.content")

        # print('self.realizations ',self.realizations)
        # print('self.iterations ',self.iterations)
        # print('self.simulated_attributes ', self.simulated_attributes)

        self.wells = read_wells(self.well_dir)

        if self.config_file:
            self.configuration = read_config(str(self.config_file))
        else:
            self.configuration = None

        self.all_wells_layer = make_multiple_well_layer(
            self.wells, name="All wells", zmin=0
        )

        self.current_surface_paths = [
            self.map_dict["map1"],
            self.map_dict["map2"],
            self.map_dict["map3"],
        ]
        # print('self.current_surface_paths',self.current_surface_paths)
        self.label = ""

        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    def map_layout(
        self, map_name, sync_ids, attribute, map_label,
    ):
        map_id = self.ids(map_name)
        directory, map_label, attribute = get_map_info(
            self.map_dict[map_name], self.delimiter
        )

        return html.Div(
            style={"padding": "20px"},
            children=[
                html.Label(
                    children=map_label + ": " + attribute,
                    style={"textAlign": "center", "fontSize": 20, "fontWeight": "bold"},
                ),
                LayeredMap(height=800, sync_ids=sync_ids, id=map_id, layers=[],),
            ],
        )

    @property
    def layout(self):
        """Main layout"""

        # interval_label = get_plot_label(self.configuration, self.selected_interval)

        return html.Div(
            children=[
                html.H2("WebViz-4D " + self.field),
                html.Div(
                    id=self.ids("status-label"),
                    style={"textAlign": "right", "fontSize": 15, "fontWeight": "bold"},
                ),
                html.Label(
                    "Select 4D interval:", style={"fontSize": 15, "font-weight": "bold"}
                ),
                html.Div(
                    [
                        dcc.RangeSlider(
                            id=self.ids("month-slider"),
                            updatemode="mouseup",
                            count=1,
                            min=1,
                            max=self.maxmarks,
                            step=1,
                            value=self.default_tag_indices,
                            marks=self.marks,
                            pushable=1,
                        )
                    ]
                ),
                html.Div(
                    style=self.set_grid_layout(" 1fr 1fr 1fr"),
                    children=html.Label(
                        children=[
                            html.Label("Realization:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("realizations"),
                                options=[
                                    {"label": realization, "value": realization}
                                    for realization in self.realizations
                                ],
                                value=self.realizations[0],
                                clearable=False,
                            ),
                            html.Label("Iterations:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("iterations"),
                                options=[
                                    {"label": iteration, "value": iteration}
                                    for iteration in self.iterations
                                ],
                                value=self.iterations[0],
                                clearable=False,
                            ),
                            html.Label("Zone:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("zones"),
                                options=[
                                    {"label": name, "value": name}
                                    for name in self.names
                                ],
                                value=self.names[0],
                                clearable=False,
                            ),
                        ]
                    ),
                ),
                html.Div(
                    style=self.set_grid_layout(" 1fr 1fr 1fr"),
                    children=html.Label(
                        children=[
                            html.Label("Attributes:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("attributes1"),
                                options=[
                                    {"label": attribute, "value": attribute}
                                    for attribute in self.simulated_attributes
                                ],
                                value=self.simulated_attributes[2],
                                clearable=False,
                            ),
                            html.Label("Attributes:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("attributes2"),
                                options=[
                                    {"label": attribute, "value": attribute}
                                    for attribute in self.simulated_attributes
                                ],
                                value=self.simulated_attributes[2],
                                clearable=False,
                            ),
                            html.Label("Attributes:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("attributes3"),
                                options=[
                                    {"label": attribute, "value": attribute}
                                    for attribute in self.simulated_attributes
                                ],
                                value=self.simulated_attributes[0],
                                clearable=False,
                            ),
                        ]
                    ),
                ),
                html.Div(
                    style=self.set_grid_layout(" 1fr 1fr 1fr"),
                    children=[
                        self.map_layout(
                            map_name="map1",
                            sync_ids=[self.ids("map2"), self.ids("map3")],
                            attribute="maxpos",
                            map_label="Observed 4D attribute: ",
                        ),
                        self.map_layout(
                            map_name="map2",
                            sync_ids=[self.ids("map1"), self.ids("map3")],
                            attribute="maxpos",
                            map_label="Simulated 4D attribute: ",
                        ),
                        self.map_layout(
                            map_name="map3",
                            sync_ids=[self.ids("map1"), self.ids("map2")],
                            attribute="oilthickness",
                            map_label="Simulated change in: ",
                        ),
                        html.Div(
                            id=self.ids("interval-label1"),
                            style={
                                "textAlign": "center",
                                "fontSize": 20,
                                "fontWeight": "bold",
                            },
                        ),
                        html.Div(
                            id=self.ids("interval-label2"),
                            style={
                                "textAlign": "center",
                                "fontSize": 20,
                                "fontWeight": "bold",
                            },
                        ),
                        html.Div(
                            id=self.ids("interval-label3"),
                            style={
                                "textAlign": "center",
                                "fontSize": 20,
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                ),
            ]
        )

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("map1"), "layers"),
                Output(self.ids("map2"), "layers"),
                Output(self.ids("map3"), "layers"),
                Output(self.ids("interval-label1"), "children"),
                Output(self.ids("interval-label2"), "children"),
                Output(self.ids("interval-label3"), "children"),
                Output(self.ids("status-label"), "children"),
            ],
            [Input(self.ids("month-slider"), "value"),],
        )
        def _render_surface(indices):
            """Update map"""
            all_wells_layer = self.all_wells_layer
            #            selected_wells_layer = self.selected_wells_layer

            maps = ["map1", "map2", "map3"]
            layers = []

            selected_dates = [None, None]
            selected_interval = get_selected_interval(self.dates, indices)
            date1 = (
                selected_interval[0:4]
                + selected_interval[5:7]
                + selected_interval[8:10]
            )
            date2 = (
                selected_interval[11:15]
                + selected_interval[16:18]
                + selected_interval[19:21]
            )
            date1 = convert_date(date1)
            date2 = convert_date(date2)

            difference_mode = get_difference_mode(
                self.current_surface_paths[0], self.delimiter
            )

            if difference_mode == "normal":
                selected_dates = [date1, date2]
            else:
                selected_dates = [date2, date1]

            # print(selected_dates)

            for map_name in maps:
                (
                    directory,
                    selected_realization,
                    selected_iteration,
                    selected_map_type,
                    selected_name,
                    selected_attribute,
                    dates,
                ) = decode_filename(self.map_dict[map_name], self.delimiter)
                surfacepath = compose_filename(
                    directory,
                    selected_realization,
                    selected_iteration,
                    selected_map_type,
                    selected_name,
                    selected_attribute,
                    selected_dates,
                    self.delimiter,
                )

                # print('surfacepath ',surfacepath)
                label = get_plot_label(
                    self.configuration, selected_interval, difference_mode
                )
                # label = 'test'
                self.label = label

                if os.path.exists(surfacepath):
                    self.current_surface_paths[int(map_name[-1]) - 1] = surfacepath
                    self.selected_interval = (
                        convert_date(dates[0]) + "_" + convert_date(dates[1])
                    )
                    status_label = "Selected interval is OK"
                else:
                    status_label = (
                        "Attribute maps for interval "
                        + selected_interval
                        + " does not exist"
                    )

                    surfacepath = self.current_surface_paths[int(map_name[-1]) - 1]
                    return [], [], [], [], [], [], status_label

                colorscale, minval, maxval = get_colormap(
                    self.configuration, selected_attribute
                )
                surface_layer = surface_to_leaflet_layer(self, surfacepath, colorscale)
                layers.append([surface_layer, all_wells_layer])

            return layers[0], layers[1], layers[2], label, label, label, status_label

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": fn}]) for fn in self.surfacefiles],
        ]


def surface_to_leaflet_layer(self, surfacepath, colorscale):
    surface = load_surface(str(get_path(surfacepath)))

    return make_surface_layer(
        self.config_file, surface, color=colorscale, hillshading=False,
    )


@webvizstore
def get_path(path) -> Path:
    return Path(path)
