from pyeda.inter import exprvars, expr2bdd

def bdd_reachability(net):
    places = sorted(net.places.keys())
    n = len(places)

    # boolean variables for each place
    x = exprvars("p", n)

    # encode initial marking
    init_m = net.places
    init_expr = None

    for i, p in enumerate(places):
        bit = x[i] if init_m[p] == 1 else ~x[i]
        init_expr = bit if init_expr is None else init_expr & bit

    bdd = expr2bdd(init_expr)

    # relation building (same from explicit BFS)
    pre, post = build_relations(net)

    changed = True
    while changed:
        changed = False

        for t in net.transitions:
            # build transition relation T(x, x')
            guard = None 

            for i, p in enumerate(places):
                if p in pre[t]:
                    bit = x[i]
                elif p in post[t]:
                    bit = ~x[i] # token must be 0 before produce
                else: 
                    bit = (x[i] | ~x[i]) # unconstrained
                
                guard = bit if guard is None else guard & bit

            next_bdd = bdd | expr2bdd(guard)
            if next_bdd != bdd: 
                bdd = next_bdd
                changed = True
            
    return bdd
