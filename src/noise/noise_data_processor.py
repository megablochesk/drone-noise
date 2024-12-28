import os
import pandas as pd


class NoiseDataProcessor:
    @staticmethod
    def read_data(result_path: str):
        matrix_df = pd.read_csv(os.path.join(result_path, 'noise.csv'))
        config_df = pd.read_csv(os.path.join(result_path, 'config.csv'))
        return matrix_df, config_df

    @staticmethod
    def generate_density_matrix(matrix_df: pd.DataFrame, config_df: pd.DataFrame):
        config = config_df.iloc[0]
        rows = int(config['Rows'])
        cols = int(config['Cols'])

        avg_noises = matrix_df['Average Noise'].to_numpy().reshape(rows, cols)
        max_noises = matrix_df['Maximum Noise'].to_numpy().reshape(rows, cols)

        return avg_noises, max_noises
