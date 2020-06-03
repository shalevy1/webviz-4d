import os
import glob
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt
import argparse
from matplotlib import colors
import pickle


def import_colormaps(folder, suffix):
    SUPPORTED_FORMATS = [".clx"]

    if suffix in SUPPORTED_FORMATS:
        cmap_files = glob.glob(os.path.join(folder, "*" + suffix))

        for cmap_file in cmap_files:
            print("Reading " + cmap_file)
            if suffix == ".clx":
                tree = ET.parse(cmap_file)
                root = tree.getroot()

                array = np.empty([256, 3])
                color = np.empty([256])

                red = []
                green = []
                blue = []
                index = []

                for elem in root:
                    for subelem in elem:
                        try:
                            red.append(float(subelem.attrib["red"]) / 255)
                            green.append(float(subelem.attrib["green"]) / 255)
                            blue.append(float(subelem.attrib["blue"]) / 255)
                            index.append(float(subelem.attrib["index"]))
                        except:
                            pass

                x = np.arange(0, 256)
                red_values = np.interp(x, index, red)
                green_values = np.interp(x, index, green)
                blue_values = np.interp(x, index, blue)

                array[:, 0] = red_values
                array[:, 1] = green_values
                array[:, 2] = blue_values

                name = os.path.basename(cmap_file).split(".")[0]

                cm = colors.LinearSegmentedColormap.from_list(name, array)
                pickle_file = cmap_file.replace(suffix, ".pkl")
                fp = open(pickle_file, "wb")
                pickle.dump(cm, fp)
                fp.close()
                print("Colormap " + name + " stored as " + pickle_file)

                cm_r = cm.reversed()
                pickle_file = cmap_file.replace(suffix, "_r.pkl")
                fp = open(pickle_file, "wb")
                pickle.dump(cm_r, fp)
                fp.close()
                print("Colormap " + name + "_r stored as " + pickle_file)

            else:
                print("ERROR: " + suffix + " not supported")


def main():
    parser = argparse.ArgumentParser(
        description="Import and convert DSG colormaps")
    parser.add_argument("cmap_directory", help="Enter path to the colormaps folder")  
    args = parser.parse_args()
    folder = args.cmap_directory

    SUFFIX = ".clx"
    
    import_colormaps(folder, SUFFIX)


if __name__ == "__main__":
    main()
