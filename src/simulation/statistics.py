from matplotlib import pyplot as plt

MIN_NOISE_LEVEL = 0
MAX_NOISE_LEVEL = 3


def plot_noise_difference_colormap(dataframe):
    heatmap_data = dataframe.pivot(index='row', columns='col', values='noise_difference')

    plt.figure(figsize=(10, 8))
    plt.title('Noise Difference Colormap (dBs)', fontsize=16)
    img = plt.imshow(heatmap_data, cmap='coolwarm', aspect='auto', origin='lower',
                     vmin=MIN_NOISE_LEVEL, vmax=MAX_NOISE_LEVEL)

    plt.colorbar(img, label=f'Noise Difference ({MIN_NOISE_LEVEL} to {MAX_NOISE_LEVEL} dBs)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.show()
