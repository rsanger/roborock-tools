#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2020 Richard Sanger
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
A tool to open, modify and convert raw roborock S5 maps

For Roborock S5 maps from:
/mnt/data/rockrobo/last_map
/mnt/data/rockrobo/user_map0 (if persistent map set)

Firmware Version: 3.3.9_001886


Map file format:

Header 40 bytes
Map Data (width x height x 4 bytes)
MD5 hash of Map Data 4 bytes

Header Layout:
In bytes
0            4            8            12
+------------+------------+------------+------------+
| 0x83e82942 | 0x83e8d8be | 0xcf86ad3d | 0xa675a941 |
+------------+------------+------------+------------+
16           20           24           28
+------------+------------+------------+------------+
| 0xa6752942 | 0x0000a041 | 0x6effffff | 0x4fffffff |
+------------+------------+------------+------------+
First 28 bytes unknown purpose but seem to be constant

Bytes 28 - 32 vary, I have also seem 0x57ffffff, maybe this counts updates to the map?

32           36           40
+------------+------------+~~~~~~~~~~~~~~~
|   width    |   height   |  Map data ...
+------------+------------+~~~~~~~~~~~~~~~

Map Data Layout:

What I've found:
* Each pixel is represented as 4 bytes
* When viewed a RGBA, the Alpha channel clearly shows walls
  * A simple threashold can be used to find floor vs. walls
  * All 4 bytes are 0 if the pixel is unexplored/no data
  * Walls and floors don't all have the exact same value,
    even when considering only the alpha channel
* The vacuum adds to the each pixel with each LIDAR pass

Hash:
The hash at the end of the file is a simple md5 hash over the map data,
saved in the last 16 bytes.


"""
from __future__ import print_function
from array import array
from hashlib import md5
import argparse

assert array('I').itemsize == 4
# Default pixel values to fill in pixels
RR_FLOOR = 0xc22b2776  # get_pixel(149, 164)
RR_WALL = 0x422975a6  # get_pixel(149, 161)
RR_UNEXPLORED = 0


class RoborockMap:
    _map = None
    width = None
    height = None
    header = None
    checksum = None

    def __init__(self, path, verbose=False):
        """ Loads the map from the file path """
        self.header = array('I')
        self._map = array('I')
        self.checksum = array('I')
        with open(path, 'rb') as f:
            self.header.fromfile(f, 10)
            self.width = self.header[8]
            self.height = self.header[9]
            self._map.fromfile(f, self.width*self.height)
            self.checksum.fromfile(f, 4)

        if self.calc_map_checksum() != self.checksum:
            print("Warning: incorrect checksum found")

        if verbose:
            print("Successfully loaded map:")
            print("\tWidth:", self.width)
            print("\tHeight:", self.height)
            print()
            self.print_gimp()
            print()

    def get_pixel(self, x, y):
        """ Get the value of a pixel in the map

            return: An integer
        """
        return self._map[y*self.width+x]

    def set_pixel(self, x, y, value):
        """ Set the value of a pixel in the map

            value: The value to set as an integer
        """
        self._map[y*self.width+x] = value

    def set_rect(self, rect, value):
        """ Overwrite the pixels in an area of the map

            rect: a tuple (x left, y top, x right, y bottom) inclusive
            value: an integer to set
        """
        for x in range(rect[0], rect[2]+1):
            for y in range(rect[1], rect[3]+1):
                self.set_pixel(x, y, value)

    def set_rect_border(self, rect, value):
        """ Draw of border on the map

            rect: a tuple (x left, y top, x right, y bottom) inclusive
                  use x left == x right to draw a line (or y ...)
            value: an integer to set
        """
        for x in range(rect[0], rect[2]+1):
            for y in (rect[1], rect[3]):
                self.set_pixel(x, y, value)
        for y in range(rect[1], rect[3]+1):
            for x in (rect[0], rect[2]):
                self.set_pixel(x, y, value)

    def calc_map_checksum(self):
        """ Calculates the checksum for the current map

            return: The checksum as an integer array
        """
        m = md5()
        m.update(self._map)
        return array('I', m.digest())

    def update_checksum(self):
        """ Updates the checksum based on the current map

            return: None. But, self.checksum will be updated
        """
        self.checksum = self.calc_map_checksum()

    def to_file(self, f):
        """ Write back to a file in the Roborock format

            f: The output file object (open as 'wb')
        """
        self.update_checksum()
        self.header.tofile(f)
        self._map.tofile(f)
        self.checksum.tofile(f)

    def to_png(self, f):
        """ Writes the map as a png

            f: The output file object (open as 'wb')
        """
        import png
        # order per classify_pixel: Unexplored, Floor, Wall
        palette = [(48, 146, 239), (87, 174, 255), (173, 223, 255)]
        png_writer = png.Writer(width=self.width, height=self.height,
                                palette=palette)
        png_writer.write_array(f, tuple(map(self.classify_pixel, self._map)))

    def print_gimp(self):
        """ Print how to view the file in GIMP """
        print("To open the raw map in GIMP:")
        print("\t\tOpen the file as type Raw image data")
        print("\tIn dialog:")
        print("\t\tImage Type: RGB Alpha")
        print("\t\tOffset: 40")
        print("\t\tWidth:", str(self.width))
        print("\t\tHeight:", str(self.height))
        print("\t\tOpen")
        print("\tView walls on the map through Colors->Components->Decompose:")
        print("\t\tColor model RGBA")
        print("\t\tOK")
        print("\tNow hide layers other than the alpha channel, the alpha channel shows walls.")
        print("NOTE when viewing in GIMP the map is mirrored vertically vs the app.")

    @staticmethod
    def classify_pixel(value):
        """ return: 0 if unexplored, 1 if floor, 2 if wall

            value: The integer value of the pixel (from get_pixel() etc.)
        """
        # This might not be 'correct', but checking the MSB works
        if value & 0x80000000:
            return 1
        elif value:
            return 2
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='A script to load, edit and convert a raw Roborock vacuum map')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="print additional info about the map and how to "
                             "open as a raw image in GIMP")
    parser.add_argument('--png', '-p',
                        help="The file path to output the map as a PNG")
    parser.add_argument('--output', '-o',
                        help="The output filepath")
    parser.add_argument('--set-unexplored', '-u', action="append", default=[],
                        help="Mark a rectangular area as unexplored.\n"
                             "Takes a comma separated list of 4 items x1,y1,x2,y2.\n"
                             "E.g. --set-unexplored 0,0,20,10")
    parser.add_argument('--set-floor', '-f', action="append", default=[],
                        help="Mark a rectangular area as floor")
    parser.add_argument('--set-wall', '-w', action="append", default=[],
                        help="Mark a rectangle border as wall")
    parser.add_argument('map', help="the path to the map (input)")

    args = parser.parse_args()

    rr_map = RoborockMap(args.map, args.verbose)

    for rect in args.set_unexplored:
        parsed = tuple(map(int, rect.split(',')))
        assert len(parsed) == 4
        rr_map.set_rect(parsed, RR_UNEXPLORED)

    for rect in args.set_floor:
        parsed = tuple(map(int, rect.split(',')))
        assert len(parsed) == 4
        rr_map.set_rect(parsed, RR_FLOOR)

    for rect in args.set_wall:
        parsed = tuple(map(int, rect.split(',')))
        assert len(parsed) == 4
        rr_map.set_rect_border(parsed, RR_WALL)

    if args.png:
        with open(args.png, "wb") as f_png:
            rr_map.to_png(f_png)

    if args.output:
        with open(args.output, "wb") as f_out:
            rr_map.to_file(f_out)

if __name__ == "__main__":
    main()
