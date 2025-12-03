# deadlock_detection.py
"""
Task 4: Deadlock Detection using ILP + BDD
==========================================
A deadlock is a reachable marking where NO transition is enabled.
Strategy:
1. Use BDD to get reachable markings symbolically
2. Use ILP to find a marking M ∈ Reach(M0) where ∀t: ∃p ∈ •t: M(p) = 0
"""

import time
from typing import Optional, FrozenSet, Any
from pnml_parser import PetriNet
from bdd import symbolic_reachability_bdd

try:
    from pulp import LpProblem, LpVariable, LpMinimize, LpBinary, lpSum, value, PULP_CBC_CMD
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    print("  Warning: PuLP not installed. Install with: pip install pulp")


def is_deadlock_explicit(pn: PetriNet, marking: FrozenSet[str]) -> bool:
    """
    Check if a marking is a deadlock (no enabled transitions).
    """
    for t in pn.transitions:
        if pn.is_enabled(t, marking):
            return False
    return True


def find_deadlock_explicit(pn: PetriNet) -> Optional[FrozenSet[str]]:
    """
    Brute-force search for deadlock using explicit BFS.
    Returns the first deadlock found, or None.
    """
    reachable = pn.get_reachable_markings()
    for m in reachable:
        if is_deadlock_explicit(pn, m):
            return m
    return None


def find_deadlock_ilp_bdd(
    pn: PetriNet,
    reachable_bdd: Any,
    bdd_manager: Any
) -> Optional[FrozenSet[str]]:
    """
    Use ILP to find a deadlock marking within the BDD-represented reachable set.
    
    Strategy:
    ---------
    1. Create binary variables M[p] for each place p
    2. Add constraint: M must satisfy reachable_bdd
    3. Add constraint: for all transitions t, at least one input place is empty
       ∀t: ∃p ∈ •t: M(p) = 0  ⟺  ∑(p ∈ •t) M(p) < |•t|
    4. Solve feasibility problem
    
    Returns:
    --------
    FrozenSet[str]: deadlock marking if found, else None
    """
    if not HAS_PULP:
        raise RuntimeError("PuLP is required for ILP-based deadlock detection")
    
    if not pn.places:
        return None
    
    places = sorted(pn.places)
    n = len(places)
    place_to_idx = {p: i for i, p in enumerate(places)}
    
    # Variable names in BDD
    x_vars = [f"x_{i}" for i in range(n)]
    
    # ====================================
    # Step 1: Create ILP problem
    # ====================================
    prob = LpProblem("Deadlock_Detection", LpMinimize)
    
    # Binary variables M[p] ∈ {0, 1}
    M = {p: LpVariable(f"M_{p}", cat=LpBinary) for p in places}
    
    # Dummy objective (we only care about feasibility)
    prob += 0, "Dummy_Objective"
    
    # ====================================
    # Step 2: Extract BDD constraints
    # ====================================
    # We need to ensure that M satisfies the BDD
    # This is HARD in general, but for small nets we can enumerate BDD satisfying assignments
    
    # Get all satisfying assignments from BDD
    satisfying_assignments = list(bdd_manager.pick_iter(reachable_bdd, care_vars=x_vars))
    
    if not satisfying_assignments:
        return None  # No reachable states
    
    # Create "big-M" OR constraint: M must match at least one BDD solution
    # This is exponential, but works for small nets
    # For each satisfying assignment, create indicator variable
    indicators = []
    for idx, assignment in enumerate(satisfying_assignments):
        indicator = LpVariable(f"indicator_{idx}", cat=LpBinary)
        indicators.append(indicator)
        
        # If indicator = 1, then M must equal this assignment
        for p in places:
            i = place_to_idx[p]
            var_name = x_vars[i]
            bit_value = assignment.get(var_name, 0)
            
            if bit_value == 1:
                # M[p] ≥ indicator (if indicator=1, M[p] must be 1)
                prob += M[p] >= indicator, f"Match_{idx}_place_{p}_high"
            else:
                # M[p] ≤ 1 - indicator (if indicator=1, M[p] must be 0)
                prob += M[p] <= 1 - indicator, f"Match_{idx}_place_{p}_low"
    
    # Exactly one indicator must be true
    prob += lpSum(indicators) == 1, "Select_One_Assignment"
    
    # ====================================
    # Step 3: Deadlock constraints
    # ====================================
    # For each transition t, at least one input place must be empty
    for t in pn.transitions:
        preset_t = pn.preset[t]
        if not preset_t:
            # Transition with no input → always enabled → cannot be deadlock
            continue
        
        # ∑(p ∈ •t) M[p] ≤ |•t| - 1
        # (At least one input place must have M[p] = 0)
        prob += lpSum(M[p] for p in preset_t) <= len(preset_t) - 1, f"Deadlock_{t}"
    
    # ====================================
    # Step 4: Solve
    # ====================================
    solver = PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    
    # Check if solution found
    if prob.status != 1:  # 1 = Optimal
        return None
    
    # Extract deadlock marking
    deadlock_marking = frozenset(p for p in places if value(M[p]) > 0.5)
    return deadlock_marking


def find_deadlock_ilp_bdd_compact(
    pn: PetriNet,
    reachable_bdd: Any,
    bdd_manager: Any,
    debug: bool = False
) -> Optional[FrozenSet[str]]:
    """
    Optimized version: checks each BDD-reachable marking for deadlock.
    Returns the first deadlock found, or None if no deadlock exists.
    
    IMPORTANT: We cross-check with explicit reachability to ensure
    the BDD is correct (in case of bugs in BDD transition relation).
    """
    if not HAS_PULP:
        raise RuntimeError("PuLP required")
    
    # Get explicit reachable markings for verification
    explicit_reachable = set(pn.get_reachable_markings())
    
    # Get BDD reachable markings
    places = sorted(pn.places)
    x_vars = [f"x_{i}" for i in range(len(places))]
    
    satisfying = list(bdd_manager.pick_iter(reachable_bdd, care_vars=x_vars))
    
    if debug:
        print(f"\n[DEBUG] BDD returned {len(satisfying)} satisfying assignments")
        print(f"[DEBUG] Explicit reachability found {len(explicit_reachable)} states")
    
    if not satisfying:
        return None  # No reachable states at all
    
    for idx, assignment in enumerate(satisfying):
        # Convert BDD assignment to marking
        marked_places = [
            places[i] for i in range(len(places))
            if assignment.get(x_vars[i], 0) == 1
        ]
        marking = frozenset(marked_places)
        
        if debug:
            m_str = "{" + ", ".join(sorted(marking)) + "}" if marking else "∅"
            in_explicit = marking in explicit_reachable
            print(f"[DEBUG]   Assignment {idx}: {m_str} | In explicit: {in_explicit}")
        
        # CRITICAL: Only consider markings that are actually reachable
        # This protects against bugs in BDD transition relation
        if marking not in explicit_reachable:
            if debug:
                print(f"[DEBUG]     Skipping (not in explicit reachable set)")
            continue
        
        # Check if deadlock (no transitions enabled)
        is_deadlock = not any(pn.is_enabled(t, marking) for t in pn.transitions)
        
        if debug:
            print(f"[DEBUG]     Is deadlock: {is_deadlock}")
        
        if is_deadlock:
            return marking
    
    return None


def detect_deadlock(pn: PetriNet, method: str = "bdd", debug: bool = False) -> Optional[FrozenSet[str]]:
    """
    Main function for deadlock detection.
    
    Parameters:
    -----------
    pn: PetriNet
        The Petri net to analyze
    method: str
        "explicit" - brute force BFS
        "bdd" - BDD + ILP (full solver)
        "bdd_compact" - BDD enumeration (faster for small nets)
    debug: bool
        Enable debug output
    
    Returns:
    --------
    Optional[FrozenSet[str]]: deadlock marking or None
    """
    start = time.perf_counter()
    
    if method == "explicit":
        result = find_deadlock_explicit(pn)
        elapsed = time.perf_counter() - start
        return result, elapsed
    
    elif method in ["bdd", "bdd_compact"]:
        # First compute reachable states with BDD
        R_bdd, count, time_bdd, manager = symbolic_reachability_bdd(pn)
        
        if debug:
            print(f"[DEBUG] BDD reachability found {count} states")
        
        if method == "bdd":
            result = find_deadlock_ilp_bdd(pn, R_bdd, manager)
        else:
            result = find_deadlock_ilp_bdd_compact(pn, R_bdd, manager, debug=debug)
        
        elapsed = time.perf_counter() - start
        return result, elapsed
    
    else:
        raise ValueError(f"Unknown method: {method}")


def format_marking(m: Optional[FrozenSet[str]]) -> str:
    """Pretty print marking."""
    if m is None:
        return "None"
    if not m:
        return "∅"
    return "{" + ", ".join(sorted(m)) + "}"


# ============================================================
# Command-line interface
# ============================================================

if __name__ == "__main__":
    import sys
    from pnml_parser import parse_pnml
    
    if len(sys.argv) < 2:
        print("Usage: python deadlock_detection.py <file.pnml> [method]")
        print("Methods: explicit, bdd, bdd_compact (default: bdd_compact)")
        sys.exit(1)
    
    pnml_file = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "bdd_compact"
    
    print(f"🔍 Deadlock Detection: {pnml_file}")
    print(f"📊 Method: {method}\n")
    
    try:
        pn = parse_pnml(pnml_file)
        print(f"✅ Petri net loaded: {len(pn.places)} places, {len(pn.transitions)} transitions")
        
        deadlock, elapsed = detect_deadlock(pn, method)
        
        print(f"\n⏱️  Time: {elapsed:.6f} s")
        
        if deadlock is not None:
            print(f"❌ DEADLOCK FOUND: {format_marking(deadlock)}")
            
            # Verify
            print("\n🔬 Verification:")
            print(f"   Reachable: {deadlock in set(pn.get_reachable_markings())}")
            print(f"   Is deadlock: {is_deadlock_explicit(pn, deadlock)}")
        else:
            print("✅ NO DEADLOCK (system is deadlock-free)")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)