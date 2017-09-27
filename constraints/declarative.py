from sqlalchemy import UniqueConstraint

from constraints.base import InstanceOf, MaxSize, Dict, BaseConstraints


class FromModel(BaseConstraints):

    def __init__(self, model, key_map=None):
        self._model = model
        self.constraints = self._create(key_map)

    def check(self, val, **ctx):
        errors = []
        for c in self.constraints:
            errors.extend(c.check(val, **ctx))
        return errors

    def _create(self, key_map):
        key_map = key_map or (lambda x: x)

        constraints = {}
        optional = set()
        for col in self._model.__table__.columns:
            ty = col.type
            key = key_map(col.key)
            if col.nullable:
                optional.add(key)
            if hasattr(ty, "python_type"):
                constraints.setdefault(key, []).append(InstanceOf(ty.python_type))
            if hasattr(ty, "length"):
                constraints.setdefault(key, []).append(MaxSize(ty.length))
            for fk in iter(col.foreign_keys):
                constraints.setdefault(key, []).append(ForeignKeyExists(fk))

        duplicates = []
        for cons in self._model.__table__.constraints:
            if isinstance(cons, UniqueConstraint):
                duplicates.append(Unique(cons, key_map))
        root = Dict(**constraints)
        root.optional = optional
        duplicates.append(root)
        return duplicates

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__,
                                 self._model.__name__)


class ForeignKeyExists(BaseConstraints):

    def __init__(self, fk):
        self._fk = fk

    def check(self, val, **ctx):
        session = ctx['session']
        column = self._fk.column
        exists = session.query(column).filter(column == val).first()
        if not exists:
            return ["does_not_exist"]
        return []


class Unique(BaseConstraints):

    def __init__(self, unique, key_map=None):
        self._unique = unique
        self._key_map = key_map or (lambda x: x)

    def check(self, val, **ctx):
        session = ctx['session']
        cols = list(self._unique.columns)
        exists = False
        if all(self._key_map(col.key) in val for col in cols):
            filters = [col == val[self._key_map(col.key)] for col in cols]
            exists = session.query(cols[0]).filter(*filters).first()
        if exists:
            keys = [col for col in cols if not col.foreign_keys]
            if len(keys) == 1:
                return [{self._key_map(keys[0].key): "duplicate"}]
            return ["duplicate"]
        return []
