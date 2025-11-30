import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from os.path import join
from dash import  html
from teams import map_team, team_colors


# --- DATA SETUP ---
DATASET_PATH = "./dataset"

drivers = pd.read_csv(join(DATASET_PATH, 'drivers.csv'))
results = pd.read_csv(join(DATASET_PATH, 'results.csv'))
races = pd.read_csv(join(DATASET_PATH, 'races.csv'))[['raceId', 'year', 'name']]
constructors = pd.read_csv(join(DATASET_PATH, 'constructors.csv'))[['constructorId', 'name', 'nationality']]
driver_standings = pd.read_csv(join(DATASET_PATH, 'driver_standings.csv'))


races = races.rename(columns={'name': 'race_name'})
constructors = constructors.rename(columns={'name': 'constructor_name', 'nationality': 'constructor_country'})

df = results.merge(races, on='raceId').merge(constructors, on='constructorId')
df = df.merge(drivers[['driverId', 'forename', 'surname', 'dob', 'nationality']], on='driverId')
df['age'] = df['year'] - pd.to_datetime(df['dob']).dt.year
df['driver_name'] = df['forename'] + ' ' + df['surname']

#Championships
standings_with_year = driver_standings.merge(races[['raceId', 'year']], on='raceId')
final_races = standings_with_year.groupby('year')['raceId'].max().reset_index()
champions = standings_with_year.merge(final_races, on=['year', 'raceId'])
champions = champions[champions['position'] == 1]

# ---  CAREER EXTREMES ---
career = df.groupby('driverId').agg({
'year': ['min', 'max'],
'driver_name': 'first',
'nationality': 'first',
'dob': 'first'
}).reset_index()
career.columns = ['driverId', 'start_year', 'end_year', 'driver_name', 'nationality', 'dob']

# --- DRIVER STATISTICS ---
wins = df[df['positionOrder'] == 1].groupby('driverId').size()
podiums = df[df['positionOrder'] <= 3].groupby('driverId').size()
championships = champions.groupby('driverId').size()
total_races = df.groupby('driverId').size()
teams_driven = df.groupby('driverId')['constructor_name'].nunique()
teams_list = df.groupby('driverId')['constructor_name'].unique().apply(
lambda teams: sorted([t for t in teams if isinstance(t, str)])
).rename('teams_list')

# print(teams_list)
# print(championships)

# Merge stats into career dataframe
career = career.merge(
pd.DataFrame({
    'driverId': career['driverId'],
    'total_races': career['driverId'].map(total_races).fillna(0).astype(int),
    'wins': career['driverId'].map(wins).fillna(0).astype(int),
    'podiums': career['driverId'].map(podiums).fillna(0).astype(int),
    'championships': career['driverId'].map(championships).fillna(0).astype(int),
    'teams_driven': career['driverId'].map(teams_driven).fillna(0).astype(int),
    'teams_list': career['driverId'].map(teams_list)
}), on='driverId', how='left'
)

# print(career)

#TEAM SWAPS
driver_year_team = df.groupby(['driverId', 'year'])['constructor_name'].apply(
lambda x: x.mode().iloc[0] if not x.empty else 'Unknown'
).reset_index(name='primary_team')

driver_year_team = driver_year_team.sort_values(['driverId', 'year'])

driver_year_team['prev_team'] = driver_year_team.groupby('driverId')['primary_team'].shift(1)
driver_year_team['team_changed'] = driver_year_team['prev_team'] != driver_year_team['primary_team']

term_starts = driver_year_team[driver_year_team['team_changed']].copy()
term_starts['term_type'] = 'term Start'

term_ends = []
for _, start in term_starts.iterrows():
    driver_id = start['driverId']
    team = start['primary_team']
    start_yr = start['year']
    
    driver_team_years = driver_year_team[
        (driver_year_team['driverId'] == driver_id) & 
        (driver_year_team['primary_team'] == team) &
        (driver_year_team['year'] >= start_yr)
    ]['year'].sort_values().tolist()
    
    end_yr = start_yr
    for i, yr in enumerate(driver_team_years[:-1]):
        if driver_team_years[i + 1] == yr + 1: 
            end_yr = driver_team_years[i + 1]
        else:  
            break
    
    term_ends.append({
        'driverId': driver_id,
        'year': end_yr,
        'primary_team': team,
        'term_type': 'term End'
    })
term_ends_df = pd.DataFrame(term_ends)

term_data = pd.concat([
term_starts[['driverId', 'year', 'primary_team', 'term_type']],
term_ends_df
], ignore_index=True)

term_data = term_data.merge(
df[['driverId', 'year', 'driver_name', 'age']].drop_duplicates(),
on=['driverId', 'year'],
how='left'
)

# print(f"Total term markers: {len(term_data)}")
# print(term_data.tail(10))



term_data['team_group'] = term_data['primary_team'].apply(map_team)

# --- PLOT DATA PREPARATION ---
starts = term_data[term_data['term_type'] == 'term Start'].copy()
ends = term_data[term_data['term_type'] == 'term End'].copy()
print(term_data.tail())

# Add type column for visualization
starts['type'] = 'Start'
ends['type'] = 'End'

# Combine for unified plotting
plot_data = pd.concat([starts, ends], ignore_index=True)

def add_jitter(df, x_col='year', y_col='age', jitter_amount=0.15):
    """Add deterministic jitter to overlapping points based on driverId"""
    # Create a stable offset for each driver
    df = df.copy()
    df['jitter_x'] = df['driverId'].apply(lambda x: hash(str(x) + 'x') % 100 / 100 - 0.5) * jitter_amount
    df['jitter_y'] = df['driverId'].apply(lambda x: hash(str(x) + 'y') % 100 / 100 - 0.5) * jitter_amount
    
    # Adjust jittered coordinates
    df['jittered_x'] = df[x_col] + df['jitter_x']
    df['jittered_y'] = df[y_col] + df['jitter_y']
    
    return df
def create_career_plot(selected_circuit=None, mode='start', enable_jitter=True):
    """Create plot showing team stints with jittering for overlapping points"""
    
    # Apply jittering to both start and end points
    if enable_jitter:
        starts_jittered = add_jitter(starts)
        ends_jittered = add_jitter(ends)
    else:
        starts_jittered = starts.copy()
        ends_jittered = ends.copy()
        starts_jittered['jittered_x'] = starts_jittered['year']
        starts_jittered['jittered_y'] = starts_jittered['age']
        ends_jittered['jittered_x'] = ends_jittered['year']
        ends_jittered['jittered_y'] = ends_jittered['age']
    
    fig = go.Figure()
    
    # Get and sort teams: background first, then foreground
    all_teams = plot_data['team_group'].unique()
    background_teams = {'Other', 'Unknown', 'Team Lotus Original'}
    
    bg_teams = sorted([t for t in all_teams if t in background_teams])
    fg_teams = sorted([t for t in all_teams if t not in background_teams])
    ordered_teams = bg_teams + fg_teams  # Background drawn first
    
    for team in ordered_teams:
        color = team_colors.get(team, '#A0A0A0')
        
        # Draw START points
        if mode in ['start', 'both']:
            start_pts = starts_jittered[starts_jittered['team_group'] == team]
            if not start_pts.empty:
                fig.add_trace(go.Scatter(
                    x=start_pts['jittered_x'], y=start_pts['jittered_y'],
                    mode='markers', name=team, legendgroup=team,
                    showlegend=(mode == 'start'),
                    marker=dict(symbol='circle', size=8, color=color),
                    customdata=list(zip(
                        start_pts['driverId'], start_pts['driver_name'], 
                        start_pts['primary_team'], start_pts['year'], start_pts['age']
                    )),
                    hovertemplate='%{customdata[1]}<br>Year: %{customdata[3]}<br>Age: %{customdata[4]}<br>Team: %{customdata[2]}<br><b>START</b><extra></extra>',
                ))
        
        # Draw END points (on top of starts for same team)
        if mode in ['end', 'both']:
            end_pts = ends_jittered[ends_jittered['team_group'] == team]
            if not end_pts.empty:
                fig.add_trace(go.Scatter(
                    x=end_pts['jittered_x'], y=end_pts['jittered_y'],
                    mode='markers', name=team, legendgroup=team,
                    showlegend=(mode == 'end'),
                    marker=dict(symbol='x', size=8, color=color),
                    customdata=list(zip(
                        end_pts['driverId'], end_pts['driver_name'], 
                        end_pts['primary_team'], end_pts['year'], end_pts['age']
                    )),
                    hovertemplate='%{customdata[1]}<br>Year: %{customdata[3]}<br>Age: %{customdata[4]}<br>Team: %{customdata[2]}<br><b>END</b><extra></extra>',
                ))
    
    fig.update_layout(
        title=f'Drivers Career: {mode.title()} Points',
        xaxis_title='Season', yaxis_title='Age',
        plot_bgcolor='white', height=700,
        showlegend=(mode != 'both'),
        xaxis=dict(range=[plot_data['year'].min() - 0.5, plot_data['year'].max() + 0.5]),
        yaxis=dict(range=[plot_data['age'].min() - 1, plot_data['age'].max() + 1]),
    )
    
    return fig

def html_render(clickData):
        point = clickData['points'][0]
        driver_id = point['customdata'][0]
        
        driver_data = career[career['driverId'] == driver_id].iloc[0]

        return html.Div([
            html.H3(driver_data['driver_name'], className="driver-name"),
            html.Div([
                html.P(f"Nationality: {driver_data['nationality']}"),
                html.P(f"Career: {driver_data['start_year']} - {driver_data['end_year']}"),
                html.P(f"Age Debut: {abs(datetime.fromisoformat(driver_data['dob']).year - driver_data['start_year'])} years old"),
            ], className="basic-info"),
            html.Div([
                html.P(f"Total Races: {driver_data['total_races']}"),
                html.P(f"Wins: {driver_data['wins']}"),
                html.P(f"Podiums: {driver_data['podiums']}"),
                html.P(f"Championships: {driver_data['championships']}"),
            ], className="stats-grid"),
            html.Div([
                html.P("Teams:", className="teams-label"),
                html.P(", ".join(driver_data['teams_list']), className="teams-list")
            ], className="teams-section")
        ], className="card-content")
