from typing_extensions import Literal
import pandas as pd
import plotly.graph_objects as go
from source import (
    constructors_df,
    driver_standings_df,
    drivers_df,
    races_df,
    results_df,
)
from teams import map_team, team_colors, HISTORICAL_TEAM_MAP


races = races_df.copy()[['raceId', 'year', 'name']]
constructors = constructors_df.copy()[['constructorId', 'name', 'nationality']]


races = races.rename(columns={'name': 'race_name'})
constructors = constructors.rename(
    columns={'name': 'constructor_name', 'nationality': 'constructor_country'})

df = (results_df
      .merge(races, on='raceId')
      .merge(constructors, on='constructorId'))
df = df.merge(drivers_df[['driverId',
                          'forename',
                          'surname',
                          'dob',
                          'nationality']],
              on='driverId')
df['age'] = df['year'] - pd.to_datetime(df['dob']).dt.year
df['driver_name'] = df['forename'] + ' ' + df['surname']

# Championships
standings_with_year = driver_standings_df.merge(
    races[['raceId', 'year']], on='raceId')
final_races = standings_with_year.groupby('year')['raceId'].max().reset_index()
champions = standings_with_year.merge(final_races, on=['year', 'raceId'])
champions = champions[champions['position'] == 1]

# --- CAREER EXTREMES (START/END) ---
career = df.groupby('driverId').agg({
    'year': ['min', 'max'],
    'driver_name': 'first',
    'nationality': 'first',
    'dob': 'first'
}).reset_index()
career.columns = ['driverId', 'start_year',
                  'end_year', 'driver_name', 'nationality', 'dob']

# HELPERS


def get_career_data():
    """Return the career dataset for external use"""
    return career


def get_driver_data(driver_id):
    """Get specific driver data"""
    driver_data = drivers_df[drivers_df['driverId'] == driver_id]
    if not driver_data.empty:
        return driver_data.iloc[0]
    return None


# END HELPERS
# Get the first and last team for each driver
first_team = df.groupby('driverId').apply(
    lambda x: x[x['year'] == x['year'].min(
    )]['constructor_name'].mode().iloc[0]
).reset_index(name='first_team')

last_team = df.groupby('driverId').apply(
    lambda x: x[x['year'] == x['year'].max(
    )]['constructor_name'].mode().iloc[0]
).reset_index(name='last_team')

career = career.merge(first_team, on='driverId').merge(
    last_team, on='driverId')

# Create start and end points for plotting
start_points = career[['driverId',
                       'start_year',
                       'driver_name',
                       'nationality',
                       'dob',
                       'first_team']].copy()
start_points['year'] = start_points['start_year']
start_points['team'] = start_points['first_team']
start_points['type'] = 'Start'
start_points['age'] = start_points['year'] - \
    pd.to_datetime(start_points['dob']).dt.year

end_points = career[['driverId',
                     'end_year',
                     'driver_name',
                     'nationality',
                     'dob',
                     'last_team']].copy()
end_points['year'] = end_points['end_year']
end_points['team'] = end_points['last_team']
end_points['type'] = 'End'
end_points['age'] = end_points['year'] - \
    pd.to_datetime(end_points['dob']).dt.year

# --- DRIVER STATISTICS ---
wins = df[df['positionOrder'] == 1].groupby('driverId').size()
podiums = df[df['positionOrder'] <= 3].groupby('driverId').size()
championships = champions.groupby('driverId').size()
total_races = df.groupby('driverId').size()
teams_driven = df.groupby('driverId')['constructor_name'].nunique()
teams_list = df.groupby('driverId')['constructor_name'].unique().apply(
    lambda teams: sorted([t for t in teams if isinstance(t, str)])
).rename('teams_list')

# Merge stats into career dataframe
career = career.merge(
    pd.DataFrame({
        'driverId': career['driverId'],
        'teams_list': career['driverId'].map(teams_list),
        **{
            k: career['driverId'].map(v).fillna(0).astype(int)
            for k, v in (
                ('total_races', total_races),
                ('wins', wins),
                ('podiums', podiums),
                ('championships', championships),
                ('teams_driven', teams_driven),
            )
        }
    }), on='driverId', how='left'
)

# Combine for unified plotting
plot_data = pd.concat([start_points, end_points], ignore_index=True)


Axis = Literal['x'] | Literal['y']


def hash_driver_team(row, axis=Axis):
    return hash(f"{row['driverId']}_{row['team_group']}_{axis}")


def get_jitter(row, axis=Axis, jitter_amount=0.3):
    """Simple hash-based jitter function"""
    base_hash = hash_driver_team(row, axis)
    return (base_hash % 100 / 100 - 0.5) * jitter_amount


def add_jitter(df, x_col='year', y_col='age', jitter_amount=0.3):
    """Add improved jitter with team-based offsetting"""
    df = df.copy()

    # Add team-based offset to separate same-team overlaps
    team_offsets = {team: i * 0.1 for i,
                    team in enumerate(df['team_group'].unique())}

    # Combine driver ID and team for more stable jitter
    df['jitter_x'] = df.apply(
        lambda row: (get_jitter(row, 'x', jitter_amount)
                     + team_offsets.get(row['team_group'], 0)),
        axis=1
    )
    df['jitter_y'] = df.apply(
        lambda row: get_jitter(row, 'y', jitter_amount),
        axis=1
    )

    df['jittered_x'] = df[x_col] + df['jitter_x']
    df['jittered_y'] = df[y_col] + df['jitter_y']

    return df

# In scatter_plot_drivers.py - update create_career_plot function


def create_career_plot(mode='start',
                       enable_jitter=True,
                       constructor_filter=None,
                       driver_filter=None,
                       season_filter=None):
    """Create career plot with improved legend and disclaimer"""
    # Filter by constructor if provided
    if constructor_filter:
        start_points_filtered = start_points.copy()[
            start_points['team'].isin(constructor_filter)
        ]
        end_points_filtered = end_points.copy()[
            end_points['team'].isin(constructor_filter)
        ]
    else:
        start_points_filtered = start_points.copy()
        end_points_filtered = end_points.copy()

    if driver_filter:
        start_points_filtered = start_points_filtered[
            start_points_filtered['driverId'].isin(driver_filter)
        ]
        end_points_filtered = end_points_filtered[
            end_points_filtered['driverId'].isin(driver_filter)
        ]

    if season_filter:
        start_points_filtered = start_points_filtered[
            (start_points_filtered['year'] >= season_filter[0]) &
            (start_points_filtered['year'] <= season_filter[1])
        ]
        end_points_filtered = end_points_filtered[
            (end_points_filtered['year'] >= season_filter[0]) &
            (end_points_filtered['year'] <= season_filter[1])
        ]

    # Map teams
    start_points_filtered['team_group'] = \
        start_points_filtered['team'].apply(map_team)
    end_points_filtered['team_group'] = \
        end_points_filtered['team'].apply(map_team)

    # Apply jittering
    if enable_jitter:
        start_plot = add_jitter(start_points_filtered)
        end_plot = add_jitter(end_points_filtered)
    else:
        start_plot = start_points_filtered.copy()
        end_plot = end_points_filtered.copy()
        start_plot['jittered_x'] = start_plot['year']
        start_plot['jittered_y'] = start_plot['age']
        end_plot['jittered_x'] = end_plot['year']
        end_plot['jittered_y'] = end_plot['age']

    fig = go.Figure()

    # Use different marker sizes and opacity for better visibility
    marker_config = {
        'start': {'size': 10, 'opacity': 0.8, 'symbol': 'circle'},
        'end': {'size': 10, 'opacity': 0.8, 'symbol': 'x'},
        'both': {'size': 9, 'opacity': 0.7}
    }

    config = marker_config.get(mode, marker_config['both'])

    # Plot teams in order (background first)
    all_teams = sorted(set(start_plot['team_group'].tolist()
                           + end_plot['team_group'].tolist()))
    background_teams = {'Other', 'Unknown', 'Team Lotus Original'}

    # Track which teams we've shown in legend
    legend_shown = set()

    for team in all_teams:
        color = team_colors.get(team, '#A0A0A0')
        is_background = team in background_teams

        # Plot start points
        if mode in ['start', 'both']:
            team_starts = start_plot[start_plot['team_group'] == team]
            if not team_starts.empty:
                show_in_legend = (mode == 'start') or (
                    mode == 'both' and team not in legend_shown)
                if show_in_legend:
                    legend_shown.add(team)

                fig.add_trace(go.Scatter(
                    x=team_starts['jittered_x'], y=team_starts['jittered_y'],
                    mode='markers', name=f"{team}", legendgroup=team,
                    showlegend=show_in_legend,
                    marker=dict(
                        symbol='circle',
                        size=config['size'] - (1 if is_background else 0),
                        color=color,
                        opacity=config['opacity'] -
                        (0.2 if is_background else 0)
                    ),
                    customdata=list(zip(
                        team_starts['driverId'],
                        team_starts['driver_name'],
                        team_starts['team'],
                        team_starts['year'],
                        team_starts['age']
                    )),
                    hovertemplate=('%{customdata[1]}<br>Year: '
                                   '%{customdata[3]}<br>Age: '
                                   '%{customdata[4]}<br>Team: '
                                   '%{customdata[2]}<br><b>Career Start</b>'
                                   '<extra></extra>'),
                ))

        # Plot end points
        if mode in ['end', 'both']:
            team_ends = end_plot[end_plot['team_group'] == team]
            if not team_ends.empty:
                show_in_legend = (mode == 'end') or (
                    mode == 'both' and team not in legend_shown)
                if show_in_legend:
                    legend_shown.add(team)

                fig.add_trace(go.Scatter(
                    x=team_ends['jittered_x'], y=team_ends['jittered_y'],
                    mode='markers', name=f"{team}", legendgroup=team,
                    showlegend=show_in_legend,
                    marker=dict(
                        symbol='x',
                        size=config['size'] - (1 if is_background else 0),
                        color=color,
                        opacity=config['opacity'] -
                        (0.2 if is_background else 0)
                    ),
                    customdata=list(zip(
                        team_ends['driverId'], team_ends['driver_name'],
                        team_ends['team'], team_ends['year'], team_ends['age']
                    )),
                    hovertemplate=('%{customdata[1]}<br>Year: '
                                   '%{customdata[3]}<br>Age: '
                                   '%{customdata[4]}<br>Team: '
                                   '%{customdata[2]}<br><b>Career End'
                                   '</b><extra></extra>'),
                ))

    # Add disclaimer annotation
    other_teams = ", ".join([team
                             for team, label
                             in HISTORICAL_TEAM_MAP.items()
                             if label == "Other"])
    disclaimer_text = insert_break_after(
        f'Note: Background teams ({other_teams}, Unknown, '
        f'Team Lotus Original) represent less prominent/historical '
        'teams', 200)

    fig.update_layout(
        title='Entry Age of Formula Drivers by Year',
        xaxis_title='Season',
        yaxis_title='Age',
        plot_bgcolor='white',
        height=700,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
        ),
        xaxis=dict(range=[min(start_plot['year'].min(),
                              end_plot['year'].min()) - 1,
                          max(start_plot['year'].max(),
                              end_plot['year'].max()) + 1]),
        yaxis=dict(range=[min(start_plot['age'].min(),
                              end_plot['age'].min()) - 2,
                          max(start_plot['age'].max(),
                              end_plot['age'].max()) + 2]),
        annotations=[
            dict(
                text=disclaimer_text,
                xref="paper", yref="paper",
                x=0.98, y=0.98,  # Top-right corner
                showarrow=False,
                font=dict(size=9, color="gray"),
                align="left",
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="gray",
                borderwidth=1,
                borderpad=4,
                xanchor="right",  # Anchor to right side
                yanchor="top"     # Anchor to top side
            )
        ]
    )

    return fig


# https://community.plotly.com/t/ploty-legned-break-line-fixed-width/79868
def insert_break_after(text, after):
    if len(text) <= after:
        return text
    else:
        space_index = text.find(' ', after)
        if space_index == -1:
            return text
        return (text[:space_index]
                + '<br>'
                + insert_break_after(text[space_index+1:], after))


def create_career_timeline(driver_id):
    """Create enhanced career timeline chart with all placements
    and mean line"""

    # Get driver's race results
    driver_results = df[df['driverId'] == driver_id].copy()
    driver_results = driver_results.sort_values('year')

    # Get best position per year (including below 10th)
    yearly_best = driver_results.groupby('year').agg({
        'positionOrder': 'min',
        'driver_name': 'first',
        'constructor_name': lambda x: (x.mode().iloc[0]
                                       if not x.empty
                                       else 'Unknown')
    }).reset_index()

    # Calculate mean placement per season
    yearly_stats = driver_results.groupby('year').agg({
        'positionOrder': ['min', 'mean', 'count'],
        'constructor_name': lambda x: (x.mode().iloc[0]
                                       if not x.empty
                                       else 'Unknown')
    }).reset_index()

    yearly_stats.columns = ['year', 'best_position',
                            'mean_position', 'race_count', 'constructor_name']
    yearly_stats['mean_position'] = yearly_stats['mean_position'].round(1)

    # Merge with best positions
    yearly_best = yearly_best.merge(
        yearly_stats[['year', 'mean_position', 'race_count']], on='year')

    # Categorize results
    yearly_best['win'] = yearly_best['positionOrder'] == 1
    yearly_best['podium'] = yearly_best['positionOrder'] <= 3
    yearly_best['points'] = yearly_best['positionOrder'] <= 10
    yearly_best['top15'] = yearly_best['positionOrder'] <= 15

    fig = go.Figure()

    # Plot all seasons with different categories
    categories = [
        ('Championship (1st)',
         yearly_best[yearly_best['win']], 'red', 'star', 15),
        ('Podium (2-3rd)', yearly_best[yearly_best['podium']
         & ~yearly_best['win']], 'gold', 'diamond', 12),
        ('Points (4-10th)', yearly_best[yearly_best['points']
         & ~yearly_best['podium']], 'lightblue', 'circle', 10),
        ('Top 15 (11-15th)', yearly_best[yearly_best['top15']
         & ~yearly_best['points']], 'lightgreen', 'circle', 8),
        ('Other (16+)',
         yearly_best[~yearly_best['top15']], 'lightgray', 'circle', 6)
    ]

    for name, data, color, symbol, size in categories:
        if not data.empty:
            fig.add_trace(go.Scatter(
                x=data['year'],
                y=data['positionOrder'],
                mode='markers',
                name=name,
                marker=dict(size=size, color=color, symbol=symbol),
                customdata=list(zip(data['constructor_name'],
                                    data['positionOrder'],
                                    data['race_count'])),
                hovertemplate=('%{x}: %{customdata[1]}th place<br>Team: '
                               '%{customdata[0]}<br>Races: %{customdata[2]}'
                               '<extra></extra>'),
            ))

    # Add mean position line
    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['mean_position'],
        mode='lines+markers',
        name='Season Average',
        line=dict(color='black', width=3, dash='dash'),
        marker=dict(size=8, color='black', symbol='x'),
        customdata=list(
            zip(yearly_stats['race_count'], yearly_stats['mean_position'])),
        hovertemplate=('%{x}: Avg %{customdata[1]}th place<br>Races: '
                       '%{customdata[0]}<extra></extra>'),
    ))

    # Add best position line (connecting all points)
    fig.add_trace(go.Scatter(
        x=yearly_best['year'],
        y=yearly_best['positionOrder'],
        mode='lines',
        name='Best Position',
        line=dict(color='darkblue', width=1),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Invert y-axis so 1st place is at top
    fig.update_yaxes(autorange='reversed')

    # Calculate y-axis range to include all positions
    min_pos = yearly_best['positionOrder'].min()
    max_pos = yearly_best['positionOrder'].max()
    y_range = [max_pos + 1, max(0.5, min_pos - 1)]

    fig.update_layout(
        title=(str(yearly_best['driver_name'].iloc[0])
               + " - Complete Career Timeline"),
        xaxis_title='Year',
        yaxis_title='Best Championship Position',
        plot_bgcolor='white',
        height=500,
        yaxis=dict(range=y_range),
        xaxis=dict(range=[yearly_best['year'].min() -
                   1, yearly_best['year'].max() + 1]),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="Black",
            borderwidth=1
        )
    )

    return fig
