def get_difference(primary_list, exclusion_list):
    return [element for element in primary_list if element not in exclusion_list]
