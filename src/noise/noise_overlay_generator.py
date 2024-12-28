import matplotlib
import numpy as np
from PIL import Image
from matplotlib import cm
from matplotlib.colors import Normalize


class NoiseOverlayGenerator:
    def __init__(self, min_scale=25, max_scale=50):
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.norm = Normalize(vmin=min_scale, vmax=max_scale)
        self.colormap = cm.get_cmap('jet')

    def create_overlay_image(self, noise_map, file_name='avg_noises.png'):
        normalized = self.norm(noise_map)
        img_array = self.colormap(normalized)
        img_uint8 = (img_array * 255).astype(np.uint8)
        Image.fromarray(img_uint8).save(file_name)

    def get_color_scale(self):
        colors = [self.colormap(i) for i in np.linspace(0, 1, 256)]
        return [matplotlib.colors.rgb2hex(c) for c in colors]
