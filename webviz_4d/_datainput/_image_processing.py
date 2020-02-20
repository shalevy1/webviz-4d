import io
import base64

import numpy as np
from matplotlib import cm
from PIL import Image

import matplotlib as mpl
import matplotlib.pyplot as plt
from xml.dom import minidom
from pathlib import Path

def read_clx_file(color_dir,color_name):
    color_file = color_dir + color_name + '.clx'
    mydoc = minidom.parse(color_file)
    items = mydoc.getElementsByTagName('controlPoint')
    
    points = []
    rgbs = []
    
    for item in items:
        points.append(item.attributes['index'].value)
        red = item.attributes['red'].value
        green = item.attributes['green'].value
        blue = item.attributes['blue'].value
        rgb = [red,green,blue]
        rgbs.append(rgb)
        
    return points, rgbs


def create_colormap(name,points,rgbs,mode):
    cmap = None
    tuples = []

    l = len(points)

    for i in range(0,l):
        rgb = rgbs[i]
        r = int(float(rgb[0]))/255
        g = int(float(rgb[1]))/255
        b = int(float(rgb[2]))/255
        t = (int(float(points[i]))/255,[r,g,b])
        tuples.append(t)

    cmap = mpl.colors.LinearSegmentedColormap.from_list(name, tuples, N=256,gamma=1.0)

    reverse = []
    k = []   

    for key in cmap._segmentdata:    
        k.append(key)
        channel = cmap._segmentdata[key]
        data = []

        for t in channel:                    
            data.append((1-t[0],t[2],t[1]))            
        reverse.append(sorted(data))    

    LinearL = dict(zip(k,reverse))
    cmap_r = mpl.colors.LinearSegmentedColormap(name, LinearL) 

    if mode == 'r':
        #return cmap_r
        cm.register_cmap(name,cmap_r)

    cm.register_cmap(name,cmap)
    #return cmap 



def array_to_png(tensor, shift=True, colormap=False):
    """The layered map dash component takes in pictures as base64 data
    (or as a link to an existing hosted image). I.e. for containers wanting
    to create pictures on-the-fly from numpy arrays, they have to be converted
    to base64. This is an example function of how that can be done.

    1) Scale the input array (tensor) to the range 0-255.
    2) If shift=True and colormap=False, the 0 value in the scaled range
       is reserved for np.nan (while the actual data points utilize the
       range 1-255.

       If shift=True and colormap=True, the 0 value in the colormap range
       has alpha value equal to 0.0 (i.e. full transparency). This makes it
       possible for np.nan values in the actual map becoming transparent in
       the image.
    3) If the array is two-dimensional, the picture is stored as greyscale.
       Otherwise it is either stored as RGB or RGBA (depending on if the size
       of the third dimension is three or four, respectively).
    """

    tensor -= np.nanmin(tensor)

    if shift:
        tensor *= 254.0 / np.nanmax(tensor)
        tensor += 1.0
    else:
        tensor *= 255.0 / np.nanmax(tensor)

    tensor[np.isnan(tensor)] = 0

    if colormap:
        if tensor.shape[0] != 1:
            raise ValueError("The first dimension of a colormap tensor should be 1")
        if tensor.shape[1] != 256:
            raise ValueError("The second dimension of a colormap tensor should be 256")
        if tensor.shape[2] not in [3, 4]:
            raise ValueError(
                "The third dimension of a colormap tensor should be either 3 or 4"
            )
        if shift:
            if tensor.shape[2] != 4:
                raise ValueError(
                    "Can not shift a colormap which is not utilizing alpha channel"
                )
            tensor[0][0][3] = 0.0  # Make first color channel transparent

    if tensor.ndim == 2:
        image = Image.fromarray(np.uint8(tensor), "L")
    elif tensor.ndim == 3:
        if tensor.shape[2] == 3:
            image = Image.fromarray(np.uint8(tensor), "RGB")
        elif tensor.shape[2] == 4:
            image = Image.fromarray(np.uint8(tensor), "RGBA")
        else:
            raise ValueError(
                "Third dimension of tensor must have length 3 (RGB) or 4 (RGBA)"
            )
    else:
        raise ValueError("Incorrect number of dimensions in tensor")
    byte_io = io.BytesIO()
    image.save(byte_io, format="png")

    byte_io.seek(0)

    base64_data = base64.b64encode(byte_io.read()).decode("ascii")

    return f"data:image/png;base64,{base64_data}"


def get_colormap(colormap):
    return array_to_png(
        cm.get_cmap(colormap, 256)([np.linspace(0, 1, 256)]), colormap=True
    )
    
def get_new_colormap(colormap):
    color_dir = str(Path.home()) + '/.lgcpalettes/'
    color_name = 'spectrum'
    
    points, rgbs = read_clx_file(color_dir,color_name)
    colormap = create_colormap(color_name, points, rgbs, 'r')
    
    return array_to_png(
        cm.get_cmap(color_name, 256)([np.linspace(0, 1, 256)]), colormap=True
    )

