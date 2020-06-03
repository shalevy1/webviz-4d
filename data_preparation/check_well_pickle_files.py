import argparse
import pickle
import glob

# Main program
def main():
    """ Display the tooltip info found in all well list (pickle) files found in a folder
    
    Parameters
    ----------
    folder : str
        The name of the folder with the pickle files

    Returns
    -------
    """

    parser = argparse.ArgumentParser(
        description="Check well list files"
    )
    parser.add_argument("folder", help="Enter folder path")

    args = parser.parse_args()
    folder = args.folder

    pickle_files = glob.glob(folder + "*.pkl")

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
