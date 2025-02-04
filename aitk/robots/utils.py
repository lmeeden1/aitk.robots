# -*- coding: utf-8 -*-
# ************************************************************
# aitk.robots: Python robot simulator
#
# Copyright (c) 2021 AITK Developers
#
# https://github.com/ArtificialIntelligenceToolkit/aitk.robots
# ************************************************************

import glob
import io
import json
import math
import os
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps

from .color_data import COLORS
from .config import get_aitk_search_paths

PI_OVER_180 = math.pi / 180
PI_OVER_2 = math.pi / 2
ONE80_OVER_PI = 180 / math.pi
TWO_PI = math.pi * 2

try:
    from IPython.display import display
except ImportError:
    display = print

def degrees_to_world(degrees):
    return ((TWO_PI - (degrees * PI_OVER_180)) % TWO_PI)

def world_to_degrees(direction):
    return (((direction + TWO_PI) * -ONE80_OVER_PI) % 360)

def rotate_around(x1, y1, length, angle):
    """
    Swing a line around a point.
    """
    return [x1 + length * math.cos(-angle),
            y1 - length * math.sin(-angle)]

def progress_bar(range, show_progress=True, progress_type="tqdm"):
    """
    Wrap a range/iter in a progress bar (or not).
    """
    try:
        import tqdm
        import tqdm.notebook
    except ImportError:
        tqdm = None

    if progress_type is None or tqdm is None or show_progress is False:
        return range
    elif progress_type == "tqdm":
        return tqdm.tqdm(range)
    elif progress_type == "notebook":
        return tqdm.notebook.tqdm(range)
    else:
        return range


def dot(v, w):
    x, y, z = v
    X, Y, Z = w
    return x * X + y * Y + z * Z


def length(v):
    x, y, z = v
    return math.sqrt(x * x + y * y + z * z)


def vector(b, e):
    x, y, z = b
    X, Y, Z = e
    return (X - x, Y - y, Z - z)


def unit(v):
    x, y, z = v
    mag = length(v)
    return (x / mag, y / mag, z / mag)


def scale(v, sc):
    x, y, z = v
    return (x * sc, y * sc, z * sc)


def add(v, w):
    x, y, z = v
    X, Y, Z = w
    return (x + X, y + Y, z + Z)


def ccw(ax, ay, bx, by, cx, cy):
    # counter clockwise
    return ((cy - ay) * (bx - ax)) > ((by - ay) * (cx - ax))


def intersect(ax, ay, bx, by, cx, cy, dx, dy):
    # Return true if line segments AB and CD intersect
    return ccw(ax, ay, cx, cy, dx, dy) != ccw(bx, by, cx, cy, dx, dy) and (
        ccw(ax, ay, bx, by, cx, cy) != ccw(ax, ay, bx, by, dx, dy)
    )


def coefs(p1x, p1y, p2x, p2y):
    A = p1y - p2y
    B = p2x - p1x
    C = p1x * p2y - p2x * p1y
    return [A, B, -C]


def intersect_coefs(L1_0, L1_1, L1_2, L2_0, L2_1, L2_2):
    D = L1_0 * L2_1 - L1_1 * L2_0
    if D != 0:
        Dx = L1_2 * L2_1 - L1_1 * L2_2
        Dy = L1_0 * L2_2 - L1_2 * L2_0
        x1 = Dx / D
        y1 = Dy / D
        return [x1, y1]
    else:
        return None


def intersect_hit(p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y):
    """
    Compute the intersection between two lines.
    """
    # http:##stackoverflow.com/questions/20677795/find-the-point-of-intersecting-lines
    L1 = coefs(p1x, p1y, p2x, p2y)
    L2 = coefs(p3x, p3y, p4x, p4y)
    xy = intersect_coefs(L1[0], L1[1], L1[2], L2[0], L2[1], L2[2])
    # now check to see on both segments:
    if xy:
        lowx = min(p1x, p2x) - 0.1
        highx = max(p1x, p2x) + 0.1
        lowy = min(p1y, p2y) - 0.1
        highy = max(p1y, p2y) + 0.1
        if (lowx <= xy[0] and xy[0] <= highx) and (lowy <= xy[1] and xy[1] <= highy):
            lowx = min(p3x, p4x) - 0.1
            highx = max(p3x, p4x) + 0.1
            lowy = min(p3y, p4y) - 0.1
            highy = max(p3y, p4y) + 0.1
            if lowx <= xy[0] and xy[0] <= highx and lowy <= xy[1] and xy[1] <= highy:
                return xy
    return None


def format_time(time):
    hours = time // 3600
    minutes = (time % 3600) // 60
    seconds = (time % 3600) % 60
    return "%02d:%02d:%04.1f" % (hours, minutes, seconds)


def load_world(filename=None):
    """
    worlds/
        test1/
            worlds/test1/w1.json
            worlds/test1/w2.json
        test2/
            worlds/test2/w1.json
        worlds/w1.json

    """
    from .world import World

    if filename is None:
        print("Searching for aitk.robots config files...")
        for path in get_aitk_search_paths():
            print("Directory:", path)
            files = sorted(
                glob.glob(os.path.join(path, "**", "*.json"), recursive=True),
                key=lambda filename: (filename.count("/"), filename),
            )
            if len(files) > 0:
                for fname in files:
                    basename = os.path.splitext(fname)[0]
                    print("    %r" % basename[len(path) :])
            else:
                print("    no files found")
    else:
        if not filename.endswith(".json"):
            filename += ".json"
        for path in get_aitk_search_paths():
            path_filename = os.path.join(path, filename)
            if os.path.exists(path_filename):
                print("Loading %s..." % path_filename)
                with open(path_filename) as fp:
                    contents = fp.read()
                    config = json.loads(contents)
                    config["filename"] = path_filename
                    world = World(**config)
                    return world
        print("No such world found: %r" % filename)
    return None


def load_image(filename, width=None, height=None):
    from PIL import Image

    pathname = find_resource(filename)
    if pathname is not None:
        image = Image.open(pathname)
        if width is not None and height is not None:
            image = image.resize((width, height))
        return image


def find_resource(filename=None):
    if filename is None:
        print("Searching for aitk.robots files...")
        for path in get_aitk_search_paths():
            files = sorted(glob.glob(os.path.join(path, "*.*")))
            print("Directory:", path)
            if len(files) > 0:
                for filename in files:
                    print("    %r" % filename)
            else:
                print("    no files found")
    else:
        for path in get_aitk_search_paths():
            path_filename = os.path.abspath(os.path.join(path, filename))
            if os.path.exists(path_filename):
                return path_filename
        print("No such file found: %r" % filename)
    return None


def image_to_png(image):
    with io.BytesIO() as fp:
        image.save(fp, format="png")
        return fp.getvalue()


def image_to_gif(image):
    # Leave fp opened
    from PIL import Image

    fp = io.BytesIO()
    image.save(fp, "gif")
    frame = Image.open(fp)
    return frame


def gallery(*images, border_width=1, background_color=(255, 255, 255)):
    """
    Construct a gallery of images
    """
    try:
        from PIL import Image
    except ImportError:
        print("gallery() requires Pillow, Python Image Library (PIL)")
        return

    gallery_cols = math.ceil(math.sqrt(len(images)))
    gallery_rows = math.ceil(len(images) / gallery_cols)

    size = images[0].size
    size = size[0] + (border_width * 2), size[1] + (border_width * 2)

    gallery_image = Image.new(
        mode="RGBA",
        size=(int(gallery_cols * size[0]), int(gallery_rows * size[1])),
        color=background_color,
    )

    for i, image in enumerate(images):
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        location = (
            int((i % gallery_cols) * size[0]) + border_width,
            int((i // gallery_cols) * size[1]) + border_width,
        )
        gallery_image.paste(image, location)
    return gallery_image


class arange:
    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step

    def __iter__(self):
        current = self.start
        if self.step > 0:
            while current <= self.stop:
                yield current
                current += self.step
        else:
            while current >= self.stop:
                yield current
                current += self.step

    def __len__(self):
        return abs(self.stop - self.start) / abs(self.step)


def distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2))


def distance_point_to_line_3d(point, line_start, line_end):
    """
    Compute distance and location to closest point
    on a line segment in 3D.
    """
    line_vec = vector(line_start, line_end)
    point_vec = vector(line_start, point)
    line_len = length(line_vec)
    line_unitvec = unit(line_vec)
    point_vec_scaled = scale(point_vec, 1.0 / line_len)
    t = dot(line_unitvec, point_vec_scaled)
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    nearest = scale(line_vec, t)
    # Optipization: assume 2D:
    dist = distance(nearest[0], nearest[1], point_vec[0], point_vec[1])
    nearest = add(nearest, line_start)
    return (dist, nearest)


def distance_point_to_line(point, line_start, line_end):
    return distance_point_to_line_3d(
        (point[0], point[1], 0),
        (line_start[0], line_start[1], 0),
        (line_end[0], line_end[1], 0),
    )


def json_dump(config, fp, sort_keys=True, indent=4):
    dumps(fp, config, sort_keys=sort_keys, indent=indent)


def dumps(fp, obj, level=0, sort_keys=True, indent=4, newline="\n", space=" "):
    if isinstance(obj, dict):
        if sort_keys:
            obj = OrderedDict({key: obj[key] for key in sorted(obj.keys())})
        fp.write(newline + (space * indent * level) + "{" + newline)
        comma = ""
        for key, value in obj.items():
            fp.write(comma)
            comma = "," + newline
            fp.write(space * indent * (level + 1))
            fp.write('"%s":%s' % (key, space))
            dumps(fp, value, level + 1, sort_keys, indent, newline, space)
        fp.write(newline + (space * indent * level) + "}")
    elif isinstance(obj, str):
        fp.write('"%s"' % obj)
    elif isinstance(obj, (list, tuple)):
        if len(obj) == 0:
            fp.write("[]")
        else:
            fp.write(newline + (space * indent * level) + "[")
            # fp.write("[")
            comma = ""
            for item in obj:
                fp.write(comma)
                comma = ", "
                dumps(fp, item, level + 1, sort_keys, indent, newline, space)
            # each on their own line
            if len(obj) > 2:
                fp.write(newline + (space * indent * level))
            fp.write("]")
    elif isinstance(obj, bool):
        fp.write("true" if obj else "false")
    elif isinstance(obj, int):
        fp.write(str(obj))
    elif obj is None:
        fp.write("null")
    elif isinstance(obj, float):
        fp.write("%.7g" % obj)
    else:
        raise TypeError("Unknown object %r for json serialization" % obj)


class throttle(object):
    """
    Decorator that prevents a function from being called more than once every
    time period.
    To create a function that cannot be called more than once a minute:
        @throttle(minutes=1)
        def my_fun():
            pass
    """

    def __init__(self, seconds=0, minutes=0, hours=0):
        self.throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        self.time_of_last_call = datetime.min

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = datetime.now()
            time_since_last_call = now - self.time_of_last_call

            if time_since_last_call > self.throttle_period:
                self.time_of_last_call = now
                return fn(*args, **kwargs)

        return wrapper


class Color:
    def __init__(self, red, green=None, blue=None, alpha=None):
        self.name = None
        if isinstance(red, str):
            if red.startswith("#"):
                # encoded hex color
                red, green, blue, alpha = self.hex_to_rgba(red)
            else:
                # color name
                self.name = red
                hex_string = COLORS.get(red, "#00000000")
                red, green, blue, alpha = self.hex_to_rgba(hex_string)
        elif isinstance(red, (list, tuple)):
            if len(red) == 3:
                red, green, blue = red
                alpha = 255
            else:
                red, green, blue, alpha = red
        elif isinstance(red, Color):
            red, green, blue, alpha = red.red, red.green, red.blue, red.alpha

        self.red = red
        if green is not None:
            self.green = green
        else:
            self.green = red
        if blue is not None:
            self.blue = blue
        else:
            self.blue = red
        if alpha is not None:
            self.alpha = alpha
        else:
            self.alpha = 255

    def hex_to_rgba(self, hex_string):
        r_hex = hex_string[1:3]
        g_hex = hex_string[3:5]
        b_hex = hex_string[5:7]
        if len(hex_string) > 7:
            a_hex = hex_string[7:9]
        else:
            a_hex = "FF"
        return int(r_hex, 16), int(g_hex, 16), int(b_hex, 16), int(a_hex, 16)

    def __str__(self):
        if self.name is not None:
            return self.name
        else:
            return self.to_hexcode()

    def __repr__(self):
        return "<Color%s>" % (self.to_tuple(),)

    def to_tuple(self):
        return (int(self.red), int(self.green), int(self.blue), int(self.alpha))

    def rgb(self):
        return "rgb(%d,%d,%d)" % (int(self.red), int(self.green), int(self.blue))

    def to_hexcode(self):
        return "#%02X%02X%02X%02X" % self.to_tuple()

    def __add__(self, other):
        new_color = Color(self)
        new_color.red += other.red
        new_color.green += other.green
        new_color.blue += other.blue
        return new_color

    def __truediv__(self, number):
        new_color = Color(self)
        new_color.red /= number
        new_color.green /= number
        new_color.blue /= number
        return new_color


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y

    def __len__(self):
        return 2

    def __repr__(self):
        return "Point(%s,%s)" % (self.x, self.y)

    def copy(self):
        return Point(self.x, self.y)


class Line:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def __repr__(self):
        return "Line(%s,%s)" % (self.p1, self.p2)
