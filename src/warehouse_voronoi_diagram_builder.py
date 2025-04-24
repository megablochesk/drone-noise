import folium
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, MultiPoint
from shapely.ops import voronoi_diagram, unary_union

from common.configuration import LONDON_WAREHOUSES_LATLON as WAREHOUSES


def get_area_boundary(location):
    gdf = ox.geocode_to_gdf(location)
    return unary_union(gdf.geometry)


def compute_voronoi_cells(points, boundary):
    diagram = voronoi_diagram(MultiPoint(points))
    return [cell.intersection(boundary) for cell in diagram.geoms if not cell.is_empty]


def assign_cells_to_warehouses(points, cells):
    records = []

    for (name, _), pt in zip(WAREHOUSES, points):
        for cell in cells:
            if cell.covers(pt):
                records.append({'name': name, 'geometry': cell})
                break

    return gpd.GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')


def create_map(voronoi_diagram_gdf, boundary):
    centroid = boundary.centroid

    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=9)

    folium.GeoJson(
        voronoi_diagram_gdf,
        style_function=lambda f: {'fillOpacity': 0.2, 'color': 'black'},
        tooltip=folium.GeoJsonTooltip(fields=['name'])
    ).add_to(m)

    for name, (lat, lon) in WAREHOUSES:
        folium.Marker(location=[lat, lon], popup=name).add_to(m)

    return m


def main(result_file, location):
    boundary = get_area_boundary(location)

    points = [Point(lon, lat) for _, (lat, lon) in WAREHOUSES]
    cells = compute_voronoi_cells(points, boundary)

    vor_gdf = assign_cells_to_warehouses(points, cells)

    m = create_map(vor_gdf, boundary)

    m.save(result_file)

if __name__ == '__main__':
    result_file_path = 'recourses/results/london_voronoi_map.html'
    location_name = 'Greater London, UK'

    main(result_file_path, location_name)
