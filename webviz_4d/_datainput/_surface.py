import numpy as np
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE

from .._datainput._config import get_field_bounds
from ._image_processing import array_to_png, get_colormap, get_new_colormap, read_clx_file


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_surface(surface_path):
    return RegularSurface(surface_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    return [x, y, z]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence, surface):
    return surface.get_fence(fence)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_surface_layer(
    config_file,
    surface,
    name="surface",
    min_val=None,
    max_val=None,
    color="inferno_r",
    hillshading=False,
    unit="",
):
    """Make LayeredMap surface image base layer"""
    arr = get_surface_arr(surface, unrotate=True, flip=True)
    print(np.min(arr[0]),np.max(arr[0]))
    print(np.min(arr[1]),np.max(arr[1]))
    #bounds = get_field_bounds(config_file)
    #print(bounds)
    bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
    min_val = min_val if min_val else np.min(arr[2])
    max_val = max_val if max_val else np.max(arr[2])
    return {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(arr[2].copy()),
                "colormap": get_colormap(color),
                "bounds": bounds,
                "allowHillshading": hillshading,
                "minvalue": f"{min_val:.2f}" if min_val else None,
                "maxvalue": f"{max_val:.2f}" if max_val else None,
                "unit": unit,
            }
        ],
    }
