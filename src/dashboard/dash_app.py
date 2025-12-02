import asyncio

import dash
import pandas as pd
import plotly.express as px
from dash import html, dcc, Input, Output, callback

from src.config import Settings
from src.repositories import Repositories

REPOSITORIES: Repositories | None = None

# === ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# === LAYOUT ===
app.layout = html.Div([
    # Хранилища: оригинальные загруженные данные (JSON) и текущая страница таблицы
    dcc.Store(id='uploaded-data-store', data=None),

    # Заголовок
    html.Div([
        html.H1("📊 Финансовый дашборд удержания клиентов",
                style={'textAlign': 'center', 'color': '#1a365d', 'marginBottom': '10px', 'fontWeight': '700'}),
        html.P(
            "Анализ эффективности предложений по удержанию: доходы, расходы, прибыль и удержание клиентов.",
            style={'textAlign': 'center', 'color': '#4a5568', 'fontSize': '16px',
                   'maxWidth': '800px', 'margin': '0 auto 20px'}
        ),
    ], style={'padding': '20px', 'backgroundColor': '#f0f4f8', 'marginBottom': '20px'}),

    dcc.Interval(
        id='interval-component',
        interval=180*1000,
        n_intervals=0
    ),

    # Блок: Фильтры
    html.Div([
        html.H3("⚙️ Фильтры", style={'marginBottom': '15px', 'color': '#2d3748'}),

        # Тип предложения
        html.Div([
            html.Label("Тип предложения удержания:",
                       style={'fontWeight': '600', 'display': 'block', 'marginBottom': '12px'}),
            dcc.Checklist(
                id='type-filters', options=[], value=[], inline=True,
                labelStyle={
                    'display': 'inline-block', 'marginRight': '20px', 'marginBottom': '8px',
                    'padding': '6px 12px', 'backgroundColor': '#edf2f7',
                    'borderRadius': '20px', 'cursor': 'pointer'
                },
                inputStyle={'marginRight': '8px'}
            ),
        ], style={'marginBottom': '25px'}),

        # Период анализа
        html.Div([
            html.Label("Период анализа:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '12px'}),
            html.Div([
                dcc.Dropdown(
                    id='period-level',
                    options=[{'label': 'Год', 'value': 'year'},
                             {'label': 'Квартал', 'value': 'quarter'},
                             {'label': 'Месяц', 'value': 'month'}],
                    placeholder="Уровень", style={'flex': '1'}
                ),
                dcc.Dropdown(id='period-selector', placeholder="Конкретный период", style={'flex': '1'})
            ], style={'display': 'flex', 'gap': '10px'})
        ])
    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '12px',
              'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'}),

    html.Div(id='kpi-indicators', style={'marginBottom': '30px'}),
    html.Div(id='graphs-container'),

    html.Div([
        html.Hr(),
        html.P("© 2025 MMOF", style={'textAlign': 'center', 'color': '#a0aec0', 'fontSize': '12px'})
    ], style={'marginTop': '40px'})
], style={
    'padding': '10px 30px',
    'fontFamily': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
    'backgroundColor': '#f8fafc', 'minHeight': '100vh'
})

@callback(
    Output('uploaded-data-store', 'data'),
    Input('interval-component', 'n_intervals') # Триггер: таймер
)
def load_data_and_store(n_intervals):
    df = load_data_sync()

    if df.empty:
        # Если данные пусты, возвращаем ошибку
        return {'error': "Не удалось загрузить данные из базы данных или данных нет."}

    # Преобразуем DataFrame в JSON-сериализуемый словарь (records)
    df2 = df.copy()
    df2['Дата'] = df2['Дата'].astype(str)

    records = df2.to_dict(orient='records')
    columns = list(df2.columns)

    # Сохраняем только записи и колонки (без ненужного сброса страницы)
    return {'records': records, 'columns': columns}


# === CALLBACK: Обновление фильтров на основе загруженных данных ===
@callback(
    Output('type-filters', 'options'),
    Output('type-filters', 'value'),
    Output('period-selector', 'options'),
    Output('period-selector', 'placeholder'),
    Input('uploaded-data-store', 'data'),  # Триггер: обновленные данные из БД
    Input('period-level', 'value'),
)
def update_filters_from_store(store_data, period_level):
    if not store_data or store_data.get('error'):
        return [], [], [], "Нет данных"

    # Преобразуем записи обратно в DataFrame для работы с Pandas/временными рядами
    df = pd.DataFrame.from_records(store_data['records'])
    df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce')

    type_options = [{'label': t, 'value': t} for t in sorted(df['Тип предложения удержания'].unique())]
    type_value = [opt['value'] for opt in type_options]  # По умолчанию выбираем все

    period_options, placeholder = [], "Выберите уровень периода"

    # Мы используем вашу старую функцию get_periods, но она теперь принимает DataFrame из Store.
    if period_level:
        # ВАЖНО: Ваша старая get_periods работает с datetime-объектами.
        # Поскольку мы группируем по 'YYYY-MM', нам нужно адаптировать логику.
        if period_level == 'year':
            periods = sorted(df['Дата'].dt.year.unique())
        elif period_level == 'quarter':
            periods = sorted(df['Дата'].dt.to_period('Q').astype(str).unique())
        elif period_level == 'month':
            periods = sorted(df['Дата'].dt.strftime('%Y-%m').unique())  # используем YYYY-MM

        period_options = [{'label': str(p), 'value': str(p)} for p in periods]
        placeholder = "Выберите период" if period_options else "Нет данных"

    return type_options, type_value, period_options, placeholder


# === CALLBACK: Основное обновление KPI и графиков (на основе Store) ===
@callback(
    Output('kpi-indicators', 'children'),
    Output('graphs-container', 'children'),
    Input('uploaded-data-store', 'data'),
    Input('period-level', 'value'),
    Input('period-selector', 'value'),
    Input('type-filters', 'value')
)
def update_visuals_from_store(store_data, period_level, period_value, selected_types):
    if not store_data or store_data.get('error'):
        msg = store_data.get('error', "Нет данных для отображения. Проверьте подключение к БД.")
        return html.Div(msg, style={'color': 'red', 'textAlign': 'center'}), html.Div()

    df = pd.DataFrame.from_records(store_data['records'])
    df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce')

    # ... (логика фильтрации и визуализации из вашего старого update_visuals) ...

    # ... (продолжение логики)
    if not selected_types:
        selected_types = df['Тип предложения удержания'].unique().tolist()

    df_filtered = df[df['Тип предложения удержания'].isin(selected_types)].copy()
    if df_filtered.empty:
        return html.Div("Нет данных после фильтрации.", style={'color': 'orange', 'textAlign': 'center'}), html.Div()

    # Фильтрация по периоду (адаптируем вашу старую функцию)
    if period_level and period_value:

        # Переводим 'Дата' в нужный формат для фильтрации
        if period_level == 'year':
            df_final = df_filtered[df_filtered['Дата'].dt.year == int(period_value)]
        elif period_level == 'quarter':
            # period_value - это строка типа '2024Q4'
            df_final = df_filtered[df_filtered['Дата'].dt.to_period('Q').astype(str) == period_value]
        elif period_level == 'month':
            # period_value - это строка типа '2024-11'
            df_final = df_filtered[df_filtered['Дата'].dt.strftime('%Y-%m') == period_value]
        else:
            df_final = df_filtered

    else:
        df_final = df_filtered

    if df_final.empty:
        return html.Div("Нет данных для выбранного периода.",
                        style={'color': 'orange', 'textAlign': 'center'}), html.Div()

    # === KPI ===
    total_retained = df_final['Клиентов удержано'].sum()
    total_churned = df_final['Ушло клиентов'].sum()
    total_income = df_final['Доход'].sum()
    total_expenses = df_final['Расходы'].sum()
    total_profit = total_income - total_expenses

    retention_rate = (total_retained / (total_retained + total_churned) * 100) if (
                total_retained + total_churned) else 0
    cost_per_retained = total_expenses / total_retained if total_retained else 0
    profit_per_retained = total_profit / total_retained if total_retained else 0

    # Группировка по Дате (месяцу) для графика линии
    df_monthly = df_final.groupby('Дата')[['Доход', 'Расходы']].sum().reset_index()

    kpi_card = html.Div([
        html.H3("📈 Ключевые показатели", style={'marginBottom': '20px', 'color': '#2d3748'}),
        html.Div([
            make_kpi("Прибыль", f"{total_profit:,.0f} ₽", "#27ae60", "#f0fff4"),
            make_kpi("Эффективность удержания", f"{retention_rate:.1f}%", "#38a169", "#f0fff4"),
            make_kpi("Расходы на удержание", f"{cost_per_retained:,.0f} ₽", "#d97706", "#fffbeb"),
            make_kpi("Прибыль на клиента", f"{profit_per_retained:,.0f} ₽", "#2b6cb0", "#ebf8ff"),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'flexWrap': 'wrap'})
    ], className="kpi-indicators", style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '12px',
              'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'})

    # === ВИЗУАЛИЗАЦИИ ===
    fig1 = px.line(df_monthly, x='Дата', y=['Доход', 'Расходы'],
                   labels={'value': 'Сумма (₽)', 'variable': 'Показатель'})
    fig1.update_layout(title=None, showlegend=False, margin=dict(t=20))
    # ... (Остальные графики: pies, fig_hist, fig_scatter) ...

    pies = {
        "Доход": px.pie(df_final, names='Тип предложения удержания', values='Доход'),
        "Расходы": px.pie(df_final, names='Тип предложения удержания', values='Расходы'),
        "Удержано клиентов": px.pie(df_final, names='Тип предложения удержания', values='Клиентов удержано'),
        "Ушло клиентов": px.pie(df_final, names='Тип предложения удержания', values='Ушло клиентов')
    }

    for fig in pies.values():
        fig.update_layout(title=None, showlegend=False, margin=dict(t=20, b=20))

    fig_hist = px.histogram(df_final, x='Прибыль', nbins=6)
    fig_hist.update_layout(title=None, showlegend=False, margin=dict(t=20))

    fig_scatter = px.scatter(df_final, x='Клиентов удержано', y='Прибыль',
                             color='Тип предложения удержания', size='Доход')
    fig_scatter.update_layout(title=None, showlegend=False, margin=dict(t=20))

    graphs_section = html.Div([
        html.Div([
            make_graph_block("📈 Суммарные доходы и расходы по датам",
                             "Динамика финансовых потоков с учётом выбранных типов предложений и периода.", fig1)
        ], className='revenue-expense-graph'),

        html.Div([
            make_pie_block(pies),
        ], className='pie-charts-block'),

        html.Div([
            make_graph_block("📊 Распределение прибыли",
                             "Частота различных уровней прибыли по операциям удержания.", fig_hist),
        ], className='profit-histogram'),

        html.Div([
            make_graph_block("🔍 Корреляция: Прибыль и удержанные клиенты",
                             "Зависимость финансового результата от количества удержанных клиентов по типам предложений.",
                             fig_scatter)
        ], className='profit-retention-scatter')
    ])

    return kpi_card, graphs_section

#

def get_periods(df, level):
    """Возвращает список значений для выпадающего списка выбора периода."""
    if level == 'year':
        return [{'label': str(y), 'value': str(y)} for y in sorted(df['Дата'].dt.year.unique())]
    elif level == 'quarter':
        df['Quarter'] = df['Дата'].dt.to_period('Q').astype(str)
        return [{'label': q, 'value': q} for q in sorted(df['Quarter'].unique())]
    elif level == 'month':
        df['Month'] = df['Дата'].dt.to_period('M').astype(str)
        return [{'label': m, 'value': m} for m in sorted(df['Month'].unique())]
    return []


def filter_data_by_period(df, level, period_value):
    """Фильтрует данные по выбранному периоду (год, квартал, месяц)."""
    if level == 'year':
        return df[df['Дата'].dt.year == int(period_value)]
    elif level == 'quarter':
        year, q = period_value.split('Q')
        return df[(df['Дата'].dt.year == int(year)) & (df['Дата'].dt.quarter == int(q))]
    elif level == 'month':
        return df[df['Дата'].dt.to_period('M').astype(str) == period_value]
    return df

#

def make_kpi(title, value, color, bg):
    """Создаёт карточку KPI."""
    return html.Div([
        html.H4(title, style={'margin': 0, 'color': '#4a5568', 'fontSize': '14px'}),
        html.P(value, style={'fontSize': '26px', 'fontWeight': 'bold', 'color': color})
    ], style={'width': '23%', 'textAlign': 'center', 'padding': '15px',
              'backgroundColor': bg, 'borderRadius': '10px'})


def make_graph_block(title, desc, fig):
    """Создаёт стандартный блок графика с заголовком и описанием."""
    return html.Div([
        html.H4(title, style={'marginBottom': '10px', 'color': '#2d3748', 'fontWeight': '600'}),
        html.P(desc, style={'fontSize': '13px', 'color': '#718096', 'marginBottom': '15px'}),
        dcc.Graph(figure=fig)
    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '12px',
              'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'})


def make_pie_block(pies):
    """Создаёт блок из четырёх круговых диаграмм."""
    return html.Div([
        html.H4("🍩 Распределение по типам удержания",
                style={'marginBottom': '15px', 'color': '#2d3748', 'fontWeight': '600'}),
        html.P("Как различные типы предложений влияют на ключевые метрики.",
               style={'fontSize': '13px', 'color': '#718096', 'marginBottom': '20px'}),
        html.Div([html.Div([
            html.P(name, style={'textAlign': 'center', 'fontWeight': '600', 'marginBottom': '8px'}),
            dcc.Graph(figure=fig, style={'height': '300px'})
        ], style={'width': 'calc(25% - 20px)', 'margin': '10px'}) for name, fig in pies.items()
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'flex-start'})
    ], style={'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '12px',
              'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'marginBottom': '25px'})

#

async def load_data_from_db_async():
    async with REPOSITORIES.database as conn:
        query = """
                SELECT 
                    DATE_FORMAT(rc.completed_at, '%%Y-%%m') AS "Дата",
                    COALESCE(o.offer_type, 'Не указано')  AS "Тип предложения удержания",
                    SUM(c.monthly_profit)                 AS "Доход", 
                    SUM(COALESCE(o.cost, 0))              AS "Расходы", 
                    SUM(IF(rc.status = 'churned', 1, 0))  AS "Ушло клиентов",
                    SUM(IF(rc.status = 'retained', 1, 0)) AS "Клиентов удержано"
                FROM retention_cases rc
                     JOIN contracts c ON rc.contract_id = c.contract_id
                     LEFT JOIN offers o ON rc.proposed_offer_id = o.offer_id
                WHERE rc.status IN ('churned', 'retained')
                  AND rc.completed_at IS NOT NULL
                GROUP BY 
                    DATE_FORMAT(rc.completed_at, '%%Y-%%m'),
                    COALESCE(o.offer_type, 'Не указано');
                """

        data = await conn.select_all(query)
        return data


def load_data_sync() -> pd.DataFrame:
    try:
        # Запускаем асинхронную функцию
        data = asyncio.run(load_data_from_db_async())
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['Прибыль'] = df['Доход'] - df['Расходы']

        return df

    except Exception as e:
        print(f"Ошибка при загрузке данных из БД: {e}")
        return pd.DataFrame()

#

def init_dashboard(repositories: Repositories, settings: Settings):
    global REPOSITORIES

    REPOSITORIES = repositories

    app.run(debug=True, use_reloader=False, host=settings.dash_host, port=settings.dash_port)
