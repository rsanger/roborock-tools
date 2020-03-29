# roborock-tools
Tools for working with a rooted Roborock S5


### editmap.py

At tool to open, edit and convert raw Roborock LIDAR maps.

That is a map from (on a rooted vacuum):
/mnt/data/rockrobo/last\_map
/mnt/data/rockrobo/user\_map0 (if persistent map set)

Firmware Version: 3.3.9\_001886

See the file for the map format details.

```
usage: edit_map.py [-h] [--verbose] [--png PNG] [--output OUTPUT]
                   [--set-unexplored SET_UNEXPLORED] [--set-floor SET_FLOOR]
                   [--set-wall SET_WALL]
                   map

A script to load, edit and convert a raw Roborock vacuum map

positional arguments:
  map                   the path to the map (input)

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         print additional info about the map and how to open as
                        a raw image in GIMP
  --png PNG, -p PNG     The file path to output the map as a PNG
  --output OUTPUT, -o OUTPUT
                        The output filepath
  --set-unexplored SET_UNEXPLORED, -u SET_UNEXPLORED
                        Mark a rectangular area as unexplored. Takes a comma
                        separated list of 4 items x1,y1,x2,y2. E.g. --set-
                        unexplored 0,0,20,10
  --set-floor SET_FLOOR, -f SET_FLOOR
                        Mark a rectangular area as floor
  --set-wall SET_WALL, -w SET_WALL
                        Mark a rectangle border as wall
```


### License

MIT
