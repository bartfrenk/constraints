import pytest
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, \
    Boolean, ForeignKey, create_engine, UniqueConstraint


@pytest.fixture
def sess():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


Base = declarative_base()


class Owner(Base):
    __tablename__ = "owner"

    owner_id = Column(Integer, primary_key=True)


class Parent(Base):
    __tablename__ = "parent"

    parent_id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("owner.owner_id"))


class ChildA(Base):
    __tablename__ = "child_a"

    child_id = Column(Integer, primary_key=True)

    name = Column(String(10), nullable=False)
    opt = Column(Boolean)

    parent_id = Column(Integer, ForeignKey("parent.parent_id"))
    __table_args__ = (UniqueConstraint("parent_id", "name"), )


class ChildB(Base):
    __tablename__ = "child_b"

    child_id = Column(Integer, primary_key=True)

    name = Column(String(10), nullable=False)
    opt = Column(Boolean)

    parent_id = Column(Integer, ForeignKey("parent.parent_id"))
    __table_args__ = (UniqueConstraint("parent_id", "name"), )


class ChildC(Base):
    __tablename__ = "child_c"

    child_id = Column(Integer, primary_key=True)

    name = Column(String(10), nullable=False)
    opt = Column(Boolean)

    parent_id = Column(Integer, ForeignKey("parent.parent_id"))
    __table_args__ = (UniqueConstraint("parent_id", "name"), )


class GrandChild(Base):
    __tablename__ = "grand_child"

    grand_child_id = Column(Integer, primary_key=True)

    parent_a_id = Column(Integer, ForeignKey("child_a.child_id"))
    parent_b_id = Column(Integer, ForeignKey("child_b.child_id"))
    name = Column(String(2), nullable=False)


class TripleGrandChild(Base):
    __tablename__ = "grand_child_triple"

    triple_grand_child_id = Column(Integer, primary_key=True)

    parent_a_id = Column(Integer, ForeignKey("child_a.child_id"))
    parent_b_id = Column(Integer, ForeignKey("child_b.child_id"))
    parent_c_id = Column(Integer, ForeignKey("child_c.child_id"))
