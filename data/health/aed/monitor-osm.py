# encoding: utf8

"""
This script watches the Cologne area for
AED entries and looks for matches in our
aed.csv source

If no changes are detected, no output occurs.

Examples of change notices:

OSM ID 621969295, our ID 67: position is: x=6.9793727, y=51.0022035, distance: 7.25 m
OSM ID 2920841194 is not in aed.csv:
{
    "changeset": 22991636, 
    "uid": 16478, 
    "tags": {
        "description": "An der Kasse", 
        "emergency": "defibrillator"
    }, 
    "timestamp": "2014-06-17T19:40:12Z", 
    "lon": 6.9505214, 
    "version": 1, 
    "user": "Raymond", 
    "lat": 50.9348959, 
    "type": "node", 
    "id": 2920841194
}
OSM ID 766067626 (our ID 123) is no longer an AED node in OSM

-----

Dieses Script lädt Defibrillatoren-Daten
innerhalb der Kölner Stadtgrenzen und prüft,
ob diese in unserer Quelle aed.csv enthalten
sind.
"""

import sys
import json
import csv
import requests
from bs4 import BeautifulSoup
from shapely.geometry import Polygon, Point
import util


def load_osm_aeds():
    xml = """<osm-script output="json" timeout="25">
      <query type="node">
        <has-kv k="emergency" v="defibrillator"/>
        <bbox-query n="51.2" e="7.2" s="50.8" w="6.7" />
      </query>
      <print mode="meta"/>
    </osm-script>"""
    bounds = util.get_bounds()
    out = {}
    r = requests.post("http://overpass-api.de/api/interpreter", data=xml)
    for item in r.json()["elements"]:
        position = Point([item["lon"], item["lat"]])
        if bounds.contains(position):
            out[str(item["id"])] = item
    return out


def find_changes(aeds, osm_aeds):
    """
    Check which OSM nodes have been modified
    """
    for osm_id in osm_aeds.keys():
        found = False
        changes = []
        our_mapped_id = None
        for aed in aeds:
            if str(osm_id) == str(aed["osm_node_id"]):
                found = True
                our_mapped_id = aed["osm_node_id"]
                #print("OSM node %s maps to our ID %s" % (osm_id, aed["id"]))
                # check difference
                if (str(osm_aeds[osm_id]["lon"]) != str(aed["longitude"]) or 
                    str(osm_aeds[osm_id]["lat"]) != str(aed["latitude"])):
                    # distance form our to OSM position
                    dist = util.distance(osm_aeds[osm_id]["lon"],
                            osm_aeds[osm_id]["lat"],
                            aed["longitude"], aed["latitude"])
                    if dist > 0.1:
                        sys.stderr.write("OSM ID %s, our ID %s: position is: x=%s, y=%s, distance: %.2f m\n" % (
                            osm_id, aed["id"], osm_aeds[osm_id]["lon"],
                            osm_aeds[osm_id]["lat"], dist))
                        changes.append("position")
                continue
        #if changes != []:

        if not found:
            sys.stderr.write("OSM ID %s is not in aed.csv:\n" % osm_id)
            sys.stderr.write(json.dumps(osm_aeds[osm_id], indent=4))

    # other way around: check which OSM nodes have been deleted
    for aed in aeds:
        if aed["osm_node_id"] is None:
            continue
        osm_id = str(aed["osm_node_id"])
        if osm_id == "":
            continue
        if osm_id not in osm_aeds:
            sys.stderr.write("OSM ID %s, our ID %s, is no longer an AED node in OSM\n" % (
                osm_id, aed["id"]))


if __name__ == "__main__":
    aeds = util.load_csv_aeds()
    osm_aeds = load_osm_aeds()
    find_changes(aeds, osm_aeds)
