import folium
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, MultiPoint
from shapely.ops import voronoi_diagram, unary_union

warehouses = [
    ('DBR1', (51.500773, 0.160277)),
    ('DBR2', (51.389926, 0.110440)),
    ('DCR1', (51.361253, -0.119953)),
    ('DCR2', (51.375578, -0.124525)),
    ('DCR3', (51.372757, -0.121484)),
    ('DHA1', (51.556886, -0.264871)),
    ('DHA2', (51.556944, -0.262778)),
    ('DIG1', (51.653594, -0.024036)),
    ('DRM4', (51.524925, 0.111827)),
    ('DXE1', (51.520417, -0.006570)),
    ('DXN1', (51.504271, -0.447186)),
    ('EHU2', (51.520837, -0.006301)),
    ('MLN2', (51.521963, -0.080489)),
    ('MLN3', (51.502286, -0.073931)),
]

gdf_gl = ox.geocode_to_gdf('Greater London, UK')
boundary = unary_union(gdf_gl.geometry)

points = [Point(lon, lat) for _, (lat, lon) in warehouses]
full_vor = voronoi_diagram(MultiPoint(points))

records = []
for (name, (lat, lon)), pt in zip(warehouses, points):
    for cell in full_vor.geoms:
        clipped = cell.intersection(boundary)
        if not clipped.is_empty and clipped.covers(pt):
            records.append({'name': name, 'geometry': clipped})
            break

vor_gdf = gpd.GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')

centroid = boundary.centroid
m = folium.Map(location=[centroid.y, centroid.x], zoom_start=9)
folium.GeoJson(
    vor_gdf,
    style_function=lambda f: {'fillOpacity': 0.2, 'color': 'black'},
    tooltip=folium.GeoJsonTooltip(fields=['name'])
).add_to(m)

for name, (lat, lon) in warehouses:
    folium.Marker(location=[lat, lon], popup=name).add_to(m)

m.save('london_voronoi_map.html')
