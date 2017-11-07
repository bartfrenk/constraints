import json


class Error(object):
    """Output of a constraint check."""

    def __init__(self, *contents):

        self._top = []
        self._nested = {}
        for err in contents:
            if isinstance(err, str):
                self._top.append(err)
            if isinstance(err, dict):
                self._nested.update(err)
            if isinstance(err, list):
                raise ValueError('content cannot be a list')

    def merge(self, err):
        """Merge the argument into this Error object.

        :param err: The Error object to merge.
        :rtype: An Error object
        """
        # pylint: disable=protected-access
        self._top.extend(err._top)
        for (key, child) in err._nested.items():
            if key in self._nested:
                self._nested[key].merge(child)
            else:
                self._nested[key] = child

    def unwrap(self):
        """
        Convert the error object to a tree-like structure consisting of lists
        and dicts. The leaves of the tree are strings.
        """

        result = self._top
        if self._nested:
            d = {key: err.unwrap() for (key, err) in self._nested.items()}
            result.append(d)
        return result

    def to_json(self):
        return json.dumps(self.unwrap())

    def __eq__(self, err):
        # pylint: disable=protected-access
        return self._top == err._top and self._nested == err._nested

    def __nonzero__(self):
        return bool(self._top) or bool(self._nested)

    def __repr__(self):
        return repr((self._top, self._nested))
