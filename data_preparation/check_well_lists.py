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

    parser = argparse.ArgumentParser(
        description="Check well list files"
    )
    parser.add_argument("config_file", help="Enter path to the WebViz-4D configuration file")

    args = parser.parse_args()  
    config_file = args.config_file
    config = common.read_config(config_file)

    wellfolder = common.get_config_item(config_file,"wellfolder")
    wellfolder = common.get_full_path(wellfolder)
    print("Reading well lists in", wellfolder)

    pickle_files = glob.glob(wellfolder + "/*.pkl")
    print(pickle_files)

    for pickle_file in pickle_files:
        f = open(pickle_file, "rb")
        info = pickle.load(f)

        print(pickle_file)
        data = info[0]["data"]

        if len(data) > 0:
            for item in data:
                print(item["tooltip"])

        print("")
    
    
if __name__ == "__main__":
    main()    
