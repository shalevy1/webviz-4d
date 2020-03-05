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
from .._datainput._well import load_well, make_multiple_well_layer, make_test_layer
from .._datainput._config import (
    get_field_name,
    get_filenames,
    read_attributes,
    read_wells,
    get_plot_label,
    get_intervals,
    get_directory,
    get_file_path,
    get_colormap,
    get_slider_tags,
    get_map_info,
    get_default_tag_indices,
    get_selected_interval,
    get_attribute,
)


class SurfaceViewer3(WebvizPluginABC):
    """### SurfaceViewer
    Loads irap bin surfaces and visualizes as image in Leaflet

* `surfacefiles`: List of file paths to Irap binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `wellfiles`: List of file paths to RMS wells
* `zunit`: z-unit for display

"""

    def __init__(self, app, config_file: Path = None):
        super().__init__()

        self.config_file = Path(config_file)
        self.field_name = get_field_name(self.config_file)

        self.tags, self.dates = get_slider_tags(self.config_file)
        self.maxmarks = len(self.tags)

        self.marks = {}

        for i in range(1, self.maxmarks + 1):
            label_dict = {
                "label": self.tags[i],
                "style": {"font-size": 18, "font-weight": "bold"},
            }
            self.marks[str(i)] = label_dict

        self.default_tag_indices = get_default_tag_indices(self.config_file)

        map_name = "map1"
        self.selected_interval = get_selected_interval(
            self.config_file, map_name, self.dates, self.default_tag_indices
        )

        attributes = []

        for i in range(0, 3):
            attribute = get_attribute(self.config_file, "map" + str(i + 1))
            attributes.append(attribute)

        self.attributes = attributes

        node = "map1"
        all_attributes, all_dates, all_intervals = read_attributes(config_file, node)
        # print(all_attributes)

        node = "map3"
        all_attributes, all_dates, all_intervals = read_attributes(config_file, node)
        # print(all_attributes)

        self.wells = read_wells(self.config_file)

        filter_text = "G-34_AY"
        self.selected_well_list = []

        for well in self.wells:
            if filter_text in well.name:
                self.selected_well_list.append(well)

        self.all_wells_layer = make_multiple_well_layer(
            self.wells, name="All wells", zmin=0
        )
        self.selected_wells_layer = make_multiple_well_layer(
            self.selected_well_list, name=filter_text
        )
        # print("Loaded wells: " + str(len(self.wells)))
        # print("Selected wells: " + str(len(self.selected_well_list)))
        self.current_surface_paths = ["", "", ""]
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
        directory, map_label, attribute = get_map_info(self.config_file, map_name)

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

        interval_label = get_plot_label(self.config_file, self.selected_interval)

        return html.Div(
            children=[
                # html.H2("WebViz-4D " + self.field_name),
                html.H2("WebViz-4D POC"),
                html.Div(
                    id=self.ids("status-label"),
                    style={"textAlign": "right", "fontSize": 15, "fontWeight": "bold"},
                ),
                html.Label(
                    "Select 4D interval:", style={"fontSize": 18, "font-weight": "bold"}
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
            selected_wells_layer = self.selected_wells_layer

            maps = ["map1", "map2", "map3"]
            layers = []

            for map_name in maps:
                selected_interval = get_selected_interval(
                    self.config_file, map_name, self.dates, indices
                )
                surfacepath = get_file_path(
                    self.config_file,
                    map_name,
                    get_attribute(self.config_file, map_name),
                    selected_interval,
                )
                label = get_plot_label(self.config_file, selected_interval)
                self.label = label

                if os.path.exists(surfacepath):
                    self.current_surface_paths[int(map_name[-1]) - 1] = surfacepath
                    self.selected_interval = selected_interval
                    status_label = "Selected interval is OK"
                else:
                    status_label = (
                        "Attribute maps for interval "
                        + selected_interval
                        + " does not exist"
                    )
                    print(
                        "WARNING: attribute maps for interval "
                        + selected_interval
                        + " does not exist"
                    )
                    surfacepath = self.current_surface_paths[int(map_name[-1]) - 1]
                    return [], [], [], [], [], [], status_label

                colorscale, minval, maxval = get_colormap(self.config_file, surfacepath)
                surface_layer = surface_to_leaflet_layer(self, surfacepath, colorscale)
                layers.append([surface_layer, all_wells_layer, selected_wells_layer])

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
