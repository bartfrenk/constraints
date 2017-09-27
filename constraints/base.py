from abc import ABCMeta, abstractmethod


class BaseConstraints(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def check(self, val, **ctx):
        pass

    def __call__(self, val, **ctx):
        return self.check(val, **ctx)


class Generic(BaseConstraints):

    def __init__(self, code, pred):
        self._code = code
        self._pred = pred


    def check(self, val, **ctx):
        if not self._pred(val):
            return [self._code]
        else:
            return []

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self._code)


def MaxSize(n):
    return Generic('max-size', lambda v: len(v) <= n)


def InstanceOf(cls):
    return Generic('wrong-type', lambda v: isinstance(v, cls))


class Dict(BaseConstraints):

    def __init__(self, **fields):
        self._fields = fields
        self._optional = set()

    @property
    def optional(self):
        return self._optional

    @optional.setter
    def optional(self, keys):
        for key in keys:
            if key not in set(self._fields.keys()):
                raise ValueError('{} is not a key'.format(key))
        self._optional = keys

    def check(self, val, **ctx):
        if not isinstance(val, dict):
            return ['wrong-type']
        root = {}
        for (key, constraints) in self._fields.items():
            errors = []
            if key not in val:
                if key not in self.optional:
                    errors.append('missing')
            else:
                for c in constraints:
                    errors.extend(c.check(val[key], **ctx))
            if errors:
                root[key] = errors
        return [root]


