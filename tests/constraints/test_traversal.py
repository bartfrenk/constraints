import constraints.traversal as sut


def _adj_fn(graph):
    def fn(i):
        return graph[i]
    return fn


gamma = {0: [1, 2, 6],
         1: [],
         2: [1, 4],
         3: [],
         4: [3],
         5: [1, 3],
         6: [2]}


cycle = {0: [1], 1: [2], 2: [3], 3: [0]}


class TestMultipaths(object):
    # pylint: disable=no-self-use

    def test_correct_result_on_dag(self):
        actual = sut.multipaths(_adj_fn(gamma), 0)
        assert actual == {1: [[0, 1], [0, 2, 1]],
                          2: [[0, 2], [0, 6, 2]]}

    def test_correct_result_on_cycle(self):
        actual = sut.multipaths(_adj_fn(cycle), 0)
        assert actual == {}


class TestBFS(object):
    # pylint: disable=no-self-use

    def test_correct_result_on_dag(self):
        actual = sut.bfs(_adj_fn(gamma), 0)
        assert actual == {1: [0, 2],
                          2: [0, 6],
                          3: [4],
                          4: [2],
                          6: [0]}

    def test_correct_result_on_cycle(self):
        actual = sut.bfs(_adj_fn(cycle), 0)
        assert actual == {0: [3],
                          1: [0],
                          2: [1],
                          3: [2]}
