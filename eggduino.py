
import os
import sys
import copy
import inkex
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

        self.OptionParser.add_option("--laser-on-command", action="store", type="string", dest="laser_on_command", default="M03 S255", help="Laser gcode start command")
        self.OptionParser.add_option("--laser-off-command", action="store", type="string", dest="laser_off_command", default="M03 S0", help="Laser gcode end command")
        self.OptionParser.add_option("--laser-speed", action="store", type="int", dest="laser_speed", default="100", help="Laser speed (mm/min)")
        self.OptionParser.add_option("--travel-speed", action="store", type="string", dest="travel_speed", default="3000", help="Travel speed (mm/min)")
        self.OptionParser.add_option("--power-delay", action="store", type="string", dest="power_delay", default="500", help="Laser power-on delay (ms)")

        self.OptionParser.add_option("--tab", action="store", type="string", dest="tab")
        self.OptionParser.add_option("--directory", action="store", type="string", dest="directory", default="", help="Output directory")
        self.OptionParser.add_option("--filename", action="store", type="string", dest="file", default="output.gcode", help="File name")
        self.OptionParser.add_option('--serialPort', action='store', type='string',  dest='serialPort', default='/dev/cu.wchusbserial410',  help='Serial port')
        self.OptionParser.add_option('--serialBaudRate',  action='store', type='string',  dest='serialBaudRate',  default='115200',  help='Serial Baud rate')
     
    def effect(self):
        w = self.unittouu(self.getDocumentWidth())
        h = self.unittouu(self.getDocumentHeight())
        s = 1 / self.unittouu('1mm')
        w = w * s
        h = h * s

        #print >>sys.stderr, "w:"+str(w)+" h:"+str(h)+" s:"+str(s)
        bbox=Rect()
        bbox.setBounds(Vec2(0,0), Vec2(w,h))
        converter=nodeconverter.NodeToPolylines(bbox)
        converter.accept(self.document.getroot(), [[s, 0.0, 0.0], [0.0, -s, h]])
        planner=Planner()
        planner.optimize(converter.drawing)
        gcode=drawing_to_gcode(converter.drawing, self.options)

        if self.options.tab == '"filetab"':
            filename=os.path.join(os.path.abspath(os.path.expanduser(self.options.directory)), os.path.splitext(self.options.file)[0]+'.gcode')
            with open(filename, 'w') as f:
                f.write('\n'.join(gcode))
        elif self.options.tab == '"serialtab"':
            # gracefully exit script when pySerial is missing
            try:
                import serial
            except ImportError, e:
                inkex.errormsg(_("pySerial is not installed. Please follow these steps:")
                    + "\n\n" + _("1. Download and extract (unzip) this file to your local harddisk:")
                    + "\n"   +   "   https://pypi.python.org/packages/source/p/pyserial/pyserial-2.7.tar.gz"
                    + "\n"   + _("2. Copy the \"serial\" folder (Can be found inside the just extracted folder)")
                    + "\n"   + _("   into the following Inkscape folder: C:\\[Program files]\\inkscape\\python\\Lib\\")
                    + "\n"   + _("3. Close and restart Inkscape."))
                return

            # Open serial port
            try:
                s = serial.Serial(self.options.serialPort, self.options.serialBaudRate, timeout=None)

                # Wake up grbl
                s.write("\r\n\r\n")
                time.sleep(2)   # Wait for grbl to initialize
                s.flushInput()  # Flush startup text in serial input

                # Stream g-code
                for line in gcode:
                	s.write(line + '\n') # Send g-code block
                	grbl_out = s.readline() # Wait for response with carriage return
                time.sleep(2)
                # Close serial port
                s.close()
            except (OSError, serial.SerialException):
                inkex.errormsg(_("Problem connecting to serial device."))



if __name__ == '__main__':
    effect = Eggduino()
    effect.affect()