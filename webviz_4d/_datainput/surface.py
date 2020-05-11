import numpy as np
import numpy.ma as ma
import math
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE

from .image_processing import array_to_png, get_colormap


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
    z.filled(np.nan)
    return [x, y, z]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence, surface):
    return surface.get_fence(fence)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_surface_layer(
    surface,
    name="surface",
    min_val=None,
    max_val=None,
    color="viridis",
    hillshading=False,
    min_max_df=None,
    unit="",    
):
    """Make LayeredMap surface image base layer"""
    zvalues = get_surface_arr(surface)[2]
    bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
    
    if not min_max_df.empty:
        lower_limit = min_max_df["lower_limit"].values[0]
        
        if lower_limit is not None and not math.isnan(lower_limit):
            min_val = lower_limit
            
        upper_limit = min_max_df["upper_limit"].values[0]
        
        if upper_limit is not None and not math.isnan(upper_limit):
            max_val = upper_limit
    
    if min_val is not None:
        zvalues[(zvalues < min_val) & (ma.getmask(zvalues) == ma.nomask)] = min_val
        
        if np.nanmin(zvalues) > min_val:
            zvalues[0,0] = ma.nomask
            zvalues.data[0,0] = min_val
                  
    if max_val is not None:
        zvalues[(zvalues > max_val) & (ma.getmask(zvalues) == ma.nomask)] = max_val 
        
        if np.nanmax(zvalues) < max_val:
            zvalues[-1,-1] = ma.nomask
            zvalues.data[-1,-1] = max_val
        
        
    min_val = min_val if min_val is not None else np.nanmin(zvalues)
    max_val = max_val if max_val is not None else np.nanmax(zvalues)
    
    print("Layered map:", name, min_val,max_val)
    
    return {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(zvalues.copy()),
                "colormap": get_colormap(color),
                "bounds": bounds,
                "allowHillshading": hillshading,
                "minvalue": f"{min_val:.2f}" if min_val is not None else None,
                "maxvalue": f"{max_val:.2f}" if max_val is not None else None,
                "unit": str(unit),
            }
        ],
    }
