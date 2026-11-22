import json
tj = json.load(open('assets/land-50m.json'))
sc, tr = tj['transform']['scale'], tj['transform']['translate']
arcs = []
for a in tj['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(pts)
def arc(i): return arcs[i] if i >= 0 else arcs[~i][::-1]
polys = []
for g in tj['objects']['land']['geometries']:
    ps = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
    for p in ps:
        ring = []
        for i in p[0]: ring += arc(i)
        if any(60 < lo < 100 and 0 < la < 40 for lo, la in ring[::5]): polys.append(ring)
json.dump(polys, open('assets/southasia_land.json', 'w'))
print('land polys', len(polys))
