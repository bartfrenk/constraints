"""Create constraint objects from SQLAlchemy models."""
from __future__ import print_function
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
        self._per_field_cns = self._create_per_field_cns()
        self._root_cns = self._create_root_cns()

    def check(self, val, **ctx):
        """Check constraints on value.

        :param val: The value to check.
        :param ctx: The context in which to run the check, this may include the
            following keyword parameters:

                - session: The SQLAlchemy session, passing this allows the
                  checker to do database queries to verify constraints.

                - within: A SQLAlchemy entity, if passed, foreign keys are
                  considered dangling if they refer to an entity whose model has
                  a foreign key relation to the model of the entity passed to
                  within, but that foreign key does not refer to the `within`
                  entity.

        :returns: A falsy `Error` object, if constraints are not satisfied, the
                  truthy one otherwise.
        """
        errors = self._per_field_cns(val, **ctx)
        for c in self._root_cns:
            errors.merge(c.check(val, **ctx))
        return errors

    @classmethod
    def _is_optional(cls, col):
        return col.nullable or col.primary_key or \
            col.default is not None or \
            col.server_default is not None

    def _create_per_field_cns(self):
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

        per_field_cns = Dict(**constraints)
        per_field_cns.optional = optional
        per_field_cns.forbidden = {self._key_map(key)
                                   for key in self._forbidden}
        return per_field_cns

    def _create_root_cns(self):
        root_cns = []
        for cons in self._model.__table__.constraints:
            if isinstance(cons, UniqueConstraint):
                root_cns.append(Unique(cons, self._key_map))
        return root_cns

    def add_constraint(self, constraint):
        self._root_cns.append(constraint)

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self._model.__name__)


class ForeignKeyExists(BaseConstraints):
    def __init__(self, fk):
        self._fk = fk

    @staticmethod
    def _create_within_filter(pk_column, within):
        fks = pk_column.table.foreign_keys
        refs = [(fk, fk.get_referent(within.__table__).key) for fk in fks
                if fk.references(within.__table__)]
        return [fk.parent == getattr(within, key) for (fk, key) in refs]

    def check(self, val, **ctx):
        if 'session' not in ctx:
            return Error()
        session = ctx['session']
        filters = []
        column = self._fk.column
        filters.append(column == val)
        if 'within' in ctx:
            within = ctx['within']
            filters.extend(self._create_within_filter(column, within))
        exists = session.query(column).filter(*filters).first()
        if not exists:
            return Error("does-not-exist")
        return Error()


class Unique(BaseConstraints):
    def __init__(self, unique, key_map=None):
        # TODO: better name for unique, and document
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


from traversal import multipaths


def adj(tb):
    return [fk.column.table for fk in tb.foreign_keys]


def find_paths(model):
    paths = multipaths(adj, model)
    return paths


class MultiPathConstraint(BaseConstraints):
    def __init__(self, paths, key_map=None):
        self._key_map = key_map or (lambda x: x)
        self._paths = paths
        self._foreign_keys = self._get_foreign_keys(paths)

    def _get_foreign_keys(self, paths):
        result = {}
        base = self._paths[0][0]
        for fk in base.foreign_keys:
            for path in paths:
                if fk.references(path[1]):
                    result[fk.parent.name] = (fk.column, path)
        return result

    def check(self, val, **ctx):
        if 'session' not in ctx:
            return Error()
        session = ctx['session']

        if not isinstance(val, dict):
            return Error()

        results = set()
        for (field, v) in val.items():
            key = self._key_map(field)
            if key in self._foreign_keys:
                (fk_column, path) = self._foreign_keys[key]
                query = self._path_query(session, fk_column, path, v)
                for row in query:
                    results.add(row)
        if len(results) == 1:
            return Error()
        return Error({"bla": Error("")})

        # TODO: add in val to constrain the result of query
        # 1. build list of triples (foreign key, relevant keys in val, path)

    @staticmethod
    def _path_query(session, fk_column, path, v):
        it = reversed(path[1:])
        query = session.query(next(it))
        for tb in it:
            query = query.join(tb)
        return query.filter(fk_column == v)
