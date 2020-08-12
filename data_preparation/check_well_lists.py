import argparse
import pickle
import glob
from webviz_4d._datainput import common

# Main program
def main():
    """ Display the tooltip info found in all well list (pickle) files found in a folder
    
    Parameters
    ----------
    configuration_file : str
        The name of WebViz-4D configuration file

    Returns
    -------
    """
    description = "Check well list files"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config_file", help="Enter path to the WebViz-4D configuration file"
    )

    args = parser.parse_args()
    print(description)
    print(args)

    config_file = args.config_file
    config = common.read_config(config_file)

    wellfolder = common.get_config_item(config, "wellfolder")
    wellfolder = common.get_full_path(wellfolder)
    print("Reading well lists in", wellfolder)

    pickle_files = glob.glob(wellfolder + "/*.pkl")

    for pickle_file in pickle_files:
        file_object = open(pickle_file, "rb")
        info = pickle.load(file_object)

        print(pickle_file)
        data = info["data"]

        if len(data) > 0:
            for item in data:
                print(item["tooltip"])

        print("")


if __name__ == "__main__":
    main()
