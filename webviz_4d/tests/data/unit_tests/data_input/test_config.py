from webviz_4d._datainput.common import read_config, get_config_item

with open("../../fmu_directory.txt", "r") as f:
    FMU_DIRECTORY = f.read()


def test_get_config_item():
    config_file = "../../reek_4d.yaml"
    config = read_config(config_file)
    print(get_config_item(config, "fmu_directory"))

    assert get_config_item(config, "fmu_directory") == FMU_DIRECTORY
