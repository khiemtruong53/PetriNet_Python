# main.py - Updated with Task 4 & 5 Integration

import sys
import time
from pnml_parser import parse_pnml
from bdd import symbolic_reachability_bdd
from deadlock_detection import detect_deadlock, format_marking, is_deadlock_explicit
from optimization import optimize_reachable_markings_bruteforce, optimize_reachable_markings_ilp
import matplotlib.pyplot as plt
import networkx as nx


def draw_petri_net(petri_net, output_file="petri_net.png"):
    G = nx.DiGraph()
    for p in petri_net.places:
        G.add_node(p, type="place")
    for t in petri_net.transitions:
        G.add_node(t, type="transition")
    for s, tgt in petri_net.arcs:
        G.add_edge(s, tgt)

    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except:
        pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(10, 8))
    place_nodes = [n for n in G.nodes if G.nodes[n]["type"] == "place"]
    nx.draw_networkx_nodes(G, pos, nodelist=place_nodes, node_shape='o', node_color='lightblue', node_size=400)
    transition_nodes = [n for n in G.nodes if G.nodes[n]["type"] == "transition"]
    nx.draw_networkx_nodes(G, pos, nodelist=transition_nodes, node_shape='s', node_color='lightgreen', node_size=400)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=20)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")
    plt.axis("off")
    plt.title(f"Petri Net: {petri_net.name}")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def draw_reachability_graph(petri_net, deadlock_marking=None, output_file="reachability_graph.png"):
    reachable = petri_net.get_reachable_markings()
    G = nx.DiGraph()
    state_id = {m: f"S{i}" for i, m in enumerate(reachable)}
    
    # Color nodes: deadlock = red, initial = green, others = yellow
    node_colors = {}
    for m in reachable:
        label = "{" + ", ".join(sorted(m)) + "}" if m else "∅"
        sid = state_id[m]
        G.add_node(sid, label=label)
        
        if deadlock_marking and m == deadlock_marking:
            node_colors[sid] = 'red'
        elif m == frozenset(petri_net.initial_marking):
            node_colors[sid] = 'lightgreen'
        else:
            node_colors[sid] = 'lightyellow'
    
    for m in reachable:
        for t in petri_net.transitions:
            if petri_net.is_enabled(t, m):
                next_m = petri_net.fire(t, m)
                G.add_edge(state_id[m], state_id[next_m], transition=t)

    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except:
        pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(12, 10))
    
    # Draw nodes with colors
    for sid in G.nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=[sid], 
                              node_color=node_colors.get(sid, 'lightyellow'), 
                              node_size=400)
    
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=20)
    labels = {n: G.nodes[n]["label"] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=9)
    edge_labels = {(u, v): G.edges[(u, v)]["transition"] for u, v in G.edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color="red")
    
    plt.axis("off")
    title = "Reachability Graph"
    if deadlock_marking:
        title += " (Red = Deadlock)"
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <input.pnml>")
        sys.exit(1)

    try:
        net = parse_pnml(sys.argv[1])
        print("="*70)
        print("PNML PARSING SUCCESSFUL")
        print("="*70)
        print(net)

        # ====================================
        # TASK 2: Explicit Reachability (BFS)
        # ====================================
        print("\n" + "="*70)
        print("TASK 2: EXPLICIT REACHABILITY (BFS)")
        print("="*70)
        
        t0 = time.perf_counter()
        reachable_explicit = net.get_reachable_markings()
        t1 = time.perf_counter()
        count_explicit = len(reachable_explicit)
        time_explicit_ms = (t1 - t0) * 1000

        print(f"Found: {count_explicit} reachable markings")
        print(f"Time: {time_explicit_ms:.3f} ms")
        
        print("\nReachable markings (in firing order):")
        for i, m in enumerate(reachable_explicit, 1):
            print(f"  {i:2d}: {format_marking(m)}")

        # Draw Petri net
        draw_petri_net(net, "petri_net.png")
        print("\nSaved: petri_net.png")

        # ====================================
        # TASK 3: Symbolic Reachability (BDD)
        # ====================================
        print("\n" + "="*70)
        print("TASK 3: SYMBOLIC REACHABILITY (BDD)")
        print("="*70)
        
        t2 = time.perf_counter()
        Reach_bdd, count_bdd, time_bdd_sec, bdd_manager = symbolic_reachability_bdd(net)
        t3 = time.perf_counter()
        time_bdd_ms = (t3 - t2) * 1000

        print(f"Found: {count_bdd} reachable markings")
        print(f"Time: {time_bdd_ms:.3f} ms")

        # Comparison
        print("\n" + "="*70)
        print("PERFORMANCE COMPARISON (Tasks 2 vs 3)")
        print("="*70)
        print(f"{'Method':<15} {'States':>8} {'Time (ms)':>12} {'Speedup':>10}")
        print("-"*70)
        print(f"{'Explicit BFS':<15} {count_explicit:>8} {time_explicit_ms:>12.3f} {'1.00x':>10}")
        print(f"{'Symbolic BDD':<15} {count_bdd:>8} {time_bdd_ms:>12.3f} {time_explicit_ms/time_bdd_ms if time_bdd_ms > 0 else float('inf'):>10.2f}")
        print("-"*70)
        
        if count_explicit == count_bdd:
            print("Verification: Counts match!")
        else:
            print("WARNING: Count mismatch!")

        # ====================================
        # TASK 4: Deadlock Detection
        # ====================================
        print("\n" + "="*70)
        print("TASK 4: DEADLOCK DETECTION (ILP + BDD)")
        print("="*70)
        
        # Try both methods
        methods = ["explicit", "bdd_compact"]
        results = {}
        
        for method in methods:
            deadlock, elapsed = detect_deadlock(net, method=method)
            results[method] = (deadlock, elapsed)
            
            method_name = method.upper().replace("_", " ")
            print(f"\nMethod: {method_name}")
            print(f"   Result: {format_marking(deadlock)}")
            print(f"   Time: {elapsed*1000:.3f} ms")
        
        # Final verdict
        deadlock_marking = results["bdd_compact"][0]  # Use BDD result as authoritative
        
        print("\n" + "="*70)
        if deadlock_marking:
            print("DEADLOCK DETECTED!")
            print("="*70)
            print(f"Deadlock marking: {format_marking(deadlock_marking)}")
            
            # Verify it's reachable
            if deadlock_marking in set(reachable_explicit):
                print("Verified: Marking is reachable from initial state")
            else:
                print("WARNING: Marking not found in explicit reachable set!")
            
            # Verify no transitions enabled
            enabled = [t for t in net.transitions if net.is_enabled(t, deadlock_marking)]
            if not enabled:
                print("Verified: No transitions enabled (true deadlock)")
            else:
                print(f"WARNING: Transitions enabled: {enabled}")
            
            # Draw reachability graph with deadlock highlighted
            draw_reachability_graph(net, deadlock_marking, "reachability_graph.png")
            print("\nSaved: reachability_graph.png (deadlock in RED)")
            
        else:
            print("NO DEADLOCK FOUND")
            print("="*70)
            print("System is deadlock-free (all reachable markings enable at least one transition)")
            
            # Draw reachability graph
            draw_reachability_graph(net, None, "reachability_graph.png")
            print("\nSaved: reachability_graph.png")

        # ====================================
        # TASK 5: Optimization over Reachable Markings
        # ====================================
        print("\n" + "="*70)
        print("TASK 5: OPTIMIZATION OVER REACHABLE MARKINGS")
        print("="*70)
        
        places_list = sorted(net.places)
        print(f"\nPlaces: {places_list}")
        
        # Define weights (can be customized)
        # Option 1: Sequential weights (1, 2, 3, ...)
        weights = {p: i for i, p in enumerate(places_list, 1)}
        
        # Option 2: Custom weights (uncomment to use)
        # weights = {'P1': 10, 'P2': 5, 'P3': 3, 'P4': 2, 'P5': 1, 'P6': 1}
        
        print(f"Weights: {weights}")
        
        # Method 1: Brute Force
        print(f"\n{'='*70}")
        print("Method 1: BRUTE FORCE")
        print(f"{'='*70}")
        
        t4 = time.perf_counter()
        optimal_marking_bf, optimal_value_bf, time_bf = optimize_reachable_markings_bruteforce(net, weights)
        t5 = time.perf_counter()
        time_bf_ms = (t5 - t4) * 1000
        
        if optimal_marking_bf:
            print(f"Optimal marking: {format_marking(optimal_marking_bf)}")
            print(f"Optimal value: {optimal_value_bf}")
            print(f"Computation time: {time_bf_ms:.3f} ms")
        else:
            print("No reachable marking found")
        
        # Method 2: ILP
        print(f"\n{'='*70}")
        print("Method 2: INTEGER LINEAR PROGRAMMING (ILP)")
        print(f"{'='*70}")
        
        t6 = time.perf_counter()
        optimal_marking_ilp, optimal_value_ilp, time_ilp = optimize_reachable_markings_ilp(net, weights)
        t7 = time.perf_counter()
        time_ilp_ms = (t7 - t6) * 1000
        
        if optimal_marking_ilp:
            print(f"Optimal marking: {format_marking(optimal_marking_ilp)}")
            print(f"Optimal value: {optimal_value_ilp}")
            print(f"Computation time: {time_ilp_ms:.3f} ms")
        else:
            print("No reachable marking found")
        
        # Comparison
        print(f"\n{'='*70}")
        print("PERFORMANCE COMPARISON (Task 5 Methods)")
        print(f"{'='*70}")
        print(f"{'Method':<20} {'Value':>10} {'Time (ms)':>12} {'Speedup':>10}")
        print("-"*70)
        print(f"{'Brute Force':<20} {optimal_value_bf:>10} {time_bf_ms:>12.3f} {'1.00x':>10}")
        print(f"{'ILP':<20} {optimal_value_ilp:>10} {time_ilp_ms:>12.3f} {time_bf_ms/time_ilp_ms if time_ilp_ms > 0 else float('inf'):>10.2f}")
        print("-"*70)
        
        if optimal_value_bf == optimal_value_ilp:
            print("Verification: Both methods found the same optimal value!")
        else:
            print("WARNING: Different results!")

        # ====================================
        # SUMMARY
        # ====================================
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Petri Net: {net.name}")
        print(f"  Places: {len(net.places)}")
        print(f"  Transitions: {len(net.transitions)}")
        print(f"  Initial marking: {format_marking(frozenset(net.initial_marking))}")
        print(f"\nReachability:")
        print(f"  Total states: {count_explicit}")
        print(f"  Explicit time: {time_explicit_ms:.3f} ms")
        print(f"  BDD time: {time_bdd_ms:.3f} ms")
        print(f"\nDeadlock:")
        if deadlock_marking:
            print(f"  Status: FOUND")
            print(f"  Marking: {format_marking(deadlock_marking)}")
        else:
            print(f"  Status: NONE (deadlock-free)")
        print(f"\nOptimization:")
        print(f"  Optimal marking: {format_marking(optimal_marking_bf)}")
        print(f"  Optimal value: {optimal_value_bf}")
        print(f"  Best method: {'Brute Force' if time_bf_ms < time_ilp_ms else 'ILP'} ({min(time_bf_ms, time_ilp_ms):.3f} ms)")
        
        print("\n" + "="*70)
        print("ALL TASKS COMPLETED SUCCESSFULLY")
        print("="*70)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()