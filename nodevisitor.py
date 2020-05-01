import inkex
from inkex import Transform

class NodeVisitor(object):
    """Depth first traversal"""

    def visit_node(self, node, transform):
        pass

    def accept(self, node, transform = Transform([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])):
        def visible(node):
            """Return True if the node is visible."""
            style = inkex.Style.parse_str(node.get('style') or "")
            if 'display' in style and style['display'] == 'none':
                return False
            return True

        def process_node(node, transform):
            if not visible(node):
                return

            transform *= node.transform

            # special case for clones
            if node.tag == '{http://www.w3.org/2000/svg}use':
                refid = node.get('{http://www.w3.org/1999/xlink}href')
                refnodes = node.xpath('//*[@id="{0}"]'.format(refid[1:]))
                if not refnodes:
                    return
                x = float(node.get('x', '0'))
                y = float(node.get('y', '0'))
                if x != 0 or y != 0:
                    transform = composeTransform(transform, parseTransform('translate({0:f},{1:f})'.format(x, y)))
                self.visit_node(refnodes[0], transform)
            else:
                self.visit_node(node, transform)

            for child in node.iterchildren():
                process_node(child, transform)
        
        process_node(node, transform)
