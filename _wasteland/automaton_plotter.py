# !/usr/bin/python3

import math

import pygraphviz as pgv
import svgutils as svgut

import example_system


def make_graph(system):
    def explode_location(location):
        return tuple((str(location)[1:-1]).split('|')) if '|' in str(location) else ('unnamed system', 'unnamed location')
    
    def binding_safe_get(pybind_fun_call):
        try:
            return pybind_fun_call()
        except RuntimeError:
            return ''
    
    locations = dict(enumerate(system.locations()))
    
    # TODO GERETTI: get automaton name
    model_name = explode_location(list(locations.values())[0])[0]
    
    graph = pgv.AGraph(
        name=model_name,
        strict=False, directed=True, splines='polyline',
        scale=2.0
    )
    
    for i, loc in locations.items():
        # get location info
        location_name = explode_location(loc)[1]
        # TODO GERETTI: get the variables' names, which get print but can't be retrieved
        # TODO GERETTI: get algebraic function
        dynamic_function = binding_safe_get(lambda: system.dynamic_function(loc))
        algebraic_function = None  # binding_safe_get(lambda: system.algebraic_function(loc))
        graph.add_node(location_name,
                       label=f'<{location_name}<BR />'
                             f'__________<BR /><BR />'
                             f'{dynamic_function} | {algebraic_function}>',
                       shape='circle')
    
    for i, loc in locations.items():
        # possible events when in this location
        for event in system.events(loc):
            # get transaction info
            event_info = {
                # when this event is output in this location, then we know its kind
                'event_kind': binding_safe_get(lambda: system.event_kind(loc, event).name),
                # when this event is not an invariant (es. PERMISSIVE), then it has a triggering guard
                'guard_function': binding_safe_get(lambda: system.guard_function(loc, event)),
                # TODO GERETTI: get invariant function
                # 'invariant_function': safe_get(lambda: system.invariant_function(loc, event)),
                'reset_fun': binding_safe_get(lambda: system.reset_function(loc, event))
            }
            target = system.target(loc, event)
            graph.add_edge(explode_location(loc)[1], explode_location(target)[1],
                           label=f"{event} [{event_info['event_kind'][:3]}]",
                           info=event_info,
                           len=5.0)
    
    # arrange graph in a circular layout, which emphasizes the transitions between locations
    graph.layout('circo')
    # print(graph.string())  # the .dot file (now with layout information)
    
    return graph


def tweak_svg(path, graph):
    def calculate_barycenter(nodes_pos):
        xs = [float(p[0]) for p in nodes_pos]
        ys = [float(p[1]) for p in nodes_pos]
        return [sum(xs) / len(nodes_pos), sum(ys) / len(nodes_pos)]
    
    # massive use of xml.etree.Element from now on
    graph_svg = svgut.transform.fromfile(path)
    ns = graph_svg.root.nsmap
    ns['default'] = ns.pop(None)
    
    def get_xml_group(title):
        return graph_svg.root[0].find(f"*/[default:title='{title}']", ns)
    
    def get_xml_pos(xml_elem):
        if xml_elem.get('x'):
            return float(xml_elem.get('x')), float(xml_elem.get('y'))
        else:
            return float(xml_elem.get('cx')), float(xml_elem.get('cy'))
    
    # align labels to edges
    w, h = (float(v[:-2]) for v in graph_svg.get_size())
    min_x, max_x, min_y, max_y = 0, 0, 0, 0
    has_self_loops = False
    for e in graph.edges():
        distance_from_edge = 18  # TODO heuristics: arbitrary
        xml_edge = get_xml_group(f'{e[0]}->{e[1]}')
        xml_from_node = get_xml_group(e[0]).find('default:ellipse', ns)
        xml_to_node = get_xml_group(e[1]).find('default:ellipse', ns)
        if e[0] != e[1]:
            # this is a classic edge
            from_coord, to_coord = get_xml_pos(xml_from_node), get_xml_pos(xml_to_node)
            
            # get angle w.r.t. this node
            angle = math.atan2(to_coord[1] - from_coord[1], to_coord[0] - from_coord[0])
            # check if the edge is bidirectional
            if graph.has_edge(e[1], e[0]) and angle > 0:
                distance_from_edge *= -1  # it's below
            # keep labels readable
            if angle <= -math.pi / 2:
                angle += math.pi
            if angle >= math.pi / 2:
                angle -= math.pi
            
            # rotate text by calculated angle
            edge_text = xml_edge.find('default:text', ns)
            edge_text.set('x', f'{(to_coord[0] + from_coord[0]) / 2 + distance_from_edge * math.sin(angle)}')
            edge_text.set('y', f'{(to_coord[1] + from_coord[1]) / 2 + 4 - distance_from_edge * math.cos(angle)}')
            edge_text.set('transform', f"rotate({angle / math.pi * 180}, {edge_text.get('x')}, {edge_text.get('y')})")
        else:
            has_self_loops = True
            # this is a self-loop edge
            neigh = set(graph.neighbors(e[0])) - {e[0]}  # can contain itself and two times a node (bidirectional edge), thus the set and the subtraction
            barycenter = calculate_barycenter([get_xml_pos(get_xml_group(n).find('default:ellipse', ns)) for n in neigh])
            node_pos = get_xml_pos(xml_from_node)
            
            # get angle w.r.t. this node
            angle = math.atan2(node_pos[1] - barycenter[1], node_pos[0] - barycenter[0])
            
            loop_edge_width = 15  # TODO heuristics: arbitrary
            node_radius = float(xml_from_node.get('rx'))
            edge_text = xml_edge.find('default:text', ns)
            
            # calculate outer ellipse
            # assuming a 24' 16:9 1920x1080 pixels screen. its dimensions will be 20.9'x11.8', so we have 91.9 x 91.5 pix/inch x pix/inch (mean 91.7 pix/inch)
            text_demiheight = float(edge_text.get('font-size')) / 72 * 91.7  # TODO heuristics: 1pt = 1/72 inch
            outer_ellipse_axis_x = float(edge_text.get('x')) - node_pos[0]  # with circo layout, the y offset will always be 0, thus the heuristics
            text_demiwidth = outer_ellipse_axis_x - loop_edge_width - node_radius
            outer_ellipse_axis_y = text_demiheight + loop_edge_width + node_radius

            # move label along ellipse around node
            new_x = node_pos[0] + outer_ellipse_axis_x * math.cos(-angle)
            new_y = node_pos[1] + outer_ellipse_axis_y * math.sin(-angle)
            edge_text.set('x', f"{new_x}")
            edge_text.set('y', f"{new_y}")
            # rotate arrow path and head of the edge
            xml_edge.find('default:path', ns).set('transform', f"rotate({-angle / math.pi * 180}, {node_pos[0]}, {node_pos[1]})")     # edge path
            xml_edge.find('default:polygon', ns).set('transform', f"rotate({-angle / math.pi * 180}, {node_pos[0]}, {node_pos[1]})")  # edge head
            
            # update the view
            min_x = min(min_x, new_x - text_demiwidth)
            max_x = min(max(max_x, new_x + text_demiwidth, node_pos[0] + node_radius), w)
            min_y = max(min_y, new_y + text_demiheight)  # negative numbers require flipped conditions
            max_y = max(min(max_y, new_y - text_demiheight, node_pos[1] - node_radius), -h)
    
    if has_self_loops:
        # calculate new dimensions
        w = max_x - min_x
        h = -(max_y - min_y)  # negative numbers...
    
    extra_border = 5
    h += extra_border * 2
    w += extra_border * 2
    min_x -= extra_border
    min_y += extra_border
    # set new dimensions
    graph_svg.set_size((f'{int(w)}pt', f'{int(h)}pt'))
    # calculate new viewBox
    graph_svg.root.set('viewBox', f'{min_x} {min_y} {w} {h}')
    # recenter the content
    graph_svg.root[0].set('transform', f'translate({0}, {h})')
    # redraw background
    graph_svg.root[0][1].set('points', f'{min_x},{min_y} '
                                       f'{min_x},{min_y - h} '
                                       f'{min_x + w},{min_y - h} '
                                       f'{min_x + w},{min_y} '
                                       f'{min_x},{min_y}')
    
    # save the result
    graph_svg.save(path)


if __name__ == '__main__':
    
    # TODO GERETTI: CompositeHybridAutomaton is not iterable
    subsystems = ['controller', 'tank', 'valve']
    for subsystem_name in subsystems:
        
        # get automaton of interest
        model = getattr(example_system, f'get_{subsystem_name}')()
        
        # build GraphViz graph
        model_graph = make_graph(model)
        
        # export SVG image of graph
        svg_path = f"plots/graph_{subsystem_name}.svg"
        model_graph.draw(svg_path)
        
        # adjust various GraphViz hiatuses in SVG file
        tweak_svg(svg_path, model_graph)
