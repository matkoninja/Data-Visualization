import pandas as pd

# Historical team name mapping to modern equivalents
# This ensures teams with lineage connections share the same color
HISTORICAL_TEAM_MAP = {
    # ==================== CURRENT TEAMS ====================

    # Red Bull (Stewart -> Jaguar -> Red Bull)
    'Red Bull': 'Red Bull',
    'Red Bull Racing': 'Red Bull',
    'RBR': 'Red Bull',
    'Stewart': 'Red Bull',
    'Jaguar': 'Red Bull',

    # Racing Bulls (Minardi -> Toro Rosso -> AlphaTauri -> RB)
    'RB': 'Racing Bulls',
    'Racing Bulls': 'Racing Bulls',
    'AlphaTauri': 'Racing Bulls',
    'Toro Rosso': 'Racing Bulls',
    'Minardi': 'Racing Bulls',

    # Mercedes family (Tyrrell -> BAR -> Honda -> Brawn -> Mercedes)
    'Mercedes': 'Mercedes',
    'Mercedes-AMG': 'Mercedes',
    'Mercedes AMG': 'Mercedes',
    'Mercedes GP': 'Mercedes',
    'Brawn GP': 'Mercedes',
    'Brawn': 'Mercedes',
    'Honda': 'Mercedes',
    'BAR': 'Mercedes',
    'Tyrrell': 'Mercedes',

    # Ferrari (consistent)
    'Ferrari': 'Ferrari',
    'Scuderia Ferrari': 'Ferrari',

    # McLaren (consistent through engine changes)
    'McLaren': 'McLaren',
    'Team McLaren': 'McLaren',

    # Williams (consistent through engine changes)
    'Williams': 'Williams',
    'Williams Grand Prix Engineering': 'Williams',

    # Alpine family (Toleman -> Benetton -> Renault -> Lotus Renault -> Alpine)
    'Alpine': 'Renault',
    'Renault': 'Renault',
    'Renault Sport': 'Renault',
    'Lotus Renault GP': 'Renault',
    'Lotus F1': 'Renault',
    'Benetton': 'Renault',
    'Benetton Ford': 'Renault',
    'Benetton Playlife': 'Renault',
    'Benetton Renault': 'Renault',
    'Toleman': 'Renault',
    'Toleman Hart': 'Renault',

    # Aston Martin family (Jordan -> Midland -> Spyker -> Force India ->
    #                      Racing Point -> Aston Martin)
    'Aston Martin': 'Aston Martin',
    'Racing Point': 'Aston Martin',
    'Racing Point Force India': 'Aston Martin',
    'Force India': 'Aston Martin',
    'Force India F1': 'Aston Martin',
    'Spyker': 'Aston Martin',
    'Midland': 'Aston Martin',
    'Jordan': 'Aston Martin',

    # Alfa Romeo family (Sauber -> Alfa Romeo)
    'Alfa Romeo': 'Alfa Romeo',
    'Alfa Romeo Sauber': 'Alfa Romeo',
    'Sauber': 'Alfa Romeo',
    'Stake Sauber': 'Alfa Romeo',

    # Haas (consistent)
    'Haas': 'Haas',
    'Haas F1 Team': 'Haas',

    # ==================== HISTORIC/DEFUNCT TEAMS ====================
    # These will be mapped to 'Other' for coloring

    # Original Team Lotus (pre-1995, separate from modern Lotus F1)
    'Team Lotus': 'Team Lotus Original',
    'Lotus': 'Team Lotus Original',  # Ambiguous without year context

    # Major manufacturers
    'Brabham': 'Other',
    'Cooper': 'Other',
    'Maserati': 'Other',
    'Vanwall': 'Other',
    'BRM': 'Other',
    'Matra': 'Other',

    # 1970s-1990s teams
    'Arrows': 'Other',
    'Footwork': 'Other',
    'Ligier': 'Other',
    'Prost': 'Other',
    'March': 'Other',
    'Leyton House': 'Other',
    'Shadow': 'Other',
    'ATS': 'Other',
    'Fittipaldi': 'Other',
    'Ensign': 'Other',
    'Surtees': 'Other',
    'Wolf': 'Other',
    'Fondmetal': 'Other',
    'Osella': 'Other',
    'Larrousse': 'Other',
    'Onyx': 'Other',
    'AGS': 'Other',
    'Rial': 'Other',
    'Spirit': 'Other',
    'RAM': 'Other',
    'Zakspeed': 'Other',
    'Coloni': 'Other',
    'EuroBrun': 'Other',
    'Life': 'Other',
    'Andrea Moda': 'Other',
    'Dallara': 'Other',
    'Jolly Club': 'Other',
    'Lambo': 'Other',
    'Modena': 'Other',

    # 2000s-2010s defunct teams
    'HRT': 'Other',
    'Hispania Racing': 'Other',
    'Caterham': 'Other',
    'Marussia': 'Other',
    'Manor': 'Other',
    'Virgin': 'Other',

    # Manufacturer teams
    'Toyota': 'Other',
    'BMW': 'Other',
    'BMW Sauber': 'Other',
    'Porsche': 'Other',
    'Subaru': 'Other',
    'Honda Racing': 'Other',

    # One-off teams
    'Simtek': 'Other',
    'Pacific': 'Other',
    'Forti': 'Other',
    'Lola': 'Other',
    'MasterCard Lola': 'Other',
}

team_colors = {
    'Ferrari': '#DC0000',
    'Mercedes': '#00D2BE',
    'Red Bull': '#0600EF',
    'McLaren': '#FF8700',
    'Williams': '#005AFF',
    'Renault': '#FFF500',
    'Alpine': '#FF87BC',
    'Aston Martin': '#006F62',
    'Racing Bulls': '#4E7C9B',
    'Alfa Romeo': '#9B0000',
    'Haas': '#B6BABD',
    'Team Lotus Original': '#A0A0A0',
    'Other': "#BEBEBE",
    'Unknown': '#BEBEBE'
}


def map_team(team_name, year=None):
    """Map any historical team name to its modern equivalent
    for consistent coloring.

    Args:
        team_name: String from the constructor_name column
        year: Optional year to disambiguate ambiguous names like 'Lotus'

    Returns:
        Canonical team name that exists in team_colors dictionary
    """
    if pd.isna(team_name) or team_name == 'Unknown':
        return 'Unknown'

    team_name = str(team_name).strip()

    # Special case for Lotus - needs year to disambiguate
    if team_name == 'Lotus' or team_name == 'Team Lotus':
        if year is not None:
            # Original Team Lotus: 1958-1994
            # Modern Lotus F1 Team: 2012-2015 (Renault rebranded)
            if 2012 <= year <= 2015:
                return 'Renault'
            elif year < 1995:
                return 'Team Lotus Original'
        # Without year, check if it's in modern era data
        return 'Renault'  # Default to modern interpretation

    # Direct lookup
    if team_name in HISTORICAL_TEAM_MAP:
        mapped = HISTORICAL_TEAM_MAP[team_name]
        # If mapped to a specific team key, return it
        if mapped in team_colors:
            return mapped
        # Otherwise return 'Other'
        return 'Other'

    # Partial matching for team names with engine partners
    # e.g., "McLaren Mercedes" -> "McLaren"
    for key in HISTORICAL_TEAM_MAP:
        if key in team_name:
            mapped = HISTORICAL_TEAM_MAP[key]
            if mapped in team_colors:
                return mapped
            return 'Other'

    # Handle common engine partner suffixes
    # Split by common separators
    for separator in [' ', '-', '/', '\\']:
        if separator in team_name:
            base = team_name.split(separator)[0]
            if base in HISTORICAL_TEAM_MAP:
                mapped = HISTORICAL_TEAM_MAP[base]
                if mapped in team_colors:
                    return mapped

    return 'Other'
