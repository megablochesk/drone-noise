"""Short codes and high-level groups of the census ethnic groups, as used in the paper's charts and legend."""

HIGH_LEVEL_GROUPS: dict[str, str] = {
    "Indian": "Asian",
    "Pakistani": "Asian",
    "Bangladeshi": "Asian",
    "Chinese": "Asian",
    "Other Asian": "Asian",
    "African": "Black",
    "Caribbean": "Black",
    "Other Black": "Black",
    "White and Black Caribbean": "Mixed",
    "White and Black African": "Mixed",
    "White and Asian": "Mixed",
    "Other Mixed or Multiple ethnic groups": "Mixed",
    "English, Welsh, Scottish, Northern Irish or British": "White",
    "Irish": "White",
    "Gypsy or Irish Traveller": "White",
    "Roma": "White",
    "Other White": "White",
    "Arab": "Other",
    "Any other ethnic group": "Other",
}

GROUP_CODES: dict[str, str] = {
    "Indian": "A:IND",
    "Pakistani": "A:PAK",
    "Bangladeshi": "A:BAN",
    "Chinese": "A:CHN",
    "Other Asian": "A:OASN",
    "African": "B:AFR",
    "Caribbean": "B:CRB",
    "Other Black": "B:OBLK",
    "White and Black Caribbean": "M:WBCR",
    "White and Black African": "M:WBAF",
    "White and Asian": "M:WASN",
    "Other Mixed or Multiple ethnic groups": "M:OMIX",
    "English, Welsh, Scottish, Northern Irish or British": "W:BRIT",
    "Irish": "W:IRI",
    "Gypsy or Irish Traveller": "W:GIT",
    "Roma": "W:ROM",
    "Other White": "W:OWHT",
    "Arab": "O:ARB",
    "Any other ethnic group": "O:OTH",
}


def abbreviate_ethnic_groups(group_names: list[str]) -> list[str]:
    """'Indian' -> 'A:IND'; a group without a code keeps its name."""
    return [GROUP_CODES.get(name, name) for name in group_names]


def describe_ethnic_group(group_name: str) -> str:
    """'Indian' -> 'Asian: Indian'; a group without a high-level group keeps its name."""
    high_level_group = HIGH_LEVEL_GROUPS.get(group_name)
    return f"{high_level_group}: {group_name}" if high_level_group else group_name
