"""Create constraint objects from SQLAlchemy models."""
from datetime import datetime
from sqlalchemy import UniqueConstraint

from .base import InstanceOf, MaxSize, Dict, BaseConstraints
from .error import Error


class FromModel(BaseConstraints):

    def __init__(self, model, key_map=None, forbidden=None):
        """
        Create constraints from a SQLAlchemy model.

        :param model: The model to derive the constraints from.
        :param key_map: The map from column names to allowed keys in the dict.
        :param forbidden: Set of forbidden column names.
        """
        self._model = model
        self._forbidden = forbidden or set()
        self._key_map = key_map or (lambda x: x)
        self.constraints = self._create()

    def check(self, val, **ctx):
        errors = Error()
        for c in self.constraints:
            errors.merge(c.check(val, **ctx))
        return errors

    @classmethod
    def _is_optional(cls, col):
        return col.nullable or col.primary_key or \
            col.default is not None or \
            col.server_default is not None

    def _create_dict_constraint(self, key_map):
        pass

    def _create(self):

        constraints = {}
        optional = set()
        for col in self._model.__table__.columns:
            ty = col.type
            key = self._key_map(col.key)
            if self._is_optional(col):
                optional.add(key)
            constraints[key] = []
            if hasattr(ty, "python_type"):
                if ty.python_type is str:
                    constraints[key].append(InstanceOf(basestring))
                elif ty.python_type is datetime:
                    constraints[key].append(InstanceOf(int))
                else:
                    constraints[key].append(InstanceOf(ty.python_type))
            if hasattr(ty, "length"):
                constraints[key].append(MaxSize(ty.length))
            for fk in iter(col.foreign_keys):
                constraints[key].append(ForeignKeyExists(fk))

        duplicates = []
        for cons in self._model.__table__.constraints:
            if isinstance(cons, UniqueConstraint):
                duplicates.append(Unique(cons, self._key_map))
        root = Dict(**constraints)
        root.optional = optional
        root.forbidden = {self._key_map(key) for key in self._forbidden}
        duplicates.append(root)
        return duplicates

    def add_constraint(self, constraint):
        self.constraints.append(constraint)

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__,
                                 self._model.__name__)


class ForeignKeyExists(BaseConstraints):

    def __init__(self, fk):
        self._fk = fk

    def check(self, val, **ctx):
        if 'session' not in ctx:
            return Error()
        session = ctx['session']
        column = self._fk.column
        exists = session.query(column).filter(column == val).first()
        if not exists:
            return Error("does-not-exist")
        return Error()


class Unique(BaseConstraints):

    def __init__(self, unique, key_map=None):
        self._unique = unique
        self._pk = self._primary_key(unique)
        self._key_map = key_map or (lambda x: x)

    def _primary_key(self, unique):
        # pylint: disable=no-self-use
        return unique.table.primary_key.columns

    def _is_entity(self, exists, val):
        try:
            pks = [val[self._key_map(col.key)] for col in self._pk]
            return pks == list(exists)
        except KeyError:
            return False

    def check(self, val, **ctx):
        if 'session' not in ctx:
            return Error()
        session = ctx['session']
        cols = list(self._unique.columns)
        exists = False
        if all(self._key_map(col.key) in val for col in cols):
            filters = [col == val[self._key_map(col.key)] for col in cols]
            exists = session.query(*self._pk).filter(*filters).first()
        if exists and not self._is_entity(exists, val):
            keys = [col for col in cols if not col.foreign_keys]
            if len(keys) == 1:
                return Error({self._key_map(keys[0].key): Error("duplicate")})
            return Error("duplicate")
        return Error()
