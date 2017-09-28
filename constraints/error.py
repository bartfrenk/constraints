class Error(object):

    def __init__(self, *contents):
        self._top = []
        self._nested = {}
        for err in contents:
            if isinstance(err, str):
                self._top.append(err)
            if isinstance(err, dict):
                self._nested.update(err)

    def merge(self, err):
        # pylint: disable=protected-access
        self._top.extend(err._top)
        for (key, child) in err._nested.items():
            if key in self._nested:
                self._nested[key].merge(child)
            else:
                self._nested[key] = child

    def unwrap(self):
        result = self._top
        if self._nested:
            d = {key: err.unwrap() for (key, err) in self._nested.items()}
            result.append(d)
        return result

    def __eq__(self, err):
        # pylint: disable=protected-access
        return self._top == err._top and self._nested == err._nested

    def __nonzero__(self):
        return bool(self._top) or bool(self._nested)

    def __repr__(self):
        return repr((self._top, self._nested))
