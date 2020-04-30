from datetime import datetime
from uuid import uuid4
import json
import yaml

import numpy as np
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

from webviz_4d._datainput._metadata import get_metadata, unique_values


class SurfaceSelector:
    # pylint: disable=too-many-instance-attributes,too-many-statements
    """### Surface Selector

Creates a widget to select surfaces from a yaml configuration file or dictionary, and
a dataframe of ensemble/realizations, optionally with sensitivity cases.
The current selections are stored in a dcc.Store object that can
be accessed by the storage_id property of the class instance.

* `config`: A dictionary / yaml configuration file of surfaces on the format below
* `ensembles`: A pandas dataframe with ensemble, real(index), runpath, sensname and senscase

Format of configuration:
some_property:
    names:
        - surfacename
        - surfacename
    interval:
        - somedate
        - somedate
    types:    
        - 'results'
        - 'observations'
another_property:
    names:
        - surfacename
        - surfacename
    interval:
        - somedate
        - somedate
"""

    def __init__(self, app, metadata, intervals, map_defaults):

        self.metadata = metadata
        self.intervals = intervals
        self.current_selections = map_defaults
        print(self.current_selections)
        self._storage_id = f"{str(uuid4())}-surface-selector"

        self.set_ids()
        self.set_callbacks(app)

    @staticmethod
    def read_config(config):
        """Reads config file either from a yaml provided file or from a dict"""
        if isinstance(config, str):
            return yaml.safe_load(open(config, "r"))

        if isinstance(config, dict):
            return config

        raise TypeError("Config must be a dictionary of a yaml file")

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the selection"""
        return self._storage_id

    def set_ids(self):
        uuid = str(uuid4())
        self.attr_id = f"{uuid}-attr"
        self.attr_id_btn_prev = f"{uuid}-attr-btn-prev"
        self.attr_id_btn_next = f"{uuid}-attr-btn-next"
        self.name_id = f"{uuid}-name"
        self.name_id_btn_prev = f"{uuid}-name-btn-prev"
        self.name_id_btn_next = f"{uuid}-name-btn-next"
        self.date_id = f"{uuid}-date"
        self.date_id_btn_prev = f"{uuid}-date-btn-prev"
        self.date_id_btn_next = f"{uuid}-date-btn-next"
        self.type_id = f"{uuid}-type"
        self.type_id_btn_prev = f"{uuid}-type-btn-prev"
        self.type_id_btn_next = f"{uuid}-type-btn-next"
        self.name_wrapper_id = f"{uuid}-name-wrapper"
        self.date_wrapper_id = f"{uuid}-date-wrapper"
        self.type_wrapper_id = f"{uuid}-type-wrapper"

    @property
    def attrs(self):
        current_type = self.current_selections["map_type"]
        current_name = self.current_selections["name"]
        df = self.metadata.loc[
            (self.metadata["map_type"] == current_type)
            & (self.metadata["data.name"] == current_name)
        ]
        attributes = unique_values(df["data.content"].values)
        return attributes

    def _names_in_attr(self, attribute):
        current_type = self.current_selections["map_type"]
        current_attribute = self.current_selections["attribute"]
        df = self.metadata.loc[
            (self.metadata["map_type"] == current_type)
            & (self.metadata["data.content"] == current_attribute)
        ]
        names = unique_values(df["data.name"].values)

        if not names:
            names = unique_values(self.metadata["data.name"].values)

        # print('_names_in_attr: ',names)
        return names

    def _interval_in_attr(self, attribute):
        intervals = self.intervals
        if intervals is not None and intervals == [np.nan]:
            return None

        # print('_interval: ',interval)
        return intervals

    @property
    def attribute_selector(self):
        return html.Div(
            style={"display": "grid"},
            children=[
                html.Label(
                    "Surface attribute", style={"fontSize": 15, "fontWeight": "bold"}
                ),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.attr_id,
                            options=[
                                {"label": attr, "value": attr} for attr in self.attrs
                            ],
                            value=self.current_selections["attribute"],
                            clearable=False,
                            style={"fontSize": 15, "fontWeight": "normal"},
                        ),
                        self._make_buttons(
                            self.attr_id_btn_prev, self.attr_id_btn_next
                        ),
                    ],
                ),
            ],
        )

    def _make_buttons(self, prev_id, next_id):
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    id=prev_id,
                    children="⬅",
                ),
                html.Button(
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    id=next_id,
                    children="➡",
                ),
            ],
        )

    def selector(
        self, wrapper_id, dropdown_id, title, default_value, btn_prev, btn_next
    ):
        return html.Div(
            id=wrapper_id,
            style={"display": "none"},
            children=[
                html.Label(title, style={"fontSize": 15, "fontWeight": "bold"}),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=dropdown_id,
                            value=default_value,
                            clearable=False,
                            style={"fontSize": 15, "fontWeight": "normal"},
                        ),
                        self._make_buttons(btn_prev, btn_next),
                    ],
                ),
            ],
        )

    @staticmethod
    def set_grid_layout(columns):
        return {"display": "grid", "gridTemplateColumns": f"{columns}"}

    @property
    def layout(self):
        return html.Div(
            children=[
                html.Div(
                    children=[
                        self.attribute_selector,
                        self.selector(
                            self.type_wrapper_id,
                            self.type_id,
                            "Surface type",
                            self.current_selections["map_type"],
                            self.type_id_btn_prev,
                            self.type_id_btn_next,
                        ),
                        self.selector(
                            self.name_wrapper_id,
                            self.name_id,
                            "Surface name",
                            self.current_selections["name"],
                            self.name_id_btn_prev,
                            self.name_id_btn_next,
                        ),
                        self.selector(
                            self.date_wrapper_id,
                            self.date_id,
                            "Interval",
                            self.current_selections["interval"],
                            self.date_id_btn_prev,
                            self.date_id_btn_next,
                        ),
                    ]
                ),
                dcc.Store(id=self.storage_id),
            ]
        )

    def set_callbacks(self, app):
        # pylint: disable=inconsistent-return-statements
        @app.callback(
            Output(self.attr_id, "value"),
            [
                Input(self.attr_id_btn_prev, "n_clicks"),
                Input(self.attr_id_btn_next, "n_clicks"),
            ],
            [State(self.attr_id, "value")],
        )
        def _update_attr(_n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if callback == f"{self.attr_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.attrs)
            if callback == f"{self.attr_id_btn_next}.n_clicks":
                return next_value(current_value, self.attrs)

        @app.callback(
            [
                Output(self.name_id, "options"),
                Output(self.name_id, "value"),
                Output(self.name_wrapper_id, "style"),
            ],
            [
                Input(self.attr_id, "value"),
                Input(self.name_id_btn_prev, "n_clicks"),
                Input(self.name_id_btn_next, "n_clicks"),
            ],
            [State(self.name_id, "value")],
        )
        def _update_name(attr, _n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            names = self._names_in_attr(attr)
            if not names:
                return None, None, {"visibility": "hidden"}

            callback = ctx[0]["prop_id"]
            if callback == f"{self.name_id_btn_prev}.n_clicks":
                value = prev_value(current_value, names)
            elif callback == f"{self.name_id_btn_next}.n_clicks":
                value = next_value(current_value, names)
            else:
                value = current_value if current_value in names else names[0]
            options = [{"label": name, "value": name} for name in names]
            return options, value, {}

        @app.callback(
            [
                Output(self.date_id, "options"),
                Output(self.date_id, "value"),
                Output(self.date_wrapper_id, "style"),
            ],
            [
                Input(self.attr_id, "value"),
                Input(self.date_id_btn_prev, "n_clicks"),
                Input(self.date_id_btn_next, "n_clicks"),
            ],
            [State(self.date_id, "value")],
        )
        def _update_date(attr, _n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered

            if not ctx:
                raise PreventUpdate
            interval = self._interval_in_attr(attr)

            if not interval or not interval[0]:
                return [], None, {"visibility": "hidden"}

            callback = ctx[0]["prop_id"]
            if callback == f"{self.date_id_btn_prev}.n_clicks":
                value = prev_value(current_value, interval)
            elif callback == f"{self.date_id_btn_next}.n_clicks":
                value = next_value(current_value, interval)
            else:
                value = current_value if current_value in interval else interval[0]
            options = [{"label": format_date(date), "value": date} for date in interval]
            return options, value, {}

        @app.callback(
            Output(self.storage_id, "children"),
            [
                Input(self.attr_id, "value"),
                Input(self.name_id, "value"),
                Input(self.date_id, "value"),
            ],
        )
        def _set_data(attr, name, date):

            """
            Stores current selections to dcc.Store. The information can
            be retrieved as a json string from a dash callback Input.
            E.g. [Input(surfselector.storage_id, 'children')]
            """

            # Preventing update if selections are not valid (waiting for the other callbacks)
            if not name in self._names_in_attr(attr):
                raise PreventUpdate
            if date and not date in self._interval_in_attr(attr):
                raise PreventUpdate
            return json.dumps({"name": name, "attr": attr, "date": date})


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


def format_date(date_string):
    """Reformat date string for presentation
    20010101 => Jan 2001
    20010101_20010601 => (Jan 2001) - (June 2001)
    20010101_20010106 => (01 Jan 2001) - (06 Jan 2001)"""
    date_string = str(date_string)
    if len(date_string) == 8:
        return datetime.strptime(date_string, "%Y%m%d").strftime("%b %Y")

    if len(date_string) == 17:
        [begin, end] = [
            datetime.strptime(date, "%Y%m%d") for date in date_string.split("_")
        ]
        if begin.year == end.year and begin.month == end.month:
            return f"({begin.strftime('%-d %b %Y')})-\
              ({end.strftime('%-d %b %Y')})"

        return f"({begin.strftime('%b %Y')})-({end.strftime('%b %Y')})"

    return date_string
