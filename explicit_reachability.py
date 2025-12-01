from collections import deque

def build_relations(net):
    pre = {t: [] for t in net.transitions}
    post = {t: [] for t in net.transitions}

    for src, tgt in net.arcs:
        # p => t
        if src in net.places and tgt in net.transitions:
            pre[tgt].append(src)

        # t => p
        if src in net.transitions and tgt in net.places:
            post[src].append(tgt)

    return pre, post

def is_firable(marking, pre, t):
    for p in pre[t]:
        if marking[p] == 0:
            return False
    
    return True

def fire(marking, pre, post, t):
    newMarking = dict(marking)

    # consume tokens
    for p in pre[t]:
        newMarking[p] -= 1

    # produce tokens
    for p in post[t]:
        newMarking[p] += 1

    return newMarking

def bfs_reachability(net):
    pre, post = build_relations(net)

    init = dict(net.places)
    visited = set()
    queue = deque()

    # convert marking dict => tuple for hashing
    def encode(m): return tuple(m[p] for p in sorted(m))

    visited.add(encode(init))
    queue.append(init)

    all_states = [init]

    while queue: 
        marking = queue.popleft()

        for t in net.transitions:
            if is_firable(marking, pre, t):
                newM = fire(marking, pre, post, t)
                code = encode(newM)

                if code not in visited:
                    visited.add(code)
                    queue.append(newM)
                    all_states.append(newM)
    
    return all_states