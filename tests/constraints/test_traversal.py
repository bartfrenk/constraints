import constraints.traversal as sut

def _adj_fn(graph):
    def fn(i):
        return graph[i]
    return fn


class TestMultipaths(object):

    def test_correct_result_on_dag(self):
        gamma = {0: [1, 2, 6],
                 1: [],
                 2: [1, 4],
                 3: [],
                 4: [3],
                 5: [1, 3],
                 6: [2]}
        actual = sut.multipaths(_adj_fn(gamma), 0)
        assert actual == {1: [[0, 1], [0, 2, 1]],
                          2: [[0, 2], [0, 6, 2]]}

