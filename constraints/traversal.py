from collections import deque, defaultdict


def multi_paths(adj_fn, start, singles=False):
    """List disjoint paths from start to all reachable vertices.

    :param adj_fn: The adjacency function of the graph, see `bfs`.
    :param start: The starting node, see `bfs`.
    :param singles: Also return nodes that are reachable by a single path.

    :returns: A dict with keys the nodes reachable from `start` by multiple
              paths, and values a list of disjoint paths from `start` to that
              node.
    """
    edges_to = bfs(adj_fn, start)
    paths = {}
    for (key, ws) in edges_to.items():
        if len(ws) > 1 or singles:
            paths[key] = [_backtrack(edges_to, w) + [key] for w in ws]
    return paths


def bfs(adj_fn, start):
    """Traverse a digraph in breadth-first order.

    :param adj_fn: The adjacency function of the graph, i.e., it maps a vertex v
        to a the list of w such that (v, w) is an arc in the digraph.
    :param start: The node at which to start the traversal.

    :returns: A dict with keys the nodes reachable from start and values a list
              of penultimate nodes of path that connect them to start.
    """
    todo = deque()
    visited = set([])
    edges_to = defaultdict(list)

    visited.add(start)
    todo.appendleft(start)
    while todo:
        v = todo.pop()
        for w in adj_fn(v):
            if w not in visited:
                edges_to[w].append(v)
                visited.add(w)
                todo.appendleft(w)
            else:
                edges_to[w].append(v)
    return edges_to


def _backtrack(edges_to, w):
    path = [w]
    current = w
    if current in edges_to:
        # take the shortest path
        current = edges_to[current][0]
        path.append(current)
    path.reverse()
    return path
