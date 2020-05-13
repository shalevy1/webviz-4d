import os
import glob
import pickle
import matplotlib.pyplot as pl


def load_custom_colormaps(colormaps_folder):    
    cmap_files = glob.glob(os.path.join(colormaps_folder,'*.pkl'))

    for cmap_file in cmap_files:
        fp = open(cmap_file, 'rb')
        cmap = pickle.load(fp)
        print("Colormap loaded:", cmap.name)
        pl.register_cmap(cmap=cmap)
        fp.close()
        
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Import and convert DSG colormaps")
    parser.add_argument("cmap_directory", help="Enter path to the colormaps folder")  
    args = parser.parse_args()
    folder = args.cmap_directory

    load_custom_colormaps(folder)


if __name__ == "__main__":
    main()        
