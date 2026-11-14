"""The short codes of the ethnic groups used in the paper's bar charts and their legend table."""
from census_analysis.ethnic_group_codes import abbreviate_ethnic_groups, describe_ethnic_group


def test_groups_get_the_codes_of_the_paper():
    assert abbreviate_ethnic_groups(["Indian", "Other White", "Arab"]) == ["A:IND", "W:OWHT", "O:ARB"]


def test_a_group_is_described_with_its_high_level_group():
    assert describe_ethnic_group("Indian") == "Asian: Indian"
    assert describe_ethnic_group("English, Welsh, Scottish, Northern Irish or British") == (
        "White: English, Welsh, Scottish, Northern Irish or British"
    )


def test_an_unknown_group_keeps_its_name():
    assert abbreviate_ethnic_groups(["Martian"]) == ["Martian"]
    assert describe_ethnic_group("Martian") == "Martian"
