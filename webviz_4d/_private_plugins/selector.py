from uuid import uuid4

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc


class Selector:
    # pylint: disable=too-many-instance-attributes,too-many-statements
    """### Selector

Creates a widget to select an item from a list, including next and prev buttons.
The current selection are stored in a dcc.Store object that can
be accessed by the storage_id property of the class instance.
"""


    def __init__(self, app, label, items, default_item):
        self.items = items
        self.default_item = default_item
        self._storage_id = f"{str(uuid4())}-selector"
        self.set_ids()
        self.set_callbacks(app)

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the selection"""
        return self._storage_id

    def set_ids(self):
        uuid = str(uuid4())
        self.item_id = f"{uuid}-selector"
        self.item_id_btn_prev = f"{uuid}-selector-btn-prev"
        self.item_id_btn_next = f"{uuid}-selector-btn-next"
        self.item_wrapper_id = f"{uuid}-selector-wrapper"

    @property
    def item_selector(self):
        return html.Div(
            style={"display": "grid"},
            children=[
                html.Label(
                    label, style={"fontSize": 15, "fontWeight": "bold"}
                ),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.item_id,
                            options=[
                                {"label": item, "value": item} for item in self.items
                            ],
                            value=default_item,
                            clearable=False,
                            style={"fontSize": 15, "fontWeight": "normal"},
                        ),
                        self._make_buttons(
                            self.item_id_btn_prev, self.item_id_btn_next
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


    def set_callbacks(self, app):
        # pylint: disable=inconsistent-return-statements
        @app.callback(
            [
                Output(self.item_id, "options"),
                Output(self.item_id, "value"),
                Output(self.item_wrapper_id, "style"),
            ],
            [
                Input(self.item_id, "value"),
                Input(self.item_id_btn_prev, "n_clicks"),
                Input(self.item_id_btn_next, "n_clicks"),
            ],
            [State(self.item_id, "value")],
        )
        def _update_item(_n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if ctx is None or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if callback == f"{self.item_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.items)
            if callback == f"{self.item_id_btn_next}.n_clicks":
                return next_value(current_value, self.items)

        @app.callback(
            [
                Output(self.storage_id, "children"),
                Input(self.item_id, "value"),
            ],    
        )
        def _set_data(item):

            """
            Stores current selections to dcc.Store. The information can
            be retrieved as a json string from a dash callback Input.
            E.g. [Input(surfselector.storage_id, 'children')]
            """

            return json.dumps({"item": item})


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



