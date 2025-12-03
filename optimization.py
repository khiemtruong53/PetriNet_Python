# task5_optimization.py

from typing import Dict, FrozenSet, Optional, Tuple
from pnml_parser import PetriNet
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, PULP_CBC_CMD
import time


def optimize_reachable_markings_bruteforce(
    petri_net: PetriNet, 
    weights: Dict[str, int]
) -> Tuple[Optional[FrozenSet[str]], float, float]:
    """
    Task 5: Tim marking M trong tap reachable markings de maximize c^T * M
    Phuong phap: Brute Force - duyet qua tat ca reachable markings
    
    Args:
        petri_net: Petri net da parse
        weights: Dictionary anh xa place -> trong so (c vector)
    
    Returns:
        (optimal_marking, optimal_value, computation_time)
        - optimal_marking: marking toi uu (None neu khong tim thay)
        - optimal_value: gia tri toi uu
        - computation_time: thoi gian tinh toan (seconds)
    """
    start_time = time.time()
    
    # Lay tat ca reachable markings
    reachable_markings = petri_net.get_reachable_markings()
    
    if not reachable_markings:
        return None, 0.0, time.time() - start_time
    
    places = sorted(petri_net.places)
    
    # Khoi tao trong so mac dinh = 0 neu khong co trong weights
    c = {p: weights.get(p, 0) for p in places}
    
    # Duyet qua tat ca reachable markings va tinh gia tri
    best_marking = None
    best_value = float('-inf')
    
    for marking in reachable_markings:
        # Tinh gia tri: tong trong so cua cac place co token
        value = sum(c[p] for p in marking)
        
        if value > best_value:
            best_value = value
            best_marking = marking
    
    computation_time = time.time() - start_time
    
    return best_marking, best_value, computation_time


def optimize_reachable_markings_ilp(
    petri_net: PetriNet,
    weights: Dict[str, int]
) -> Tuple[Optional[FrozenSet[str]], float, float]:
    """
    Task 5: Su dung Integer Linear Programming de optimize
    
    Formulation:
    - Variables: x_i in {0,1} cho moi reachable marking M_i
    - Objective: maximize sum(value(M_i) * x_i)
    - Constraint: sum(x_i) = 1 (chi chon dung 1 marking)
    
    Args:
        petri_net: Petri net da parse
        weights: Dictionary anh xa place -> trong so
    
    Returns:
        (optimal_marking, optimal_value, computation_time)
    """
    start_time = time.time()
    
    reachable_markings = petri_net.get_reachable_markings()
    
    if not reachable_markings:
        return None, 0.0, time.time() - start_time
    
    places = sorted(petri_net.places)
    c = {p: weights.get(p, 0) for p in places}
    
    # Tao ILP problem
    prob = LpProblem("Optimize_Reachable_Markings", LpMaximize)
    
    # Variables: x[i] = 1 neu chon marking thu i
    marking_vars = {}
    marking_values = {}
    
    for i, marking in enumerate(reachable_markings):
        var_name = f"x_{i}"
        marking_vars[i] = LpVariable(var_name, cat='Binary')
        # Tinh gia tri cua marking nay
        marking_values[i] = sum(c[p] for p in marking)
    
    # Objective function: maximize sum(value[i] * x[i])
    prob += lpSum([marking_values[i] * marking_vars[i] for i in range(len(reachable_markings))])
    
    # Constraint: chon dung 1 marking
    prob += lpSum([marking_vars[i] for i in range(len(reachable_markings))]) == 1
    
    # Solve
    prob.solve(PULP_CBC_CMD(msg=0))
    
    # Extract solution
    optimal_marking = None
    optimal_value = 0.0
    
    for i in range(len(reachable_markings)):
        if marking_vars[i].varValue == 1:
            optimal_marking = reachable_markings[i]
            optimal_value = marking_values[i]
            break
    
    computation_time = time.time() - start_time
    
    return optimal_marking, optimal_value, computation_time


def format_marking(m: FrozenSet[str]) -> str:
    """Format marking de hien thi"""
    if not m:
        return "∅"
    return "{" + ", ".join(sorted(m)) + "}"