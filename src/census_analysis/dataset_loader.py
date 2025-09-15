from common.file_utils import load_df_from_csv

from common.path_configs import PATH_CONFIGS


def load_ethnicity_dataset_df():
    return load_df_from_csv(PATH_CONFIGS.ethnicity_dataset_path)


def load_age_dataset_df():
    return load_df_from_csv(PATH_CONFIGS.age_dataset_path)
