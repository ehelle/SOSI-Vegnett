import requests
import shapely.wkt
from shapely.ops import linemerge, LineString, Point
from functools import reduce
import re

API = 'https://www.utv.vegvesen.no/nvdb/api/v3/'
#API = 'https://nvdbw01.kantega.no/nvdb/api/v3/'

def linref2geom(sekvens_nr, fra, til, retning):
    url = API + "vegnett/veglenkesekvenser/" + str(sekvens_nr)
    json = fetchJson(url)
    lst = []
    fra = float(fra)
    til = float(til)
    for veglenke in json["veglenker"]:
        if 'sluttdato' in veglenke or veglenke['detaljnivå'] == 'Vegtrase':
            continue
        start = float(veglenke['startposisjon'])
        slutt = float(veglenke['sluttposisjon'])
        if within(start, slutt, fra, til):
            lst.append({
            'start': start,
            'slutt': slutt,
            'veglenkesekvens': sekvens_nr,
            'retning': retning,
            'geom': [geom(veglenke)]
            }) 
        elif overlaps(start, slutt, fra, til):
            lst.append({
            'start': max(start, fra),
            'slutt': min(slutt, til),
            'veglenkesekvens': sekvens_nr,
            'retning': retning,
            'geom': [cut(geom(veglenke), start, slutt, fra, til)]
            })

    lst = sorted(lst, key = lambda x: x['start'])
    if len(lst) > 1:
        lst = reduce(mergeRef, [[lst[0]]] + lst[1:])

    for obj in lst:
        geo = linemerge(obj['geom'])
        if geo.geom_type == 'MultiLineString':
            geo = fixMulti(geo)            
        obj['geom'] = geo
        print('start: %s, slutt: %s\n' % (obj['start'], obj['slutt']))
        print('geom : %s' % obj['geom'])
    return lst

def fixMulti(geo):
    fst = list(geo[0].coords)
    lst = list(geo[-1].coords)
    if isCircular(fst):
        fst[0] = (fst[0][0] + 0.01, fst[0][1], fst[0][2])
    if isCircular(lst[-1]):
        lst[-1] = (lst[-1][0] + 0.01, lst[-1][1], lst[-1][2])
    return linemerge([LineString(fst)] + [x for x in geo[1:-2]] + [LineString(lst)])

def isCircular(line):
    return line[0] == line[-1]

def mergeRef(o1, o2):
    if o1[-1]['slutt'] == o2['start'] and o1[-1]['veglenkesekvens'] == o2['veglenkesekvens']:
        o1[-1]['slutt'] = o2['slutt']
        o1[-1]['geom'] = o1[-1]['geom'] + o2['geom']
    else:
        o1.append(o2)
    return o1

def super2geom(sekvens_nr, fra, til, retning):
    url = API + "vegnett/veglenkesekvenser?superid=" + str(sekvens_nr)
    json = fetchJson(url)
    lst = []
    fra = float(fra)
    til = float(til)
    for sekv in json['objekter']:
        veglenkesekvensid = sekv['veglenkesekvensid']
        for veglenke in sekv["veglenker"]:
            if 'sluttdato' in veglenke or not riktigRetning(veglenke, retning):
                continue
            start = float(veglenke['superstedfesting']['startposisjon'])
            slutt = float(veglenke['superstedfesting']['sluttposisjon'])
            if within(start, slutt, fra, til):
                lst.append({
                'start': veglenke['startposisjon'],
                'slutt': veglenke['sluttposisjon'],
                'veglenkesekvens': veglenkesekvensid,
                'retning': retning,
                'geom': [geom(veglenke)]
                }) 
            elif overlaps(start, slutt, fra, til):
                lst.append({
                'start': superstedfesting2veglenke(max(start, fra), start, slutt, float(veglenke['startposisjon']), float(veglenke['sluttposisjon'])),
                'slutt': superstedfesting2veglenke(min(slutt, til), start, slutt, float(veglenke['startposisjon']), float(veglenke['sluttposisjon'])),
                'veglenkesekvens': veglenkesekvensid,
                'retning': retning,
                'geom': [cut(geom(veglenke), start, slutt, fra, til)]
                })

    lst = sorted(lst, key = lambda x: (x['veglenkesekvens'], x['start']))
    if len(lst) > 1:
        lst = reduce(mergeRef, [[lst[0]]] + lst[1:])

    for obj in lst:
        geo = linemerge(obj['geom'])
        if geo.geom_type == 'MultiLineString':
            geo = fixMulti(geo)            
        obj['geom'] = geo
        print('xstart: %s, slutt: %s\n' % (obj['start'], obj['slutt']))
        print('xgeom : %s' % obj['geom'])
    return lst

def linref2all(sekvens_nr, fra, til, retning):
    return linref2geom(sekvens_nr, fra, til, retning) + super2geom(sekvens_nr, fra, til, retning)

def riktigRetning(veglenke, retning):
    felt = veglenke['superstedfesting']['kjørefelt'][0] # fix for bokstaver eks 1H
    #print('felt: %s\nretning: %s\n' % (felt,retning))
    return bool(int(felt) % 2) == (retning == 'MED') #oddetall og med eller partall og mot
    

def superstedfesting2veglenke(stedf, s_start, s_slutt, v_start, v_slutt):
    scale = (s_slutt - s_start) / (v_slutt - v_start)
    return ((stedf - s_start) / scale) + v_start

def passesTests(veglenke):
    return 'sluttdato' not in veglenke and \
        veglenke['detaljnivå'] != 'Vegtrase'

def fetchJson(url):
    resp = requests.get(url)
    if resp.status_code != 200:
        raise requests.exeption.HTTPError(resp.status_code)
    return resp.json()

def overlaps(start, slutt, fra, til):
    return (start >= fra and start < til) or (slutt > fra and slutt <= til)

def within(start, slutt, fra, til):
    return start >= fra and slutt <= til

def geom(veglenke):
    wkt = veglenke['geometri']['wkt']
    simpledec = re.compile(r"\d+\.\d+")
    wkt = re.sub(simpledec, mround, wkt)
    line = shapely.wkt.loads(wkt)
    return line

def mround(match): 
    return "{:.2f}".format(float(match.group()))

def almostEqual(a, b, tolerance = 0.01):
    return abs(a - b) >= tolerance

def cut(line, vl_fra, vl_til, obj_fra, obj_til):
    print('vl_fra: %s, vl_til: %s, obj_fra: %s, obj_til: %s' % (vl_fra, vl_til, obj_fra, obj_til))
    vl_len = vl_til - vl_fra
    if obj_fra <= vl_fra and obj_til >= vl_til:
        return line
    elif obj_fra <= vl_fra and obj_til < vl_til:
        distance = (obj_til - vl_fra) / vl_len
        coords = list(line.coords)
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if almostEqual(pd, distance):
                return LineString(coords[:i+1])
            if pd > distance:
                cp = line.interpolate(distance, normalized=True)
                return LineString(coords[:i] + [(cp.x, cp.y, (coords[i-1][2] + coords[i][2]) / 2)])
    elif obj_fra > vl_fra and obj_til >= vl_til:
        distance = (vl_til - obj_fra) / vl_len
        coords = list(line.coords)
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if almostEqual(pd, distance):
                return LineString(coords[i:])
            if pd > distance:
                cp = line.interpolate(distance, normalized=True)
                return LineString([(cp.x, cp.y, (coords[i-1][2] + coords[i][2]) / 2)] + coords[i:])
    elif obj_fra > vl_fra and obj_til < vl_til:
        dist1 = (vl_til - obj_fra) / vl_len
        dist2 = (obj_til - vl_fra) / vl_len
        coords = list(line.coords)
        start = None
        for i, p in enumerate(coords):
            pd = line.project(Point(p), normalized=True)
            if start == None:
                if almostEqual(pd, dist1):
                    start = i
                    startP = []
                elif pd > dist1:
                    cp = line.interpolate(dist1, normalized=True)
                    start = i + 1
                    startP [(cp.x, cp.y, (coords[i-1][2] + coords[i][2]) / 2)]
            if almostEqual(pd, dist2):
                return LineString(startP + coords[start:i+1])
            elif pd > dist2:
                cp = line.interpolate(dist2, normalized=True)
                return LineString(startP + coords[start:i] + [(cp.x, cp.y, (coords[i-1][2] + coords[i][2]) / 2)])


if __name__ == '__main__':
    #linref2geom(705275, 0.0, 0.16063818)
    #super2geom(705275, 0.0, 0.16063818)
    linref2all(1002615, 0.0, 0.0022977, 'MOT')