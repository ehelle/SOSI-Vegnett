import requests
import shapely.wkt
from shapely.ops import linemerge, LineString, Point

API = 'https://www.utv.vegvesen.no/nvdb/api/v3/'

print("hello")

def linref2geom(sekvens_nr, fra, til, super = False):
    url = API + "vegnett/veglenkesekvenser/" + str(sekvens_nr)
    json = fetchJson(url)
    lst = []
    fra = float(fra)
    til = float(til)
    for veglenke in json["veglenker"]:
        if super:
            start = float(veglenke['superstedfesting']['startposisjon'])
            slutt = float(veglenke['superstedfesting']['sluttposisjon'])
        else:
            start = float(veglenke['startposisjon'])
            slutt = float(veglenke['sluttposisjon'])
        if within(start, slutt, fra, til):
            lst.append(geom(veglenke))
        elif overlaps(start, slutt, fra, til):
            lst.append(cut(geom(veglenke), veglenke['startposisjon'], veglenke['sluttposisjon'], fra, til))
    #for w in withinLst: print("within: %s", w)
    #for o in overlapsLst: print("overlaps: %s", o)
    merged = linemerge(lst)
    #print("merged: %s", merged)
    return merged

def fetchJson(url):
    resp = requests.get(url)
    if resp.status_code != 200:
        raise requests.exeption.HTTPError(resp.status_code)
    return resp.json()

def overlaps(start, slutt, fra, til):
    return (start <= fra and slutt >= fra) or (start <= til and slutt >= til)

def within(start, slutt, fra, til):
    return start >= fra and slutt <= til

def geom(veglenke):
    wkt = veglenke['geometri']['wkt']
    line = shapely.wkt.loads(wkt)
    #print(line)
    return line

def cut(line, vl_fra, vl_til, obj_fra, obj_til):
    vl_len = vl_til - vl_fra
    if obj_fra <= vl_fra and obj_til >= vl_til:
        return line
    elif obj_fra <= vl_fra and obj_til < vl_til:
        distance = (obj_til - vl_fra) / vl_len
        coords = list(line.coords)
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if pd == distance:
                return LineString(coords[:i+1])
            if pd > distance:
                cp = line.interpolate(distance, normalized=True)
                return LineString(coords[:i] + [(cp.x, cp.y, (coords[i][2] + coords[i+1][2]) / 2)])
    elif obj_fra > vl_fra and obj_til >= vl_til:
        distance = (vl_til - obj_fra) / vl_len
        coords = list(line.coords)
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if pd == distance:
                return LineString(coords[i:])
            if pd > distance:
                cp = line.interpolate(distance, normalized=True)
                return LineString([(cp.x, cp.y, (coords[i][2] + coords[i+1][2]) / 2)] + coords[i:])
    elif obj_fra > vl_fra and obj_til < vl_til:
        dist1 = (vl_til - obj_fra) / vl_len
        dist2 = (obj_til - vl_fra) / vl_len
        coords = list(line.coords)
        start = None
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if start == None:
                if pd == dist1:
                    start = i
                    startP = []
                elif pd > dist1:
                    cp = line.interpolate(dist1, normalized=True)
                    start = i + 1
                    startP [(cp.x, cp.y, (coords[i][2] + coords[i+1][2]) / 2)]
            if pd == dist2:
                return LineString(startP + coords[start:i+1])
            elif pd > dist2:
                cp = line.interpolate(dist2, normalized=True)
                return LineString(startP + coords[start:i] + [(cp.x, cp.y, (coords[i][2] + coords[i+1][2]) / 2)])


if __name__ == '__main__':
    print("test")
    linref2geom(1057086, 0.0, 0.65) #0.72926056)