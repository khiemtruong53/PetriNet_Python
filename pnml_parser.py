# pnml_parser.py
########### task 1 + 2 ##############################
#####################################################
import xml.etree.ElementTree as ET
from typing import Set, List, Tuple, Dict, FrozenSet
from collections import deque

class PetriNet:
    def __init__(self):
        self.places: Set[str] = set()
        self.transitions: Set[str] = set()
        self.arcs: List[Tuple[str, str]] = []
        self.name: str = ""
        self.initial_marking: Set[str] = set()
        self.preset: Dict[str, Set[str]] = {}
        self.postset: Dict[str, Set[str]] = {}

    def add_place(self, pid: str):
        if pid in self.places or pid in self.transitions:
            raise ValueError(f"Duplicate node ID: {pid}")
        self.places.add(pid)
        self.preset[pid] = set()
        self.postset[pid] = set()

    def add_transition(self, tid: str):
        if tid in self.transitions or tid in self.places:
            raise ValueError(f"Duplicate node ID: {tid}")
        self.transitions.add(tid)
        self.preset[tid] = set()
        self.postset[tid] = set()

    def add_arc(self, src: str, tgt: str):
        if src not in self.places and src not in self.transitions:
            raise ValueError(f"Arc source '{src}' not defined")
        if tgt not in self.places and tgt not in self.transitions:
            raise ValueError(f"Arc target '{tgt}' not defined")
        if (src in self.places and tgt in self.places) or \
           (src in self.transitions and tgt in self.transitions):
            raise ValueError(f"Invalid arc type: {src} → {tgt}")

        self.arcs.append((src, tgt))
        self.postset[src].add(tgt)
        self.preset[tgt].add(src)

    def set_initial_marking(self, place_id: str, tokens: int):
        if tokens > 1:
            print(f"Warning: place {place_id} has marking {tokens}, treating as 1.")
        if tokens > 0:
            self.initial_marking.add(place_id)

    def is_enabled(self, transition: str, marking: FrozenSet[str]) -> bool:
        return all(p in marking for p in self.preset[transition])

    def fire(self, transition: str, marking: FrozenSet[str]) -> FrozenSet[str]:
        if not self.is_enabled(transition, marking):
            raise RuntimeError(f"Transition {transition} is not enabled!")
        new_marking = (marking - self.preset[transition]) | self.postset[transition]
        return frozenset(new_marking)

    def get_reachable_markings(self) -> List[FrozenSet[str]]:
        if not self.places:
            return []

        initial = frozenset(self.initial_marking)
        visited = {initial}
        queue = deque([initial])
        result = [initial]  # <-- giữ thứ tự

        while queue:
            m = queue.popleft()
            # Duyệt transitions theo thứ tự xác định (dùng sorted)
            for t in sorted(self.transitions):  # <-- đảm bảo reproducible
                if self.is_enabled(t, m):
                    next_m = self.fire(t, m)
                    if next_m not in visited:
                        visited.add(next_m)
                        queue.append(next_m)
                        result.append(next_m)

        return result

    def __repr__(self):
        places = "{" + ", ".join(sorted(self.places)) + "}"
        trans = "{" + ", ".join(sorted(self.transitions)) + "}"
        arcs = ", ".join(f"{s}→{t}" for s, t in self.arcs)
        init = "{" + ", ".join(sorted(self.initial_marking)) + "}"
        return f"PetriNet(name='{self.name}', places={places}, transitions={trans}, arcs=[{arcs}], initial={init})"


def parse_pnml(file_path: str) -> PetriNet:
    try:
        tree = ET.parse(file_path)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")

    root = tree.getroot()
    for elem in root.iter():
        if elem.tag.startswith("{"):
            elem.tag = elem.tag.split("}", 1)[1]

    net_elem = root.find(".//net")
    if net_elem is None:
        raise ValueError("No <net> found")

    net = PetriNet()
    net.name = net_elem.get("id", "unnamed")

    for p in net_elem.findall(".//place"):
        pid = p.get("id")
        if not pid:
            raise ValueError("Place missing ID")
        net.add_place(pid)

    for t in net_elem.findall(".//transition"):
        tid = t.get("id")
        if not tid:
            raise ValueError("Transition missing ID")
        net.add_transition(tid)

    for arc in net_elem.findall(".//arc"):
        src = arc.get("source")
        tgt = arc.get("target")
        if not src or not tgt:
            raise ValueError("Arc missing source/target")
        net.add_arc(src, tgt)

    # ---------- PASS 4: INITIAL MARKINGS ----------
    for p in net_elem.findall(".//place"):
        pid = p.get("id")
        mk = p.find(".//initialMarking")
        tokens = 0

        if mk is not None:
            # Form 1: <value>1</value>
            val = mk.find("value")
            # Form 2: <token><value>1</value></token>
            if val is None:
                val = mk.find(".//token/value")
            # Form 3: <text>1</text>  ← ADD THIS
            if val is None:
                val = mk.find("text")

            if val is not None and val.text:
                try:
                    tokens = int(val.text.strip())
                except:
                    raise ValueError(f"Invalid marking at place {pid}")

        net.set_initial_marking(pid, tokens)

    for t in net.transitions:
        if len(net.preset[t]) == 0:
            print(f"Warning: Transition {t} has no input places.")
        if len(net.postset[t]) == 0:
            print(f"Warning: Transition {t} has no output places.")

    return net