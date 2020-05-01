
import os
import sys
import copy
import inkex
from inkex import Transform
from inkex.ports import Serial
import nodeconverter
from geometry import *
import time

class Planner:
    def join_continuous(self, polylines):
        """Join polylines that are actually continuous"""
        def join(polylines):
            for i in range(len(polylines)-1):
                if polylines[i].is_closed():
                    continue
                e0=polylines[i].indices[0]
                e1=polylines[i].indices[-1]
                for j in range(i+1, len(polylines)):
                    if polylines[j].is_closed():
                        continue
                    e2=polylines[j].indices[0]
                    e3=polylines[j].indices[-1]
                    if e0 == e2 or e0 == e3:
                        polylines[i].indices.reverse()
                        e0, e1 = e1, e0
                    if e1 == e3:
                        polylines[j].indices.reverse()
                        e2, e3 = e3, e2
                    if e1 == e2:
                        polylines[i].indices.extend(polylines[j].indices)
                        del polylines[j]
                        return True
            return False

        while True:
            if not join(polylines):
                return
        for p in polylines:
            p.cleanup()

    def remove_doubles(self, polylines):
        """Remove doubled segments"""
        pass
    def closest_point(self, polyline, point):
        """
        Return the closest point index and squared distance on the polyline.
        If it's a polygon, all the points are considered.
        If not, only the two extremities are considerd.
        """
        if polyline.is_closed():
            return polyline.closest_point(point)
        else:
            index = 0
            dist = (polyline.point(0) - point).length2()
            dist2 = (polyline.point(-1) - point).length2()
            if dist2 < dist:
                dist = dist2
                index = len(polyline.indices) - 1
            return index, dist

    def closest_polyline(self, polylines, point):
        dist = sys.float_info.max
        lindex = -1
        pindex = -1
        for i,p in enumerate(polylines):
            pindex2, dist2 = self.closest_point(p, point)
            if dist2 < dist:
                dist = dist2
                lindex = i
                pindex = pindex2
        return lindex, pindex

    def reorder_polyline(self, polyline, index):
        """Reorder polyline points, making index the new first index."""
        if index == 0:
            return
        if polyline.is_closed():
            new_indices = []
            for i in range(index, len(polyline.indices)-1):
                new_indices.append(polyline.indices[i])
            for i in range(0, index):
                new_indices.append(polyline.indices[i])
            new_indices.append(new_indices[0])
            polyline.indices = new_indices
        elif index == len(polyline.indices)-1:
            polyline.indices.reverse()

    def optimize(self, drawing):
        self.join_continuous(drawing.polylines)
        self.remove_doubles(drawing.polylines)
        start=Vec2(0.0,0.0)
        plst=list(drawing.polylines)
        polylines = []
        while (len(plst) > 0):
            lindex, pindex = self.closest_polyline(plst, start)
            poly=plst[lindex]
            self.reorder_polyline(poly, pindex)
            start = poly.point(-1)
            polylines.append(poly)
            plst.pop(lindex)
        drawing.polylines = polylines

def drawing_to_gcode(drawing, options):
    gcode = ["G90", "G21", "G0 F{}".format(options.travel_speed), "G1 F{}".format(options.laser_speed), "M03 S{}".format(options.laser_off_command)]
    for polyline in drawing.polylines:
        gcode.append('G0 X%s Y%s' % (polyline.point(0).x, polyline.point(0).y))
        gcode.append(options.laser_on_command)
        gcode.append("G4 P{}".format(options.power_delay))
        for p in range(1, len(polyline.indices)):
            gcode.append('G1 X%s Y%s' % (polyline.point(p).x, polyline.point(p).y))
        gcode.append(options.laser_off_command)
        gcode.append("G4 P{}".format(options.power_delay))
    gcode.append('G0 X0 Y0')
    return gcode

class Eggduino(inkex.Effect):
    """
    Example Inkscape effect extension.
    Creates a new layer with a "Hello World!" text centered in the middle of the document.
    """
    def __init__(self):
        inkex.Effect.__init__(self)

        self.arg_parser.add_argument('--laser-on-command', default='M03 S255', help='Laser gcode start command')
        self.arg_parser.add_argument('--laser-off-command', default="M03 S0", help="Laser gcode end command")
        self.arg_parser.add_argument('--laser-speed', type=int, default="100", help="Laser speed (mm/min)")
        self.arg_parser.add_argument('--travel-speed', type=int, default="3000", help="Travel speed (mm/min)")
        self.arg_parser.add_argument('--power-delay', type=int, default="500", help="Laser power-on delay (ms)")

        self.arg_parser.add_argument('--tab')
        self.arg_parser.add_argument('--directory', default="", help="Output directory")
        self.arg_parser.add_argument('--filename', default="output.gcode", help="File name")
        self.arg_parser.add_argument('--serialPort', default='/dev/cu.wchusbserial410',  help='Serial port')
        self.arg_parser.add_argument('--serialBaudRate',  default='115200',  help='Serial Baud rate')
     
    def effect(self):
        w = self.svg.width
        h = self.svg.height
        s = 1 / self.svg.unittouu('1mm')
        w = w * s
        h = h * s

        #print(f"w: {w} h: {h} s: {s}", file=sys.stderr)
        bbox=Rect()
        bbox.setBounds(Vec2(0,0), Vec2(w,h))
        converter=nodeconverter.NodeToPolylines(bbox)
        converter.accept(self.document.getroot(), Transform([[s, 0.0, 0.0], [0.0, -s, h]]))
        planner=Planner()
        planner.optimize(converter.drawing)
        gcode=drawing_to_gcode(converter.drawing, self.options)

        if self.options.tab == 'filetab':
            filename=os.path.join(os.path.abspath(os.path.expanduser(self.options.directory)), os.path.splitext(self.options.filename)[0]+'.gcode')
            with open(filename, 'w') as f:
                f.write('\n'.join(gcode))
        elif self.options.tab == 'serialtab':
            # Open serial port
            try:
                serial = Serial(self.options.serialPort, self.options.serialBaudRate, timeout=None)

                # Wake up grbl
                serial.write("\r\n\r\n")
                time.sleep(2)   # Wait for grbl to initialize
                serial.flushInput()  # Flush startup text in serial input

                # Stream g-code
                for line in gcode:
                	serial.write(line + '\n') # Send g-code block
                	grbl_out = serial.readline() # Wait for response with carriage return
                time.sleep(2)
                # Close serial port
                serial.close()
            except (OSError, serial.SerialException):
                inkex.errormsg(_("Problem connecting to serial device."))



if __name__ == '__main__':
    Eggduino().run()