import xml.etree.ElementTree as ET

class PetriNet: 
    def __init__(self): 
        self.places = {} # id => initialMark
        self.transitions = [] # list of ids
        self.arcs = [] # (src, tgt)

    def parse_pnml(path): 
        tree = ET.parse(path)
        root = tree.getroot()

        net = PetriNet()

        namespace = "{http://www.pnml.org/version-2009/grammar/pnml}"

        netNode = root.find(f"{namespace}net")

        # parse places
        for p in netNode.findall(f"{namespace}transition"):
            tid = t.get("id")
            net.transitions.append(tid)

        # parse arcs
        for a in netNode.findall(f"{namespace}arc"):
            src = a.get("source")
            tgt = a.get("target")
            net.arcs.append((src, tgt))

        return net
    
    

        