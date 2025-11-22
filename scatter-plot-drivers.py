import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from os.path import join

DATASET_PATH = "./dataset"

# --- 1. Load Data (you'll need these 4 files) ---
drivers = pd.read_csv(join(DATASET_PATH,'drivers.csv'))
results = pd.read_csv(join(DATASET_PATH,'results.csv'))
races = pd.read_csv(join(DATASET_PATH,'races.csv'))[['raceId', 'year']] 
constructors = pd.read_csv(join(DATASET_PATH,'constructors.csv'))[['constructorId', 'name']] 

# --- 2. Merge & Calculate Age ---
df = results.merge(races, on='raceId').merge(constructors, on='constructorId')
df = df.merge(drivers[['driverId', 'forename', 'surname', 'dob']], on='driverId')
df['age'] = df['year'] - pd.to_datetime(df['dob']).dt.year
df['driver_name'] = df['forename'] + ' ' + df['surname']

# --- 3. Find Career Extremes (Start & End Year) ---
career = df.groupby('driverId').agg({
    'year': ['min', 'max'],
    'driver_name': 'first'
}).reset_index()
career.columns = ['driverId', 'start_year', 'end_year', 'driver_name']

# --- 4. Filter: Only Drivers with 5+ Season Careers ---
# ADJUST THIS THRESHOLD: 5+ seasons = ~50-80 drivers (good balance)
# 10+ seasons = ~20-30 drivers (very clean)
#career = career[career['end_year'] - career['start_year'] >= 5]

# --- 5. Efficiently Get Team & Age at Start/End ---
# Pre-compute primary team per driver-year (much faster than apply)
team_age_lookup = df.groupby(['driverId', 'year']).agg({
    'name': lambda x: x.mode().iloc[0],  # Most common team
    'age': 'mean'
}).reset_index()

# Merge start data
career = career.merge(
    team_age_lookup.rename(columns={'name': 'start_team', 'age': 'start_age'}),
    left_on=['driverId', 'start_year'],
    right_on=['driverId', 'year'],
    how='left'
).drop('year', axis=1)

# Merge end data
career = career.merge(
    team_age_lookup.rename(columns={'name': 'end_team', 'age': 'end_age'}),
    left_on=['driverId', 'end_year'],
    right_on=['driverId', 'year'],
    how='left'
).drop('year', axis=1)

# --- 6. Create Plot DataFrame (Start + End Points) ---
starts = career[['driverId', 'driver_name', 'start_year', 'start_age', 'start_team']].copy()
starts['year'] = starts['start_year']
starts['age'] = starts['start_age']
starts['team'] = starts['start_team']
starts['type'] = 'Start'

ends = career[['driverId', 'driver_name', 'end_year', 'end_age', 'end_team']].copy()
ends['year'] = ends['end_year']
ends['age'] = ends['end_age']
ends['team'] = ends['end_team']
ends['type'] = 'End'

plot_data = pd.concat([starts, ends], ignore_index=True)

# --- 7. Map Teams to 12 Color Groups ---
team_colors = {
    'Ferrari': '#DC0000',      'Mercedes': '#00D2BE',      'Red Bull': '#0600EF',
    'McLaren': '#FF8700',      'Williams': '#005AFF',      'Renault': '#FFF500',
    'Alpine': '#FF87BC',       'Aston Martin': '#006F62',  'AlphaTauri': '#4E7C9B',
    'Alfa Romeo': '#9B0000',   'Haas': '#B6BABD',          'Other': '#A0A0A0'
}

def map_team(team_name):
    """Map full team name to color group"""
    if pd.isna(team_name): 
        return 'Other'
    for key in team_colors:
        if key in str(team_name):
            return key
    return 'Other'

plot_data['team_group'] = plot_data['team'].apply(map_team)

# --- 8. Create Scatter Plot (One Trace Per Team) ---
fig = go.Figure()

for team in plot_data['team_group'].unique():
    team_data = plot_data[plot_data['team_group'] == team]
    color = team_colors.get(team, '#A0A0A0')
    
    # START POINTS (constant symbol in legend)
    start_pts = team_data[team_data['type'] == 'Start']
    if not start_pts.empty:
        fig.add_trace(go.Scatter(
            x=start_pts['year'],
            y=start_pts['age'],
            mode='markers',
            name=team,
            legendgroup=team,
            showlegend=True,  # Only this appears in legend
            marker=dict(symbol='circle', size=10, color=color, line=dict(width=1, color='white')),
            customdata=list(zip(start_pts['driver_name'], start_pts['team'])),
            hovertemplate='<b>%{customdata[0]}</b><br>Year: %{x}<br>Age: %{y}<br>Team: %{customdata[1]}<br><b>START</b><extra></extra>'
        ))
    
    # END POINTS (different symbol, hidden from legend)
    end_pts = team_data[team_data['type'] == 'End']
    if not end_pts.empty:
        fig.add_trace(go.Scatter(
            x=end_pts['year'],
            y=end_pts['age'],
            mode='markers',
            legendgroup=team,
            showlegend=False,  # Hidden from legend
            marker=dict(symbol='x', size=10, color=color, line=dict(width=1, color='white')),
            customdata=list(zip(end_pts['driver_name'], end_pts['team'])),
            hovertemplate='<b>%{customdata[0]}</b><br>Year: %{x}<br>Age: %{y}<br>Team: %{customdata[1]}<br><b>END</b><extra></extra>'
        ))

# --- 4. Style ---
fig.update_layout(
    title='F1 Driver Careers: Start & End Points',
    xaxis_title='Season',
    yaxis_title='Age',
    hovermode='closest',
    plot_bgcolor='white',
    font=dict(family="Arial", size=12),
    legend=dict(title='Teams', itemsizing='constant'),
    width=1200,
    height=700
)

fig.show()