import math
import sys

class Vec2:
    def __init__(self,x_init,y_init):
        self.x = x_init
        self.y = y_init
    def length2(self):
        return self.x * self.x + self.y * self.y
    def length(self):
        return math.sqrt(self.length2())
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    def cross(self, other):
        return self.x * other.y - self.y * other.x
    def normalize(self):
        magnitude = self.length()
        if magnitude > 0:
            self.x /= magnitude
            self.y /= magnitude
        return magnitude
    def equals(self, other, epsilon=10e-4):
        return (self - other).length2() <= epsilon*epsilon
    def __add__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x + other.x, self.y + other.y)
        return Vec2(self.x + other, self.y + other)
    def __sub__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x - other.x, self.y - other.y)
        return Vec2(self.x - other, self.y - other)
    def __div__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x / other.x, self.y / other.y)
        return Vec2(self.x / other, self.y / other)
    def __mul__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x * other.x, self.y * other.y)
        return Vec2(self.x * other, self.y * other)
    def __neg__(self):
        return Vec2(-self.x, -self.y)
    def __rmul__(self, other):
        if isinstance(other, Vec2):
            return Vec2(other.x * self.x, other.y * self.y)
        return Vec2(other * self.x, other * self.y)
    def __repr__(self):
        return self.__str__()
    def __str__(self):
        return "Vec2: ({0}, {1})".format(self.x, self.y)
    @staticmethod
    def max():
        return Vec2(sys.float_info.max, sys.float_info.max)

class Rect:
    def __init__(self):
        self.makeEmpty()
    def setBounds(self, min, max):
        self.min = Vec2(min.x, min.y)
        self.max = Vec2(max.x, max.y)
    def makeEmpty(self):
        self.min = Vec2.max()
        self.max = -Vec2.max()
    def size(self):
        return self.max - self.min
    def center(self):
        return Vec2((self.max.x + self.min.x) * 0.5, (self.max.y + self.min.y) * 0.5)
    def isEmpty(self):
        return self.max.x < self.min.x or self.max.y < self.min.y
    def extend_by(self, point):
        if self.isEmpty():
            self.setBounds(point, point)
        else:
            if point.x < self.min.x:
                self.min.x = point.x
            if point.y < self.min.y:
                self.min.y = point.y
            if point.x > self.max.x:
                self.max.x = point.x
            if point.y > self.max.y:
                self.max.y = point.y
    def contains(self, point):
        return point.x >= self.min.x and point.x <= self.max.x and point.y >= self.min.y and point.y <= self.max.y
    def distance2(self, point):
        """If that squared distance is zero, it means the point touches or is inside the box."""
        size=self.size()
        center=self.center()
        dx = max(abs(center.x - point.x) - size.x / 2, 0)
        dy = max(abs(center.y - point.y) - size.y / 2, 0)
        return dx * dx + dy * dy
    def distance(self, point):
        return math.sqrt(distance2(point))

class SearchGrid:
    def __init__(self, bbox, dims, points):
        self.bbox=bbox
        self.dims=dims
        self.cells = [[] for i in range(self.dims.x * self.dims.y)]
        self.points=points
    def cell_index(self, point):
        idx= (point - self.bbox.min) / self.bbox.size() * self.dims
        return int(idx.x) + int(self.dims.x) * int(idx.y)
    def add_point(self, point):
        cidx=self.cell_index(point)
        for pi in self.cells[cidx]:
            if self.points[pi].equals(point):
                return pi
        self.points.append(point)
        self.cells[cidx].append(len(self.points)-1)
        return len(self.points)-1
    
    
class Drawing:
    class Polyline:
        def __init__(self, drawing):
            self.drawing=drawing
            self.indices=[]
            self.bbox=Rect()
        def point(self, index):
            return self.drawing.points[self.indices[index]]
        def add_point(self, point):
            idx=self.drawing.grid.add_point(point)
            self.indices.append(idx)
            self.bbox.extend_by(point)
        def valid(self):
            return len(self.indices) > 1
        def cleanup(self):
            """Remove all zero length segments"""
            if not self.valid():
                return
            new_indices=[]
            for i in self.indices:
                if len(ind) > 0 and new_indices[-1] == i:
                    continue
                new_indices.append(i)
            self.indices=new_indices
        def is_closed(self):
            """Return True is the polyline is closed (polygon)"""
            return self.indices[0] == self.indices[-1]
        def closest_point(self, point):
            """Return the closest point index and squared distance on the polyline."""
            index = 0
            dist = (self.point(0) - point).length2()
            for i in range(1, len(self.indices)):
                dist2 = (self.point(i) - point).length2()
                if dist2 < dist:
                    dist = dist2
                    index = i
            return index, dist
        def is_inside(point):
            if not is_closed():
                return
            c = False
            for i in range(len(self.indices)-1):
                if ((point(i).y >= point.y ) != (point(i+1).y >= point.y)) and (point.x <= (point(i+1).x - point(i).x) * (point.y - point(i).y) / (point(i+1).y - point(i).y) + point(i).x):
                    c = not c
            return c

    def __init__(self, bbox):
        self.points = []
        self.polylines = []
        self.grid = SearchGrid(bbox, Vec2(10,10), self.points)