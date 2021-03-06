"""Create constraint objects from SQLAlchemy models."""
from __future__ import print_function
from datetime import datetime
from sqlalchemy import UniqueConstraint

from .base import InstanceOf, MaxSize, Dict, BaseConstraints
from .error import Error
from .traversal import multi_paths


class FromModel(BaseConstraints):
    """Constraints derived from a SQLAlchemy model."""

    def __init__(self, model, key_map=None, forbidden=None, ignore=None):
        """Create constraints from a SQLAlchemy model.

        :param model: The model to derive the constraints from.
        :param key_map: The map from column names to allowed keys in the dict.
        :param forbidden: Set of forbidden column names.
        :param ignore: The models to ignore as endpoints for multipath constraints.
        """
        self._model = model
        self._forbidden = forbidden or set()
        self._key_map = key_map or (lambda x: x)
        self._per_field_cns = self._create_per_field_cns()
        self._root_cns = self._create_root_cns()
        self._multi_path_cns = self._create_multi_path_constraints(ignore or
                                                                   set())

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
        for c in self._multi_path_cns:
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

    def _create_multi_path_constraints(self, ignore):
        start_tbl = self._model.__table__
        ignore_tbls = set(model.__table__ for model in ignore)
        return create_multi_path_constraints(start_tbl, self._key_map,
                                             ignore_tbls)

    def add_constraint(self, constraint):
        self._root_cns.append(constraint)

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self._model.__name__)


class ForeignKeyExists(BaseConstraints):
    """Constraint that checks whether a foreign key exists."""

    def __init__(self, fk):
        """Create a constraint.

        :param fk: The foreign key to check for.
        """
        self._fk = fk

    @staticmethod
    def _create_within_filter(pk_column, within):
        fks = pk_column.table.foreign_keys
        refs = [(fk, fk.get_referent(within.__table__).key) for fk in fks
                if fk.references(within.__table__)]
        return [fk.parent == getattr(within, key) for (fk, key) in refs]

    def check(self, val, **ctx):
        """Check the constraint.

        :param val: The value to check.
        :param ctx: The context.  Should contain a session, and may contain a
            'within' parameter.  See 'FromModel'.
        """
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
    """Constraint that checks whether a uniqueness constraint is violated."""

    def __init__(self, unique, key_map=None):
        """Creates a constraint from a SQLAlchemy uniqueness constraint.

        :param unique: The uniqueness constraint.
        :param key_map: The map from model attributes to keys in the dict.
        """

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
        """Checks the uniqueness constraint.

        Requires a SQLAlchemy session to be in the context under the key
        'session'.

        :param val: The value to check.

        :returns: An Error object.
        """

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


class MultiPathConstraint(BaseConstraints):
    """A multi-path constraint checks whether two distinct foreing key chains,
    starting at some base table lead to the same instance.  For example,

    Given the following chains of foreign keys (with the table containing the
    foreign key at the tail of the arrow):

        - GrandChild --> ChildA --> Parent

        - GrandChild --> ChildB --> Parent

    and a dict of values `val` for the ChildA and ChildB foreign keys in
    GrandChild.  A multi-path constraint of the list of paths ``[[GrandChild,
    ChildA, Parent], [GrandChild, ChildB, Parent]]``, checks whether the ChildA
    and ChildB instances referred to by the foreign keys in `val` point to the
    same Parent instance, and it returns a truthy Error object when they don't.
    """

    def __init__(self, paths, key_map=None):
        """Create a multi-path constraint for the list of paths `path`.

        :param paths: The list of paths this multi-path constraint is for.
        :param key_map: Maps the model attributes to the keys in the value to be checked.

        :returns: An `Error` object, truthy, with a description of the error, if
                  the paths lead to different instances, a trivial and falsy
                  `Error` object otherwise.
        """
        self._key_map = key_map or (lambda x: x)
        self._foreign_keys = self._get_foreign_keys(paths)

    def check(self, val, **ctx):
        """Check the MultiPath constraint on `val`.

        The context should contain a key `session` that maps to a SQLAlchemy
        session.
        """
        if 'session' not in ctx:
            return Error()
        session = ctx['session']

        if not isinstance(val, dict):
            return Error()

        results = set()
        mismatches = []
        for (key, v) in val.items():
            if key in self._foreign_keys:
                (fk_column, path) = self._foreign_keys[key]
                query = self._path_query(session, fk_column, path, v)
                for row in query:
                    results.add(row)
                    mismatches.append(key)
        if len(results) == 1:
            return Error()
        return Error({tuple(mismatches):
                      Error("mismatch ({})".format(self._end_table_name))})

    def _get_foreign_keys(self, paths):
        """
        Construct a dict of the foreign key fields in the joint start of the
        paths, to a tuple containing the column referred to by the foreign key
        in the second table in the path, and the path itself.
        """
        result = {}
        start = paths[0][0]
        for fk in start.foreign_keys:
            for path in paths:
                if fk.references(path[1]):
                    result[self._key_map(fk.parent.name)] = (fk.column, path)
        return result

    @property
    def _end_table_name(self):
        return self._foreign_keys.values()[0][-1][-1].name

    @staticmethod
    def _path_query(session, fk_column, path, v):
        it = reversed(path[1:])
        query = session.query(next(it))
        for tb in it:
            query = query.join(tb)
        return query.filter(fk_column == v)


def create_multi_path_constraints(start_tbl, key_map=None, ignore=None):
    """Create the complete list of multi-path constraints that start at
    `start_tbl`.  Ignores paths that end in a table contained in `ignore`.

    :param start_tbl: The table for which to create the multi-path constraints.
    :param key_map: The key map, mapping fields of the value to check to
        attributes of the model.
    :param ignore: The set of tables to ignore as path endpoints.

    :returns: A list of `MultiPathConstraint` instances, one for each set of
              multi-paths starting from `start_tbl` and ending in a table not in
              `ignore`.
    """
    ignore = ignore or set()

    def adj(tb):
        return [fk.column.table for fk in tb.foreign_keys]

    constraints = []
    end_tbl_to_paths = multi_paths(adj, start_tbl)
    for (end_tbl, paths) in end_tbl_to_paths.items():
        if end_tbl not in ignore:
            constraints.append(MultiPathConstraint(paths, key_map))
    return constraints
