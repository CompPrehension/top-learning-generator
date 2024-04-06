# crop_png.py

import os
import time
from collections import Counter

try:
    from PIL import Image
except ModuleNotFoundError:
    print('import error: module `PIL` is not installed. This will break calls to crop_image(). Use: pip install Pillow')


# code origin: https://stackoverflow.com/questions/26310873/how-do-i-crop-an-image-on-a-white-background-with-python

def crop_image(image, out_path=None, threshold=0, pad=8, quiet=True):
    out_path = out_path or image
    # image_name = image.split("\\")[-1]
    im = Image.open(image)
    pixels = im.load()
    width, height = im.size

    # modify to crop right side only...

    # rows = []
    # for h_index in range(height):
    #     row = []
    #     for w_index in range(width):
    #         row.append(pixels[((w_index, h_index))])
    #     color_count = Counter(row)[(255, 255, 255)] / float(len(row))
    #     rows.append([h_index, color_count])

    # columns = []
    x2 = width
    step = int(pad * 0.8)
    for w_index in range(width - 1, 0, -step):
        column = []
        for h_index in range(height):
            column.append(im.getpixel((w_index, h_index)))
        color_count = Counter(column)[(255, 255, 255)]  # / float(len(column))
        if height - color_count <= threshold:
            x2 = w_index + step // 2 + pad  # still white background
        else:
            break
        # columns.append([w_index, color_count])

    # rows_indexes = [i[0] for i in rows if i[1] < threshold]
    # columns_indexes = [i[0] for i in columns if i[1] < threshold]

    # x1, y1, x2, y2 = columns_indexes[0], rows_indexes[0], columns_indexes[-1], rows_indexes[-1]

    if out_path.endswith('.jpg'):
        kw = dict(quality=92)
    else:
        kw = {}

    if not quiet: print('saving cropped image')
    im.crop((
        # max(0, x1-pad), max(0, y1-pad), x2, y2
        0, 0, x2, height,
    )).save(out_path, **kw)


if __name__ == '__main__':
    # path_in  = 'out_c.jpg'
    path_in = r'c:\Temp2\cntrflowoutput_v6_jpg\algo_cond_signal__9903369855764460415__1643030095.jpg'
    # path_out = 'out_0_c.jpg'
    path_out = path_in.replace('.', '_c.')
    crop_image(path_in, path_out)
