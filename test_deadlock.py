# test_deadlock.py
"""
Test suite for deadlock detection
"""

from pnml_parser import PetriNet
from deadlock_detection import detect_deadlock, format_marking


def build_simple_deadlock():
    """
    P1 → T1 → P2
    P3 (isolated, no token)
    
    Initial: {P1}
    After T1 fires: {P2} ← DEADLOCK (no enabled transitions)
    """
    pn = PetriNet()
    pn.name = "Simple Deadlock"
    
    pn.add_place("P1")
    pn.add_place("P2")
    pn.add_place("P3")
    
    pn.add_transition("T1")
    
    pn.add_arc("P1", "T1")
    pn.add_arc("T1", "P2")
    
    pn.initial_marking = {"P1"}
    
    return pn


def build_no_deadlock():
    """
    Simple cycle: P1 ⇄ T1
    No deadlock possible.
    """
    pn = PetriNet()
    pn.name = "No Deadlock (cycle)"
    
    pn.add_place("P1")
    pn.add_transition("T1")
    
    pn.add_arc("P1", "T1")
    pn.add_arc("T1", "P1")
    
    pn.initial_marking = {"P1"}
    
    return pn


def build_dining_philosophers_2():
    """
    2 philosophers, 2 forks → potential deadlock
    
    State space:
    - Initial: both thinking
    - Each can pick up left fork
    - DEADLOCK: both hold one fork, waiting for the other
    """
    pn = PetriNet()
    pn.name = "Dining Philosophers (n=2)"
    
    # Philosophers
    pn.add_place("Think1")
    pn.add_place("Think2")
    pn.add_place("Eat1")
    pn.add_place("Eat2")
    
    # Forks
    pn.add_place("Fork1")
    pn.add_place("Fork2")
    
    # Philosopher 1: Think1 → (pickup forks) → Eat1 → (release) → Think1
    pn.add_transition("Pickup1")
    pn.add_transition("Release1")
    
    pn.add_arc("Think1", "Pickup1")
    pn.add_arc("Fork1", "Pickup1")
    pn.add_arc("Fork2", "Pickup1")
    pn.add_arc("Pickup1", "Eat1")
    
    pn.add_arc("Eat1", "Release1")
    pn.add_arc("Release1", "Think1")
    pn.add_arc("Release1", "Fork1")
    pn.add_arc("Release1", "Fork2")
    
    # Philosopher 2: Think2 → (pickup forks) → Eat2 → (release) → Think2
    pn.add_transition("Pickup2")
    pn.add_transition("Release2")
    
    pn.add_arc("Think2", "Pickup2")
    pn.add_arc("Fork2", "Pickup2")
    pn.add_arc("Fork1", "Pickup2")
    pn.add_arc("Pickup2", "Eat2")
    
    pn.add_arc("Eat2", "Release2")
    pn.add_arc("Release2", "Think2")
    pn.add_arc("Release2", "Fork2")
    pn.add_arc("Release2", "Fork1")
    
    # Initial: both thinking, forks available
    pn.initial_marking = {"Think1", "Think2", "Fork1", "Fork2"}
    
    return pn


def build_xor_deadlock():
    """
    XOR choice leading to deadlock:
    
         T1
        /  \\
      P1    P2
        \\  /
         T2 (requires BOTH P1 and P2)
    
    Initial: P0
    After T1: either P1 or P2 (not both) → DEADLOCK at T2
    """
    pn = PetriNet()
    pn.name = "XOR Deadlock"
    
    pn.add_place("P0")
    pn.add_place("P1")
    pn.add_place("P2")
    pn.add_place("P3")
    
    pn.add_transition("T1a")  # P0 → P1
    pn.add_transition("T1b")  # P0 → P2
    pn.add_transition("T2")   # P1 ∧ P2 → P3
    
    pn.add_arc("P0", "T1a")
    pn.add_arc("T1a", "P1")
    
    pn.add_arc("P0", "T1b")
    pn.add_arc("T1b", "P2")
    
    pn.add_arc("P1", "T2")
    pn.add_arc("P2", "T2")
    pn.add_arc("T2", "P3")
    
    pn.initial_marking = {"P0"}
    
    return pn


# ============================================================
# TEST RUNNER
# ============================================================

def run_test(pn: PetriNet, expected_deadlock: bool, debug: bool = False):
    """
    Run deadlock detection test.
    """
    print(f"\n{'='*60}")
    print(f"TEST: {pn.name}")
    print(f"{'='*60}")
    print(f"Places: {len(pn.places)}, Transitions: {len(pn.transitions)}")
    print(f"Initial marking: {format_marking(pn.initial_marking)}")
    print(f"Expected: {'DEADLOCK' if expected_deadlock else 'NO DEADLOCK'}")
    
    # Test all methods
    methods = ["explicit", "bdd_compact"]
    results = {}
    
    for method in methods:
        try:
            deadlock, elapsed = detect_deadlock(pn, method, debug=(debug and method == "bdd_compact"))
            results[method] = (deadlock, elapsed)
            print(f"\n📊 {method.upper()}: {format_marking(deadlock)} ({elapsed:.6f}s)")
        except Exception as e:
            print(f"\n❌ {method.upper()} failed: {e}")
            results[method] = (None, -1)
    
    # Verify consistency - both should find deadlock or both should find none
    deadlocks = [d for d, _ in results.values()]
    found_explicit = deadlocks[0] is not None
    found_bdd = deadlocks[1] is not None
    
    if found_explicit != found_bdd:
        print("\n⚠️  WARNING: Methods disagree on existence of deadlock!")
    
    # Check expectation
    found = any(d is not None for d, _ in results.values())
    if found == expected_deadlock:
        print("\n✅ TEST PASSED")
    else:
        print("\n❌ TEST FAILED")


def main():
    tests = [
        (build_simple_deadlock(), True, False),
        (build_no_deadlock(), False, True),  # Enable debug for this test
        (build_dining_philosophers_2(), False, False),
        (build_xor_deadlock(), True, False),
    ]
    
    for pn, expected, debug in tests:
        run_test(pn, expected, debug)
    
    print(f"\n{'='*60}")
    print("ALL TESTS COMPLETED")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()