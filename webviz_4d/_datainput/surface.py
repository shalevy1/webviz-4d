import numpy as np
import numpy.ma as ma
import math
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE


def load_surface(surface_path):
    return RegularSurface(surface_path)


def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    z.filled(np.nan)
    return [x, y, z]



