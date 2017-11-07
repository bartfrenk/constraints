"""Defines basic constraint objects."""
from abc import ABCMeta, abstractmethod

from .error import Error


class BaseConstraints(object):
    """Abstract base class for constraints."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def check(self, val, **ctx):
        """Check argument for constraints within a context.

        :param val: The value to check.
        :param ctx: The context to run the check in, for example, this might
            include a database session.

        :returns: An non-trivial Error object when the argument does not satisfy
                  the constraints, or Error() when it does.

        :rtype: An Error object.
        """
        pass

    def __call__(self, val, **ctx):
        return self.check(val, **ctx)


class Generic(BaseConstraints):
    """Generic constraint from a predicate."""

    def __init__(self, code, pred):
        """Create a generic constraint.

        :param code: On error, the constraint returns Error(code).
        :param pred: The predicate to check for.
        """
        self._code = code
        self._pred = pred

    def check(self, val, **ctx):
        if not self._pred(val):
            return Error(self._code)
        return Error()

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self._code)


def MaxSize(n):
    """Create generic constraint on the length of the value."""
    return Generic('max-size', lambda v: len(v) <= n)


def InstanceOf(cls):
    """Create generic constraint on the type of the value."""
    return Generic('wrong-type', lambda v: isinstance(v, cls))


class Dict(BaseConstraints):
    """Composite constraint on a Python dict."""

    def __init__(self, **fields):
        self._fields = fields
        self._optional = set()
        self._forbidden = set()

    @property
    def optional(self):
        return self._optional

    @optional.setter
    def optional(self, keys):
        for key in keys:
            if key not in set(self._fields.keys()):
                raise ValueError('{} is not a key'.format(key))
        self._optional = keys

    @property
    def forbidden(self):
        return self._forbidden

    @forbidden.setter
    def forbidden(self, keys):
        for key in keys:
            if key not in set(self._fields.keys()):
                raise ValueError('{} is not a key'.format(key))
        self._forbidden = keys

    def check(self, val, **ctx):
        if not isinstance(val, dict):
            return Error('wrong-type')
        root = {}
        for (key, constraints) in self._fields.items():
            errors = Error()
            if key not in val:
                if key not in self.optional and key not in self.forbidden:
                    errors.merge(Error('missing'))
            elif key in self.forbidden:
                errors.merge(Error('forbidden'))
            else:
                for c in constraints:
                    errors.merge(c.check(val[key], **ctx))
            if errors:
                root[key] = errors
        if root:
            return Error(root)
        return Error()


class All(BaseConstraints):

    def __init__(self, *constraints):
        self._constraints = list(constraints)

    def check(self, val, **ctx):
        err = Error()
        for c in self._constraints:
            err.merge(c.check(val, **ctx))
        return err
