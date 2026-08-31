import os
from datetime import date

import dash_bootstrap_components as dbc
import plotly.io as pio
from dash import dcc, html

from .account_formatter import formatter

pio.templates.default = "plotly_white"

import base64

# Path to your downloaded logo
script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "../assets/REIT_logo.png")

# Encode the image
with open(logo_path, "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode()

logo = html.Img(
    src=f"data:image/png;base64,{encoded_string}",
    height="40px",
    className="bg-white rounded",
    style={
        "padding": "4px",
        "border-radius": "6px"
    }
)

COLORS = {
    "primary": "#04A5D5",
    "secondary": "#333333",
    "light": "#f8f9fa",
    "dark": "#343a40",
    "white": "#ffffff",
    "admin": "#EC7300",
}

HEADER_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "right": 0,
    "height": "80px",
    "zIndex": 1030,
}

FOOTER_STYLE = {
    "position": "fixed",
    "bottom": 0,
    "left": 0,
    "right": 0,
    "height": "40px",
    "zIndex": 1030,
}

CARD_STYLE = {
    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
    "border-radius": "5px",
    "margin-bottom": "20px",
    "padding": "15px",
    "zIndex": 0,
}

# Helper functions
def create_filter(component, title=None):
    """Create a consistently styled filter with an optional title."""
    if title:
        return html.Div(
            [html.Label(title, className="font-weight-bold mb-2"), component],
            className="mb-3",
        )
    return html.Div(component, className="mb-3")


def create_section(title, children, id=None):
    """Create a section with a title and content."""
    return html.Div(
        [
            html.H3(title, className="mb-4", style={"color": COLORS["secondary"]}),
            html.Div(children, className="mb-4"),
        ],
        id=id,
        className="mt-4 mb-5",
    )


# Admin switch component
admin_switch = dbc.Nav(
    [
        dbc.NavItem(
            dbc.NavLink(
                [
                    dbc.Switch(
                        id="admin-mode-switch",
                        value=False,
                        className="ms-2 d-inline-block",
                    ),
                ],
                href="#",
                className="d-flex align-items-center",
                style={"cursor": "pointer"},
            )
        ),
    ],
    navbar=True,
    id="admin-toggle-container",
    style={"display": "none"},
)

# Filter components
data_range_picker = dcc.DatePickerRange(
    id="data_range_picker",
    start_date=date(2000, 1, 1),
    end_date=date(2001, 1, 1),
    className="w-100",
    display_format="YYYY-MM-DD",
)

hostname_dropdown = dcc.Dropdown(
    id="hostname_dropdown",
    options=[{"label": "No cluster data", "value": ""}],
    value="",
    multi=False,
    placeholder="Select cluster...",
    clearable=False,
    className="w-100",
)

partitions_dropdown = dcc.Dropdown(
    id="partitions_dropdown",
    options=[{"label": "Default", "value": "default"}],
    value=None,
    multi=True,
    placeholder="Select partitions...",
    className="w-100",
)

accounts_dropdown = dcc.Dropdown(
    id="accounts_dropdown",
    options=[],
    value=None,
    multi=True,
    placeholder="Filter by accounts...",
    className="w-100",
)

qos_selection_dropdown = dcc.Dropdown(
    id="qos_selection_dropdown",
    options=[],
    value=None,
    multi=True,
    clearable=False,
    placeholder="Filter by QoS...",
    className="w-100",
)

state_items = [
    {"label": "Completed", "value": "COMPLETED"},
    {"label": "Cancelled", "value": "CANCELLED"},
    {"label": "Failed", "value": "FAILED"},
    {"label": "Timeout", "value": "TIMEOUT"},
    {"label": "Out of memory", "value": "OUT_OF_MEMORY"},
    {"label": "Node fail", "value": "NODE_FAIL"},
]

states_dropdown = dcc.Dropdown(
    id="states_dropdown",
    options=state_items,
    value=None,
    multi=True,
    placeholder="Filter states...",
    className="w-100",
)

users_dropdown = dcc.Dropdown(
    id="users_dropdown",
    options=[],
    value=None,
    multi=True,
    placeholder="Filter by users...",
    className="w-100",
)

users_filter_container = html.Div(
    [html.Label("Users", className="font-weight-bold mb-2"), users_dropdown],
    id="users-filter-container",
    className="mb-3",
    style={"display": "none"},
)

color_by_dropdown = dcc.Dropdown(
    id="color_by_dropdown",
    options=[],
    value=None,
    placeholder="Color visualizations by...",
    className="w-100",
)

color_by_items_standard = [
    {"label": "Account", "value": "Account"},
    {"label": "Partition", "value": "Partition"},
    {"label": "State", "value": "State"},
    {"label": "QOS", "value": "QOS"},
]

color_by_items_admin = [
    {"label": "Account", "value": "Account"},
    {"label": "Partition", "value": "Partition"},
    {"label": "State", "value": "State"},
    {"label": "QOS", "value": "QOS"},
    {"label": "User", "value": "User"},
]

waiting_time_observables = [
    {"label": "Median", "value": "50%"},
    {"label": "75 Percentile", "value": "75%"},
    {"label": "Mean", "value": "mean"},
    {"label": "Maximum", "value": "max"},
]

waiting_times_observable_dropdown = dcc.Dropdown(
    id="waiting_times_observable_dropdown",
    options=waiting_time_observables,
    value="50%",
    placeholder="Select metric...",
    clearable=False,
    className="w-100",
)

job_duration_observable_dropdown = dcc.Dropdown(
    id="job_duration_observable_dropdown",
    options=waiting_time_observables,
    value="50%",
    placeholder="Select metric...",
    clearable=False,
    className="w-100",
)

interval = dcc.Interval(
    id="interval",
    interval=1 * 1000 * 60,
    n_intervals=0,
    max_intervals=0,
)

hide_unused_nodes_switch = dbc.Switch(
    id="hide_unused_nodes_switch",
    label="Hide unused nodes",
    value=True,
    className="ms-2 mb-2",
)

normalize_node_resources_switch = dbc.Switch(
    id="normalize_node_resources_switch",
    label="Normalize by resource count",
    value=False,
    className="ms-2 mb-2",
    style={"display": "none"},
)

sort_by_usage_switch = dbc.Switch(
    id="sort_by_usage_switch",
    label="Sort by usage (default: alphabetical)",
    value=False,
    className="ms-2 mb-2",
)

complete_periods_switch = dbc.Switch(
    id="complete_periods_switch",
    label="Show only complete periods",
    value=False,
    className="ms-2 mb-2",
    style={"display": "none"},
)

# Account formatter components
account_formatter_store = dcc.Store(id="account-formatter-store", data={"segments": formatter.max_segments})

account_formatter_controls = html.Div(
    [
        html.Label("Account Name Format", className="font-weight-bold mb-2"),
        dbc.RadioItems(
            id="account-format-segments",
            options=[
                {"label": "Full names", "value": 0},
                {"label": "First segment", "value": 1},
                {"label": "First two segments", "value": 2},
                {"label": "First three segments", "value": 3}
            ],
            value=3,
            inline=False,
            className="mb-2",
        ),
        html.Div(
            [
                html.Small(
                    [
                        "Example: physics-theory-quantum-project",
                        html.Br(),
                        "• Full: physics-theory-quantum-project",
                        html.Br(),
                        "• First segment: physics",
                        html.Br(),
                        "• First two: physics-theory",
                        html.Br(),
                        "• First three: physics-theory-quantum",
                    ],
                    className="text-muted",
                )
            ]
        ),
    ],
    className="mb-3",
    id="account-format-container",
    style={"display": "none"},
)

# Filters sidebar
filters_content = html.Div(
    [
        create_filter(data_range_picker, "Date Range"),
        create_filter(dcc.Loading(hostname_dropdown), "Cluster"),
        create_filter(partitions_dropdown, "Partitions"),
        create_filter(accounts_dropdown, "Accounts"),
        create_filter(states_dropdown, "Job States"),
        create_filter(qos_selection_dropdown, "Quality of Service"),
        users_filter_container,
        complete_periods_switch,
    ],
    className="mt-3",
)

filters_sidebar = html.Div(
    [
        html.H4("Filters", className="mb-3"),
        filters_content,
        html.Hr(className="my-4"),
        html.H4("Visualization", className="mb-3"),
        create_filter(color_by_dropdown, "Color By"),
        account_formatter_controls,
        account_formatter_store,
    ],
    id="filters-sidebar",
    style={
        "backgroundColor": COLORS["light"],
        "padding": "20px",
        "borderRadius": "5px",
        "height": "99%",
        "transition": "all 0.3s ease-in-out",
        "box-shadow": "3px 0 10px rgba(0,0,0,0.1)",
    },
    className="mb-4 mt-4",
)

# Section definitions
overview_section = create_section(
    "Overview",
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Total Active Users"),
                            dbc.CardBody(
                                html.H3(id="total-active-users", className="card-title text-center"),
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Total Jobs"),
                            dbc.CardBody(
                                html.H3(id="total-jobs", className="card-title text-center"),
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Total CPU Hours"),
                            dbc.CardBody(
                                html.H3(id="total-cpu-hours", className="card-title text-center"),
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Total GPU Hours"),
                            dbc.CardBody(
                                html.H3(id="total-gpu-hours", className="card-title text-center"),
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=3,
                ),
            ],
            className="mb-4",
        ),
    ],
    id="overview-section",
)

users_section = create_section(
    "Users",
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Active Users"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_active_users"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=8,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Active Users Distribution"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_active_users_distribution"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
            ],
            className="mb-4",
        ),
    ],
    id="users-section",
)

jobs_section = create_section(
    "Jobs",
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Number of Jobs"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_number_of_jobs"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=8,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Jobs Distribution"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_jobs_distribution"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
            ],
            className="mb-4",
        ),
    ],
    id="jobs-section",
)

resource_usage_section = create_section(
    "Usage",
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("CPU Usage"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_cpu_hours"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=8,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("CPU Usage Distribution"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_cpu_usage_distribution"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
            ],
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("GPU Usage"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_gpu_hours"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=8,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("GPU Usage Distribution"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_gpu_usage_distribution"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
            ],
            className="mb-4",
        ),
        dbc.Card(
            [
                dbc.CardHeader("CPU/GPU Usage by Node"),
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(hide_unused_nodes_switch, width=6),
                                dbc.Col(normalize_node_resources_switch, width=6),
                                dbc.Col(sort_by_usage_switch, width=4),
                            ],
                            className="mb-3",
                        ),
                        dbc.Tabs(
                            [
                                dbc.Tab(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_nodes_usage_cpu"),
                                        type="default",
                                    ),
                                    label="CPU Usage",
                                ),
                                dbc.Tab(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_nodes_usage_gpu"),
                                        type="default",
                                    ),
                                    label="GPU Usage",
                                ),
                            ]
                        ),
                    ]
                ),
            ],
            style=CARD_STYLE,
        ),
    ],
    id="usage-section",
)

job_timing_section = create_section(
    "Timing",
    [
        html.H4("Job Waiting Times", className="mt-3 mb-2"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Waiting Time Distribution by Time Period"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_waiting_times_stacked"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                ),
            ],
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Show/Hide Waiting Time Details",
                        id="collapse-button-waiting",
                        color="outline-primary",
                        size="sm",
                        n_clicks=0,
                    ),
                    width=12,
                    className="text-center mb-3",
                ),
            ]
        ),
        dbc.Collapse(
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Waiting Times Distribution"),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_waiting_times_hist"),
                                        type="default",
                                    )
                                ),
                            ],
                            style=CARD_STYLE,
                        ),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col("Waiting Times Trend", width=8),
                                            dbc.Col(
                                                waiting_times_observable_dropdown,
                                                width=4,
                                            ),
                                        ]
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_waiting_times"),
                                        type="default",
                                    )
                                ),
                            ],
                            style=CARD_STYLE,
                        ),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-5",
            ),
            id="collapse-waiting",
            is_open=False,
        ),
        html.H4("Job Durations", className="mt-4 mb-2"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Job Duration Distribution by Time Period"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_job_duration_stacked"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                ),
            ],
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Show/Hide Job Duration Details",
                        id="collapse-button-duration",
                        color="outline-primary",
                        size="sm",
                        n_clicks=0,
                    ),
                    width=12,
                    className="text-center mb-3",
                ),
            ]
        ),
        dbc.Collapse(
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Job Duration Distribution"),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_job_duration_hist"),
                                        type="default",
                                    )
                                ),
                            ],
                            style=CARD_STYLE,
                        ),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col("Job Duration Trend", width=8),
                                            dbc.Col(
                                                job_duration_observable_dropdown,
                                                width=4,
                                            ),
                                        ]
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(id="plot_job_duration"),
                                        type="default",
                                    )
                                ),
                            ],
                            style=CARD_STYLE,
                        ),
                        width=12,
                        lg=6,
                    ),
                ]
            ),
            id="collapse-duration",
            is_open=False,
        ),
    ],
    id="timing-section",
)

resources_section = create_section(
    "Allocated Resources",
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("CPUs per Job"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_cpus_per_job"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("GPUs per Job"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_gpus_per_job"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Nodes per Job"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id="plot_nodes_per_job"),
                                    type="default",
                                )
                            ),
                        ],
                        style=CARD_STYLE,
                    ),
                    width=12,
                    lg=4,
                ),
            ]
        ),
    ],
    id="resources-section",
)

# Header and Footer
header = html.Div(
    [
        dbc.Navbar(
            dbc.Container(
                [
                    html.A(
                        dbc.Row(
                            [
                                dbc.Col(
                                    logo,
                                    width="auto",
                                    className="me-2 d-flex align-items-center"
                                ),
                                dbc.Col(
                                    html.H2(
                                        "Slurm-Usage-History Dashboard",
                                        className="m-0",
                                        style={"color": COLORS["white"]},
                                    )
                                ),
                            ],
                            align="center",
                            className="g-0",
                        ),
                        href="#",
                        style={"textDecoration": "none"},
                    ),
                    dbc.ButtonGroup(
                        [
                            html.A(
                                dbc.Button(
                                    "Overview",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#overview-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                            html.A(
                                dbc.Button(
                                    "Users",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#users-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                            html.A(
                                dbc.Button(
                                    "Jobs",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#jobs-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                            html.A(
                                dbc.Button(
                                    "Usage",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#usage-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                            html.A(
                                dbc.Button(
                                    "Timing",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#timing-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                            html.A(
                                dbc.Button(
                                    "Resources",
                                    outline=True,
                                    color="light",
                                    size="sm",
                                ),
                                href="#resources-section",
                                **{"data-scroll": "true"},
                                className="mx-1",
                            ),
                        ],
                        className="me-4",
                    ),
                    admin_switch,
                    dbc.Nav(
                        [
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Help",
                                    href="https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history",
                                    external_link=True,
                                )
                            ),
                            dbc.NavItem(dbc.NavLink("Logout", href="/?slo", external_link=True)),
                        ],
                        navbar=True,
                    ),
                ],
                fluid=True,
            ),
            color=COLORS["primary"],
            dark=True,
            className="mb-4",
        )
    ],
    style=HEADER_STYLE,
)

footer = html.Div(
    [
        html.Footer(
            dbc.Container(
                [
                    html.Span(
                        "© 2024 Research Engineering and Infrastructure Team, TU Delft",
                        className="text-center d-block",
                    ),
                ],
                fluid=True,
            ),
            className="py-2",
            style={
                "background": COLORS["primary"],
                "color": COLORS["white"],
                "height": "100%",
            },
        )
    ],
    style=FOOTER_STYLE,
)

# Main layout
layout = html.Div(
    [
        dcc.Store(id='session-store', storage_type='session'),
        dcc.Location(id="url", refresh=False),
        html.Div(id="dummy-output", style={"display": "none"}),
        dbc.Modal(
            [
                dbc.ModalHeader(
                    dbc.ModalTitle("Admin Mode Activated"),
                    close_button=True,
                    style={"backgroundColor": COLORS["admin"], "color": "white"},
                ),
                dbc.ModalBody(
                    [
                        html.P("You have activated admin mode which provides access to additional features:"),
                        html.Ul(
                            [
                                html.Li("Ability to view and filter by individual user data"),
                                html.Li("Access to user-specific metrics and analysis"),
                                html.Li("Additional visualization options for user comparisons"),
                            ]
                        ),
                        html.P("Please use these features responsibly and in accordance with privacy policies."),
                    ]
                ),
                dbc.ModalFooter(dbc.Button("I Understand", id="close-admin-warning", className="ms-auto")),
            ],
            id="admin-warning",
            is_open=False,
        ),
        header,
        interval,
        html.Div(
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                filters_sidebar,
                                id="sidebar-col",
                                width=2,
                                className="position-fixed",
                                style={
                                    "z-index": "1000",
                                    "height": "calc(100vh - 110px)",
                                    "overflow-y": "auto",
                                    "top": "60px",
                                },
                            ),
                            dbc.Col(width=2, id="spacer-col"),
                            dbc.Col(
                                [
                                    overview_section,
                                    users_section,
                                    jobs_section,
                                    resource_usage_section,
                                    job_timing_section,
                                    resources_section,
                                ],
                                width=13,
                                lg=9,
                            ),
                        ]
                    ),
                ],
                fluid=True,
                className="mt-4",
            ),
            style={
                "padding-top": "60px",
                "padding-bottom": "50px",
                "z-index": "0",
            },
        ),
        footer,
    ],
)
