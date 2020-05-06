import os
import glob
import pickle
import matplotlib.pyplot as pl


def load_custom_colormaps(colormaps_folder):    
    cmap_files = glob.glob(os.path.join(colormaps_folder,'*.pkl'))
    for cmap_file in cmap_files:
        fp = open(cmap_file, 'rb')
        cmap = pickle.load(fp)
        pl.register_cmap(cmap=cmap)
        fp.close()
