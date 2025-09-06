import dash
from dash import Dash, html, dash_table, dcc, Input, Output, callback
import base64
import os
from datetime import datetime
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Crear la aplicación Dash
app = Dash(__name__)
app.title = "TÖRÖN 2 - Sistema de Monitoreo Integral"

# Configuración de carpetas y archivos
IMAGE_FOLDER = r"../../../Fotos/Recibidas"
TELEMETRY_FILE = "./Archivos/telemetria_toron2.csv"

# Variables globales para el control de actualizaciones
last_image_time = 0
last_telemetry_time = 0
cached_images = []
cached_df = None

# ===== FUNCIONES PARA IMÁGENES =====
def get_image_paths():
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    image_paths = []

    if os.path.exists(IMAGE_FOLDER):
        for file in os.listdir(IMAGE_FOLDER):
            if file.lower().endswith(image_extensions):
                full_path = os.path.join(IMAGE_FOLDER, file)
                image_paths.append(full_path)

    # Ordenar por fecha de creación (más antiguas primero)
    image_paths.sort(key=lambda x: os.path.getctime(x))
    return image_paths

def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Error cargando imagen {image_path}: {e}")
        return None

# ===== FUNCIONES PARA TELEMETRÍA =====
def load_telemetry_data():
    global last_telemetry_time, cached_df

    try:
        if not os.path.exists(TELEMETRY_FILE):
            return None

        current_modified_time = os.path.getmtime(TELEMETRY_FILE)

        if current_modified_time != last_telemetry_time:
            print(f"[{datetime.now()}] Actualizando datos de telemetría...")

            df = pd.read_csv(TELEMETRY_FILE, delimiter=";")

            def convertir_a_numero(valor):
                if isinstance(valor, str):
                    return float(valor.replace(',', '.'))
                return valor

            columnas_numericas = ['Altitud', 'Temperatura', 'Presion', 'Humedad', 'Latitud', 'Longitud']
            for col in columnas_numericas:
                if col in df.columns:
                    df[col] = df[col].apply(convertir_a_numero)

            df['Punto'] = "Hora: " + df['Hora']

            cached_df = df
            last_telemetry_time = current_modified_time

        return cached_df

    except Exception as e:
        print(f"Error cargando datos de telemetría: {e}")
        return cached_df

def create_map_figure(df):
    if df is None or df.empty:
        fig = px.scatter_map(
            lat=[10.4806],
            lon=[-66.9036],
            zoom=5,
            height=600
        )
    else:
        fig = px.scatter_map(
            df,
            lat="Latitud",
            lon="Longitud",
            hover_name="Punto",
            hover_data={
                "Altitud": ":.2f",
                "Temperatura": ":.2f",
                "Presion": ":.2f",
                "Humedad": ":.2f",
                "Latitud": ":.6f",
                "Longitud": ":.6f"
            },
            color="Altitud",
            size="Altitud",
            color_continuous_scale=px.colors.sequential.Viridis,
            zoom=5,
            height=600
        )

        # Personalizar el tooltip
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>" +
                "Altitud: %{customdata[0]:.2f} m<br>" +
                "Temperatura: %{customdata[1]:.2f} °C<br>" +
                "Presión: %{customdata[2]:.2f} hPa<br>" +
                "Humedad: %{customdata[3]:.2f} %<br>" +
                "Latitud: %{customdata[4]:.6f}<br>" +
                "Longitud: %{customdata[5]:.6f}"
            )
        )

    fig.update_layout(
        mapbox_style="satellite-streets",
        mapbox=dict(
            center=dict(lat=8, lon=-66),
            zoom=5.5
        ),
        title=dict(
            text="Trayectoria de TÖRÖN 2 - Tiempo Real",
            font=dict(size=20, family="Verdana", color="#ffffff"),
            x=0.5,
            xanchor="center"
        ),
        margin={"r": 0, "t": 60, "l": 0, "b": 0},
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#ffffff")
    )

    return fig

def create_telemetry_chart(df):
    if df is None or df.empty:
        # Crear un gráfico vacío si no hay datos
        fig = go.Figure()
        fig.update_layout(
            title="Sin datos de telemetría",
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#1e1e1e",
            font=dict(color="#ffffff")
        )
        return fig

    # Crear subplots con 4 gráficos en una columna para mejor visualización
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=('Altitud (m)', 'Temperatura (°C)', 'Presión (hPa)', 'Humedad (%)'),
        vertical_spacing=0.1
    )

    # Añadir trazas
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['Altitud'], name="Altitud", line=dict(color='#3498db')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['Temperatura'], name="Temperatura", line=dict(color='#e74c3c')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['Presion'], name="Presión", line=dict(color='#2ecc71')), row=3, col=1)
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['Humedad'], name="Humedad", line=dict(color='#f39c12')), row=4, col=1)

    # Actualizar diseño
    fig.update_layout(
        height=1200,  # Aumentar altura para mejor visualización
        showlegend=False,
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#ffffff"),
        title=dict(
            text="Datos de Telemetría - TÖRÖN 2",
            font=dict(size=20),
            x=0.5
        )
    )

    # Actualizar ejes X (solo el último gráfico muestra etiquetas completas)
    fig.update_xaxes(title_text="Hora", row=4, col=1)
    for i in range(1, 4):
        fig.update_xaxes(showticklabels=False, row=i, col=1)

    # Actualizar ejes Y
    fig.update_yaxes(title_text="m", row=1, col=1)
    fig.update_yaxes(title_text="°C", row=2, col=1)
    fig.update_yaxes(title_text="hPa", row=3, col=1)
    fig.update_yaxes(title_text="%", row=4, col=1)

    return fig

# ===== LAYOUT DE LA APLICACIÓN =====
app.layout = html.Div([
    html.Div([
        html.H1(
            "MISIÓN TÖRÖN 2",
            style={
                'textAlign': 'center',
                'color': '#ffffff',
                'fontFamily': 'Roboto, sans-serif',
                'fontWeight': '700',
                'fontSize': '36px',
                'marginBottom': '10px',
                'textShadow': '2px 2px 4px rgba(0,0,0,0.5)'
            }
        ),
        html.P(
            "Sistema de Monitoreo Integral de la Cápsula Espacial",
            style={
                'textAlign': 'center',
                'color': '#cccccc',
                'fontFamily': 'Monotype Corsiva, sans-serif',
                'fontWeight': '300',
                'fontSize': '20px',
                'marginBottom': '20px'
            }
        ),
    ], style={'backgroundColor': '#2c3e50', 'padding': '20px', 'borderBottom': '3px solid #3498db'}),

    # Pestañas
    dcc.Tabs(id='tabs', value='tab-imagenes', children=[
        dcc.Tab(label='Imágenes', value='tab-imagenes'),
        dcc.Tab(label='Mapa', value='tab-mapa'),
        dcc.Tab(label='Gráficas', value='tab-graficas'),
        dcc.Tab(label='Tabla de Datos', value='tab-tabla'),
    ], style={'fontWeight': 'bold'}),

    html.Div(id='tabs-content'),

    # Componentes de intervalo para actualizaciones
    dcc.Interval(
        id='interval-imagenes',
        interval=3000,  # 3 segundos
        n_intervals=0
    ),
    dcc.Interval(
        id='interval-telemetria',
        interval=2000,  # 2 segundos
        n_intervals=0
    ),
], style={'backgroundColor': '#1e1e1e', 'minHeight': '100vh', 'margin': '0'})

# ===== CALLBACKS =====
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'tab-imagenes':
        return html.Div([
            html.Div(id='image-counter', style={'textAlign': 'center', 'color': '#3498db', 'margin': '20px'}),
            html.Div(id='images-container', style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'})
        ])
    elif tab == 'tab-mapa':
        return html.Div([
            dcc.Graph(id='mapa-tiempo-real', style={'height': '80vh'})
        ], style={'padding': '10px'})
    elif tab == 'tab-graficas':
        return html.Div([
            dcc.Graph(id='grafica-telemetria', style={'height': '1200px'})  # Altura aumentada para mejor visualización
        ], style={'padding': '10px'})
    elif tab == 'tab-tabla':
        return html.Div([
            html.Div(id='tabla-container', style={'padding': '20px'})
        ])

# Callback para actualizar imágenes
@app.callback(
    [Output('images-container', 'children'),
     Output('image-counter', 'children')],
    Input('interval-imagenes', 'n_intervals')
)
def update_images(n_intervals):
    image_paths = get_image_paths()
    total_images = len(image_paths)

    image_elements = []
    for i, img_path in enumerate(reversed(image_paths)):
        image_number = total_images - i
        img_name = os.path.basename(img_path)
        encoded_image = encode_image(img_path)

        if encoded_image:
            image_elements.append(
                html.Div([
                    html.H4(f"Imagen {image_number}: {img_name}", 
                           style={'color': '#ffffff', 'textAlign': 'center', 'marginBottom': '10px'}),
                    html.Img(
                        src=encoded_image,
                        style={
                            'maxWidth': '100%',
                            'maxHeight': '500px',
                            'display': 'block',
                            'margin': '0 auto',
                            'border': '2px solid #3498db',
                            'borderRadius': '5px',
                            'boxShadow': '0 4px 8px rgba(0,0,0,0.3)'
                        }
                    ),
                    html.P(f"Fecha de recepción: {datetime.fromtimestamp(os.path.getctime(img_path)).strftime('%Y-%m-%d %H:%M:%S')}", 
                          style={'color': '#cccccc', 'textAlign': 'center', 'marginTop': '10px'}),
                    html.Hr(style={'borderColor': '#3498db', 'margin': '30px 0'})
                ], style={'marginBottom': '40px'})
            )
        else:
            image_elements.append(
                html.Div([
                    html.H4(f"Imagen {image_number} no disponible", 
                           style={'color': '#ff6666', 'textAlign': 'center'}),
                    html.P(f"No se pudo cargar: {img_name}", 
                          style={'color': '#cccccc', 'textAlign': 'center'}),
                    html.Hr(style={'borderColor': '#3498db', 'margin': '20px 0'})
                ])
            )

    counter_text = f"Total de imágenes: {total_images} | Última actualización: {datetime.now().strftime('%H:%M:%S')}"

    return image_elements, counter_text

# Callback para actualizar mapa
@app.callback(
    Output('mapa-tiempo-real', 'figure'),
    Input('interval-telemetria', 'n_intervals')
)
def update_map(n_intervals):
    df = load_telemetry_data()
    return create_map_figure(df)

# Callback para actualizar gráficas
@app.callback(
    Output('grafica-telemetria', 'figure'),
    Input('interval-telemetria', 'n_intervals')
)
def update_charts(n_intervals):
    df = load_telemetry_data()
    return create_telemetry_chart(df)

# Callback para actualizar tabla
@app.callback(
    Output('tabla-container', 'children'),
    Input('interval-telemetria', 'n_intervals')
)
def update_table(n_intervals):
    df = load_telemetry_data()

    if df is None or df.empty:
        return html.Div("Cargando datos...", style={'textAlign': 'center', 'color': '#ffffff', 'padding': '20px'})

    # Excluir la columna "Punto" de la visualización
    columns_to_show = [col for col in df.columns if col != 'Punto']

    return dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in columns_to_show],
        style_table={'overflowX': 'auto', 'backgroundColor': '#1e1e1e'},
        style_cell={
            'backgroundColor': '#2c3e50',
            'color': 'white',
            'padding': '10px',
            'textAlign': 'left'
        },
        style_header={
            'backgroundColor': '#3498db',
            'fontWeight': 'bold',
            'color': 'white'
        },
        #page_size=10,
        sort_action='native',
        filter_action='native'
    )

# ===== EJECUCIÓN =====
if __name__ == "__main__":
    # Cargar datos iniciales
    cached_images = get_image_paths()
    print(f"Iniciando con {len(cached_images)} imágenes en la carpeta")

    app.run(debug=True, host="0.0.0.0", port=8050)
