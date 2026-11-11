def get_city(city_names, query):
    for city in city_names:
        if query == city:
            return city
    for city in city_names:
        if query in city:
            return city
    return None

def get_state(states, query):
    us_state_abbreviations = {
        "Alabama": "AL",
        "Alaska": "AK",
        "Arizona": "AZ",
        "Arkansas": "AR",
        "California": "CA",
        "Colorado": "CO",
        "Connecticut": "CT",
        "Delaware": "DE",
        "Florida": "FL",
        "Georgia": "GA",
        "Hawaii": "HI",
        "Idaho": "ID",
        "Illinois": "IL",
        "Indiana": "IN",
        "Iowa": "IA",
        "Kansas": "KS",
        "Kentucky": "KY",
        "Louisiana": "LA",
        "Maine": "ME",
        "Maryland": "MD",
        "Massachusetts": "MA",
        "Michigan": "MI",
        "Minnesota": "MN",
        "Mississippi": "MS",
        "Missouri": "MO",
        "Montana": "MT",
        "Nebraska": "NE",
        "Nevada": "NV",
        "New Hampshire": "NH",
        "New Jersey": "NJ",
        "New Mexico": "NM",
        "New York": "NY",
        "North Carolina": "NC",
        "North Dakota": "ND",
        "Ohio": "OH",
        "Oklahoma": "OK",
        "Oregon": "OR",
        "Pennsylvania": "PA",
        "Rhode Island": "RI",
        "South Carolina": "SC",
        "South Dakota": "SD",
        "Tennessee": "TN",
        "Texas": "TX",
        "Utah": "UT",
        "Vermont": "VT",
        "Virginia": "VA",
        "Washington": "WA",
        "West Virginia": "WV",
        "Wisconsin": "WI",
        "Wyoming": "WY"
    }

    for state in states:
        if query == state:
            return state.upper()
    for state in us_state_abbreviations.keys():
        if query == state.lower():
            return us_state_abbreviations[state]
    for state in us_state_abbreviations.keys():
        if query in state.lower():
            return us_state_abbreviations[state]
    return None

def split_array(arr):
    # Calculate the sizes of the parts
    part1_len = len(arr) // 3
    part2_len = (len(arr) - part1_len) // 2
    
    # Slice the array into 3 parts
    part1 = arr[:part1_len]
    part2 = arr[part1_len:part1_len+part2_len]
    part3 = arr[part1_len+part2_len:]
    
    return [part1, part2, part3]

def get_region_from_id(id):
    regions = {
        1: "Alabama & Panhandle",
        2: "Mississippi",
        3: "Louisiana",
        4: "Arkansas",
        5: "Tennessee",
        6: "North",
        7: "Georgia & Florida",
        8: "North Carolina & South Carolina",
    }

    return regions.get(id, "Unknown Region")

def get_team_name_from_roles(roles, teams):
    teams = set(teams)
    for role in roles:
        if role.name in teams:
            return role.name
    return None