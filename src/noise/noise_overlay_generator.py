import matplotlib
import numpy as np
from PIL import Image
from matplotlib import cm
from matplotlib.colors import Normalize

import folium
import branca
import pandas as pd


def get_color_scale():
    colormap = cm.get_cmap('jet')

    colors = [colormap(i) for i in np.linspace(0, 1, 256)]
    return [matplotlib.colors.rgb2hex(c) for c in colors]


def create_noise_layer(combined_noise_df: pd.DataFrame) -> folium.GeoJson:
    min_val = combined_noise_df['combined_noise'].min()
    max_val = combined_noise_df['combined_noise'].max()

    colormap = branca.colormap.LinearColormap(
        colors=get_color_scale(),
        vmin=min_val,
        vmax=max_val,
        caption='Average Noise (dB)'
    )
    colormap.caption = "Noise Level (dB)"

    feature_collection = {
        "type": "FeatureCollection",
        "features": []
    }

    for _, row in combined_noise_df.iterrows():
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

    noise_layer = folium.GeoJson(
        data=feature_collection,
        style_function=style_function,
        name="Noise Map"
    )

    return noise_layer, colormap
