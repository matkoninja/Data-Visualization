import requests
from dash import html
from datetime import datetime
from urllib.parse import urlparse
import pandas as pd


def get_wikipedia_image(wiki_url):
    try:
        if pd.isna(wiki_url) or not wiki_url:
            return None

        # Clean the URL
        wiki_url = wiki_url.strip()

        # Extract page title from URL
        parsed = urlparse(wiki_url)
        page_title = parsed.path.split('/')[-1]

        if not page_title:
            return None

        # Wikipedia API endpoint
        api_url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                   + page_title)
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 6.1; WOW64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/56.0.2924.76 Safari/537.36')
        }
        response = requests.get(api_url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if 'thumbnail' in data and 'source' in data['thumbnail']:
                return data['thumbnail']['source']

    except Exception as e:
        print(f"Error fetching Wikipedia image from {wiki_url}: {e}")

    return None


def create_driver_card(driver_data, link):
    """Create enhanced driver card with photo and career timeline button"""
    driver_name = driver_data['driver_name']
    # Get Wikipedia image
    tmp_photo_url = get_wikipedia_image(link)
    photo_url = tmp_photo_url if tmp_photo_url is not None else ""
    age_at_debut = abs(datetime.fromisoformat(driver_data['dob']).year
                       - driver_data['start_year'])
    card_content = html.Div([
        html.Div([
            html.Img(
                src=(photo_url
                     or "https://via.placeholder.com/150x150?text=No+Photo"),
                className="driver-photo",
                style={'width': '100%', 'height': '150px',
                       'object-fit': 'contain'}
            ) if photo_url else html.Div(),
            html.H3(driver_name, className="driver-name"),
        ], className="driver-header"),

        html.Div([
            html.P(f"Nationality: {driver_data['nationality']}"),
            html.P("Career: " + " - ".join([str(driver_data['start_year']),
                                            str(driver_data['end_year'])])),
            html.P(
                f"Age at Debut: {age_at_debut} years old"),
        ], className="basic-info"),

        html.Div([
            html.P(f"Total Races: {driver_data['total_races']}"),
            html.P(f"Wins: {driver_data['wins']}"),
            html.P(f"Podiums: {driver_data['podiums']}"),
            html.P(f"Championships: {driver_data['championships']}"),
        ], className="stats-grid"),

        html.Div([
            html.P("Teams:", className="teams-label"),
            html.P(
                ", ".join(driver_data['teams_list']), className="teams-list")
        ], className="teams-section"),

        # html.Button(
        #     "Show Career Timeline",
        #     id="show-career-timeline",
        #     n_clicks=0,
        #     className="career-timeline-button",
        #     style={
        #         'margin-top': '20px',
        #         'padding': '10px 20px',
        #         'background-color': '#0066cc',
        #         'color': 'white',
        #         'border': 'none',
        #         'border-radius': '5px',
        #         'cursor': 'pointer',
        #     },
        # ),
    ], className="enhanced-driver-card")
    return card_content
