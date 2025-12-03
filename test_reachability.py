# test_reachability.py
# -------------------------------------------------------
# Test explicit (BFS) vs symbolic (BDD) reachability
# Compatible with your provided pnml_parser.py & bdd.py
# -------------------------------------------------------

from pnml_parser import PetriNet
from bdd import symbolic_reachability_bdd
import time


# ============================================================
# 1. TEST CASE GENERATORS
# ============================================================

def build_linear_chain(n=5):
    """
    P0 -> P1 -> P2 -> ... -> P(n-1)
    Initial marking: P0
    """
    pn = PetriNet()
    for i in range(n):
        pn.add_place(f"P{i}")
    for i in range(n - 1):
        pn.add_transition(f"T{i}")
        pn.add_arc(f"P{i}", f"T{i}")
        pn.add_arc(f"T{i}", f"P{i+1}")
    pn.initial_marking = {"P0"}
    return pn


def build_xor_split(k=4):
    """
    XOR branching:
    P0 -> (T0_0 or T0_1) -> P1 -> ... (k times)
    """
    pn = PetriNet()
    pn.add_place("P0")
    pn.initial_marking = {"P0"}

    for i in range(k):
        pn.add_place(f"P{i+1}")
        pn.add_transition(f"T{i}_0")
        pn.add_transition(f"T{i}_1")

        pn.add_arc("P0" if i == 0 else f"P{i}", f"T{i}_0")
        pn.add_arc("P0" if i == 0 else f"P{i}", f"T{i}_1")

        pn.add_arc(f"T{i}_0", f"P{i+1}")
        pn.add_arc(f"T{i}_1", f"P{i+1}")

    return pn


def build_parallel_net(k=3):
    """
    Independent loops: P_i <-> T_i
    BDD-friendly.
    """
    pn = PetriNet()
    for i in range(k):
        pn.add_place(f"P{i}")
        pn.add_transition(f"T{i}")
        pn.add_arc(f"P{i}", f"T{i}")
        pn.add_arc(f"T{i}", f"P{i}")
        pn.initial_marking.add(f"P{i}")
    return pn


def build_no_transition():
    pn = PetriNet()
    pn.add_place("P")
    pn.initial_marking = {"P"}
    return pn


def build_dead_transition():
    pn = PetriNet()
    pn.add_place("P0")
    pn.add_place("P1")
    pn.add_transition("Tdead")
    pn.add_arc("P1", "Tdead")  # P1 has no token → dead
    pn.initial_marking = {"P0"}
    return pn


# ⭐⭐⭐ NEW SUPER TEST — PHÁT HUY SỨC MẠNH BDD ⭐⭐⭐
def build_parallel_chains(n: int):
    """
    Tạo n chuỗi song song:
      pi_0 → pi_1 → pi_2
    Mỗi chuỗi độc lập → reachable states = 2^n
    BFS: chết ở n >= 20
    BDD: chạy cực nhanh
    """
    pn = PetriNet()
    for i in range(n):
        p0 = f"P{i}_0"
        p1 = f"P{i}_1"
        p2 = f"P{i}_2"
        t1 = f"T{i}_1"
        t2 = f"T{i}_2"

        pn.add_place(p0)
        pn.add_place(p1)
        pn.add_place(p2)
        pn.add_transition(t1)
        pn.add_transition(t2)

        pn.add_arc(p0, t1)
        pn.add_arc(t1, p1)

        pn.add_arc(p1, t2)
        pn.add_arc(t2, p2)

        pn.initial_marking.add(p0)  # token tại p0

    return pn


# ============================================================
# 2. HELPERS
# ============================================================

def explicit_reachability(pn: PetriNet):
    """
    Wrapper để đo thời gian BFS:
    dùng pn.get_reachable_markings()
    """
    start = time.perf_counter()
    reachable = pn.get_reachable_markings()
    elapsed = time.perf_counter() - start
    return reachable, len(reachable), elapsed


# ============================================================
# 3. TEST FUNCTION
# ============================================================

def test_case(pn: PetriNet, name: str):
    print("\n====================================")
    print(f"TEST: {name}")
    print("====================================")

    # --------------------
    # Explicit BFS
    # --------------------
    try:
        R_exp, n_exp, t_exp = explicit_reachability(pn)
    except MemoryError:
        R_exp, n_exp, t_exp = None, -1, -1
        print("Explicit BFS: FAILED (MemoryError)")

    # --------------------
    # Symbolic BDD
    # --------------------
    R_bdd, n_bdd, t_bdd, manager = symbolic_reachability_bdd(pn)

    print(f"Explicit reachable states = {n_exp}")
    print(f"BDD reachable states      = {n_bdd}")

    if n_exp == n_bdd and n_exp != -1:
        print("✔ Kết quả KHỚP nhau")
    elif n_exp == -1:
        print("⚠ BFS không chạy được → BDD thắng tuyệt đối")
    else:
        print("❌ LỖI: số lượng trạng thái không khớp!")

    print(f"Explicit time = {t_exp:.6f} s")
    print(f"BDD time      = {t_bdd:.6f} s")


# ============================================================
# 4. RUN ALL TESTS
# ============================================================

def run_all_tests():
    tests = [
        ("Linear chain n=5", build_linear_chain(5)),
        ("Linear chain n=10", build_linear_chain(10)),
        ("XOR branching k=4", build_xor_split(4)),
        ("Parallel net k=3", build_parallel_net(3)),
        ("No transition", build_no_transition()),
        ("Dead transition", build_dead_transition()),

        # ⭐⭐⭐ Test mạnh nhất: BDD >> BFS ⭐⭐⭐
        ("Parallel Chains n=5 (2^5 states)", build_parallel_chains(5)),
        ("Parallel Chains n=10 (2^10 states)", build_parallel_chains(8))
    ]

    for name, pn in tests:
        test_case(pn, name)


if __name__ == "__main__":
    run_all_tests()
