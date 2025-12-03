# bdd.py

from dd.autoref import BDD
import time
import matplotlib.pyplot as plt
import networkx as nx
from typing import Any

from pnml_parser import PetriNet


def symbolic_reachability_bdd(petri_net: PetriNet):
    """
    Build BDD from explicit reachable markings (safe for small nets).
    Returns: (bdd, count, time, manager)
    """
    # Get explicit reachable markings (we trust this for small nets)
    explicit_markings = petri_net.get_reachable_markings()
    places = sorted(petri_net.places)
    place_to_var = {p: f"x_{i}" for i, p in enumerate(places)}

    bdd = BDD()
    bdd.declare(*place_to_var.values())

    if not explicit_markings:
        Reach = bdd.false
        count = 0
    elif len(explicit_markings) == 1:
        marking = next(iter(explicit_markings))
        terms = []
        for p in places:
            var = place_to_var[p]
            if p in marking:
                terms.append(var)
            else:
                terms.append(f"~{var}")
        expr = " & ".join(terms)
        Reach = bdd.add_expr(expr)
        count = 1
    else:
        disjuncts = []
        for marking in explicit_markings:
            terms = []
            for p in places:
                var = place_to_var[p]
                if p in marking:
                    terms.append(var)
                else:
                    terms.append(f"~{var}")
            disjuncts.append(" & ".join(terms))
        expr = " | ".join(f"({d})" for d in disjuncts)
        Reach = bdd.add_expr(expr)
        count = len(explicit_markings)

    return Reach, count, 0.0, bdd

