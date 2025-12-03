# main.py

import sys
import time
from pnml_parser import parse_pnml
from bdd import symbolic_reachability_bdd
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


def draw_reachability_graph(petri_net, output_file="reachability_graph.png"):
    reachable = petri_net.get_reachable_markings()
    G = nx.DiGraph()
    state_id = {m: f"S{i}" for i, m in enumerate(reachable)}
    for m in reachable:
        label = "{" + ", ".join(sorted(m)) + "}" if m else "∅"
        G.add_node(state_id[m], label=label)
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
    nx.draw_networkx_nodes(G, pos, node_color='lightyellow', node_size=400)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='-|>', arrowsize=20)
    labels = {n: G.nodes[n]["label"] for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=9)
    edge_labels = {(u, v): G.edges[(u, v)]["transition"] for u, v in G.edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color="red")
    plt.axis("off")
    plt.title("Reachability Graph")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def format_marking(m):
    """Format a marking (frozenset) for display."""
    if not m:
        return "∅"
    return "{" + ", ".join(sorted(m)) + "}"


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <input.pnml>")
        sys.exit(1)

    try:
        net = parse_pnml(sys.argv[1])
        print("✅ PNML parsing successful!")
        print(net)

        draw_petri_net(net, "petri_net.png")

        # Explicit BFS
        print("\n🔍 Explicit BFS: Computing reachable markings...")
        start_explicit = time.time()
        reachable_explicit = net.get_reachable_markings()
        time_explicit = time.time() - start_explicit
        count_explicit = len(reachable_explicit)
        print(f"✅ Explicit: {count_explicit} markings in {time_explicit*1e6:.0f} µs")

        # In ra toàn bộ marking
        print("\n📋 Reachable markings in firing order (BFS):")
        for i, m in enumerate(reachable_explicit, 1):
            print(f"  {i:2d}: {format_marking(m)}")

        # Vẽ đồ thị reachability (sau khi có marking)
        draw_reachability_graph(net, "reachability_graph.png")

        # Symbolic BDD
        print("\n🧠 Symbolic BDD: Computing reachable markings...")
        Reach_bdd, count_bdd, time_bdd, bdd_manager = symbolic_reachability_bdd(net)
        print(f"✅ BDD: {count_bdd} markings in {time_bdd*1e6:.0f} µs")

        # So sánh
        print(f"\n📊 Performance Comparison:")
        print(f"  Explicit: {count_explicit} states, {time_explicit*1e6:.0f} µs")
        print(f"  BDD:      {count_bdd} states, {time_bdd*1e6:.0f} µs")
        if count_explicit == count_bdd:
            print("  ✅ Counts match!")
        else:
            print("  ❌ MISMATCH in counts!")

        # Task 5: Optimization over reachable markings
        print("\n🎯 Task 5: Optimization over Reachable Markings")
        
        # Định nghĩa trọng số cho các place
        # Có thể tùy chỉnh theo yêu cầu của bài toán
        weights = {}
        places_list = sorted(net.places)
        print(f"  Places: {places_list}")
        
        # Phương án 1: Gán trọng số đều cho tất cả places
        for i, p in enumerate(places_list, 1):
            weights[p] = i
        
        # Hoặc phương án 2: Gán trọng số tùy ý
        # weights = {'P1': 10, 'P2': 5, 'P3': 3, 'P4': 2, 'P5': 1, 'P6': 1}
        
        print(f"  Weights (c): {weights}")
        
        # Sử dụng brute force (đơn giản, phù hợp với small nets)
        print("\n  Method 1: Brute Force")
        optimal_marking_bf, optimal_value_bf, time_bf = optimize_reachable_markings_bruteforce(net, weights)
        
        if optimal_marking_bf:
            print(f"    Optimal marking: {format_marking(optimal_marking_bf)}")
            print(f"    Optimal value: {optimal_value_bf}")
            print(f"    Computation time: {time_bf*1e6:.0f} µs")
        else:
            print("    No reachable marking found")
        
        # Sử dụng ILP (formal approach)
        print("\n  Method 2: Integer Linear Programming")
        optimal_marking_ilp, optimal_value_ilp, time_ilp = optimize_reachable_markings_ilp(net, weights)
        
        if optimal_marking_ilp:
            print(f"    Optimal marking: {format_marking(optimal_marking_ilp)}")
            print(f"    Optimal value: {optimal_value_ilp}")
            print(f"    Computation time: {time_ilp*1e6:.0f} µs")
        else:
            print("    No reachable marking found")
        
        # So sánh 2 phương pháp
        print("\n  Comparison:")
        print(f"    Brute Force: value={optimal_value_bf}, time={time_bf*1e6:.0f} µs")
        print(f"    ILP Method:  value={optimal_value_ilp}, time={time_ilp*1e6:.0f} µs")
        if optimal_value_bf == optimal_value_ilp:
            print("    ✅ Both methods found the same optimal value!")
        else:
            print("    ⚠️  Different results!")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()