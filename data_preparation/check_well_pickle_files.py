""" Display the wells that are included in a given Pickle well lists """

import pickle
import glob


DIRECTORY = "/private/ashska/development/webviz-4d/data_preparation/grane_wells/"

PICKLE_FILES = glob.glob(DIRECTORY + "*.pkl")
#PICKLE_FILES = [DIRECTORY + "production_well_layers_2017-05-15-2014-09-15.pkl"]

for pickle_file in PICKLE_FILES:
    f = open(pickle_file, "rb")
    info = pickle.load(f)

    print(pickle_file)
    data = info[0]["data"]

    if len(data) > 0:
        for item in data:
            print(item["tooltip"])

    print("")
