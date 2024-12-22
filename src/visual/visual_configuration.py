style_function = lambda x: {'fillColor': '#ffffff',
                            'color': '#000000',
                            'fillOpacity': 0.1,
                            'weight': 0.1}

highlight_function = lambda x: {'fillColor': '#000000',
                                'color': '#000000',
                                'fillOpacity': 0.50,
                                'weight': 0.1}


# Geographical data
GEO_PATH = 'recourses/data/geo/shown_geography.geojson'
# Old population density data
POPULATION_DENSITY_PATH = 'recourses/data/population/shown_tract_popdensity2010.csv'

# Harm threshold (in dB)
HARM_AVG_LEVEL = 45
HARM_MAX_LEVEL = 85

# Map
CRS = 'epsg:3857'
