
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from constraints.base import InstanceOf, MaxSize, Dict, BaseConstraints

from constraints._models import Base, Template


class FromModel(BaseConstraints):

    def __init__(self, model, key_map=None):
        self._model = model
        self.constraints = self._create(key_map)

    def check(self, val, **ctx):
        return self.constraints(val, **ctx)

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
        root = Dict(**constraints)
        root.optional = optional
        return root

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

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])

c = FromModel(Template, to_camel_case)

x = {
    "templateSetId": 2,
    "templateId": 1,
    "width": 1200,
    "height": 800,
    "readyForUse": True,
    "name": "TestTemplate" + 80 * "as"
}


def init_db():
    url = "postgresql://docker:docker@localhost:15433/docker"
    engine = create_engine(url, echo=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)
