# bdd.py
from dd.autoref import BDD
import time
from typing import Tuple, Any
from pnml_parser import PetriNet


def symbolic_reachability_bdd(petri_net: PetriNet) -> Tuple[Any, int, float, BDD]:
    """
    Symbolic reachability via fixpoint iteration using BDDs.
    Returns: (reachable_bdd, count, time_seconds, bdd_manager)
    """
    if not petri_net.places:
        bdd = BDD()
        return bdd.false, 0, 0.0, bdd

    start_time = time.perf_counter()
    places = sorted(petri_net.places)
    n = len(places)

    # Initialize BDD manager
    bdd = BDD()
    
    # Declare current (x_i) and next (y_i) variables
    x_vars = [f"x_{i}" for i in range(n)]
    y_vars = [f"y_{i}" for i in range(n)]
    bdd.declare(*x_vars, *y_vars)

    # Map place name to variable index
    place_to_idx = {p: i for i, p in enumerate(places)}
    
    # Encode initial marking: R0 = ∧ (x_i = 1 if marked else 0)
    init_terms = []
    for p in places:
        i = place_to_idx[p]
        if p in petri_net.initial_marking:
            init_terms.append(x_vars[i])
        else:
            init_terms.append(f"~{x_vars[i]}")
    R = bdd.add_expr(" & ".join(init_terms)) if init_terms else bdd.true

    # Build global transition relation T(X, Y) = ∨_t T_t(X, Y)
    T_global = bdd.false

    for t in petri_net.transitions:
        pre = petri_net.preset[t]
        post = petri_net.postset[t]

        # Guard: all pre-places must be marked
        if pre:
            guard = " & ".join(x_vars[place_to_idx[p]] for p in pre)
        else:
            guard = "True"

        # Next-state constraints — FIXED LOGIC
        next_constraints = []
        for p in places:
            i = place_to_idx[p]
            x = x_vars[i]
            y = y_vars[i]
            in_pre = p in pre
            in_post = p in post

            if in_pre and in_post:
                # Net effect: token consumed and produced → unchanged
                next_constraints.append(f"({x} <-> {y})")
            elif in_pre:
                # Only consumed → must be 0 in next state
                next_constraints.append(f"~{y}")
            elif in_post:
                # Only produced → must be 1 in next state
                next_constraints.append(y)
            else:
                # Unchanged
                next_constraints.append(f"({x} <-> {y})")

        body = " & ".join(next_constraints)
        T_t_expr = f"({guard}) & ({body})" if guard != "True" else body
        T_t = bdd.add_expr(T_t_expr)
        
        # Accumulate: T_global = T_global OR T_t
        T_global = bdd.apply("or", T_global, T_t)

    # Fixpoint iteration: R = R ∪ Image(R)
    rename_map = {y_vars[i]: x_vars[i] for i in range(n)}
    current_var_names = x_vars  # for existential quantification

    while True:
        # Image = ∃X. (R ∧ T)
        image = bdd.apply("and", R, T_global)
        image = bdd.exist(current_var_names, image)
        image = bdd.let(rename_map, image)

        # New = image \ R
        not_R = bdd.apply("not", R)
        new_states = bdd.apply("and", image, not_R)
        if new_states == bdd.false:
            break

        R = bdd.apply("or", R, new_states)

    elapsed = time.perf_counter() - start_time
    count = bdd.count(R)
    return R, count, elapsed, bdd