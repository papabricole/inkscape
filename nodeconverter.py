import nodevisitor
import simpletransform
import cubicsuperpath
import cspsubdiv
from geometry import *

class NodeToPolylines(nodevisitor.NodeVisitor):
    def __init__(self, bbox):
        self.flatness = 0.2
        self.drawing = Drawing(bbox)

    def visit_node(self, node, transform):
        if node.tag == '{http://www.w3.org/2000/svg}path':
            d = node.get('d')
            if not d:
                return
        elif node.tag == '{http://www.w3.org/2000/svg}rect':
            x = float(node.get('x', 0))
            y = float(node.get('y', 0))
            width = float(node.get('width'))
            height = float(node.get('height'))
            d = "m %s,%s %s,%s %s,%s %s,%s z" % (x, y, width, 0, 0, height, -width, 0)
        elif node.tag == '{http://www.w3.org/2000/svg}line':
            x1 = float(node.get('x1', 0))
            x2 = float(node.get('x2', 0))
            y1 = float(node.get('y1', 0))
            y2 = float(node.get('y2', 0))
            d = "M %s,%s L %s,%s" % (x1, y1, x2, y2)
        elif node.tag == '{http://www.w3.org/2000/svg}circle':
            cx = float(node.get('cx', 0))
            cy = float(node.get('cy', 0))
            r = float(node.get('r'))
            d = "m %s,%s a %s,%s 0 0 1 %s,%s %s,%s 0 0 1 %s,%s z" % (cx + r, cy, r, r, -2*r, 0, r, r, 2*r, 0)
        elif node.tag == '{http://www.w3.org/2000/svg}ellipse':
            cx = float(node.get('cx', 0))
            cy = float(node.get('cy', 0))
            rx = float(node.get('rx'))
            ry = float(node.get('ry'))
            d = "m %s,%s a %s,%s 0 0 1 %s,%s %s,%s 0 0 1 %s,%s z" % (cx + rx, cy, rx, ry, -2*rx, 0, rx, ry, 2*rx, 0)
        else:
            return

        p = cubicsuperpath.parsePath(d)

        simpletransform.applyTransformToPath(transform, p)

        cspsubdiv.cspsubdiv(p, self.flatness)

        for sub in p:
            polyline = Drawing.Polyline(self.drawing)

            prev=None
            for s in sub:
                point=Vec2(s[1][0],s[1][1])            
                # filter out zero length segments
                if prev and prev.equals(point):
                    continue
                polyline.add_point(point)
                prev=point
            
            if polyline.valid():
                self.drawing.polylines.append(polyline)

    def accept(self, node, transform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]):
        self.polylines = []
        super(NodeToPolylines, self).accept(node, transform)