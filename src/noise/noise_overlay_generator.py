import branca
import folium
import matplotlib
import numpy as np
from matplotlib import cm


def get_color_scale():
    colormap = cm.get_cmap('jet')

    colors = [colormap(i) for i in np.linspace(0, 1, 256)]
    return [matplotlib.colors.rgb2hex(c) for c in colors]


def get_colormap(min_noise_level, max_noise_level, caption):
    return branca.colormap.LinearColormap(
        colors=get_color_scale(),
        vmin=min_noise_level,
        vmax=max_noise_level,
        caption=caption
    )


def create_noise_layer(dataframe, colormap) -> folium.GeoJson:
    feature_collection = {
        "type": "FeatureCollection",
        "features": []
    }

    for _, row in dataframe.iterrows():
        feature_collection["features"].append({
            "type": "Feature",
            "properties": {
                "combined_noise": row["combined_noise"]
            },
            "geometry": row["geometry"]
        })

    def style_function(feature):
        val = feature["properties"]["combined_noise"]
        return {
            "fillColor": colormap(val),
            "fillOpacity": 0.7,
            "color": None,
            "weight": 0
        }

    return folium.GeoJson(
        data=feature_collection,
        style_function=style_function,
        name="Noise Pollution Map"
    )
