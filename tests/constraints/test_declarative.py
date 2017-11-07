# pylint: disable=redefined-outer-name, no-self-use
import pytest
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, \
    Boolean, ForeignKey, create_engine, UniqueConstraint

import constraints.declarative as sut
from constraints.error import Error


@pytest.fixture
def sess():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()

Base = declarative_base()


class Parent(Base):
    __tablename__ = "parent"

    parent_id = Column(Integer, primary_key=True)


class Child(Base):
    __tablename__ = "child"

    child_id = Column(Integer, primary_key=True)

    name = Column(String(10), nullable=False)
    opt = Column(Boolean)

    parent_id = Column(Integer, ForeignKey("parent.parent_id"))
    __table_args__ = (
        UniqueConstraint("parent_id", "name"),
    )


class TestDeclarative(object):

    def test_missing_non_nullable_returns_error(self, sess):
        cn = sut.FromModel(Child)
        actual = cn.check({"child_id": 1}, session=sess)
        assert actual == Error({"name": Error("missing")})

    def test_dangling_foreign_key_returns_error(self, sess):
        cn = sut.FromModel(Child)
        actual = cn.check({"child_id": 1, "parent_id": 1, "name": "x"}, session=sess)
        assert actual == Error({"parent_id": Error("does-not-exist")})

    def test_existing_foreign_key_passes(self, sess):
        cn = sut.FromModel(Child)
        sess.add(Parent(parent_id=1))
        actual = cn.check({"child_id": 1, "parent_id": 1, "name": "x"}, session=sess)
        assert not actual

    def test_duplicate_field_in_context_returns_error(self, sess):
        cn = sut.FromModel(Child)
        sess.add(Parent(parent_id=1))
        sess.add(Child(name="x", parent_id=1))

        actual = cn.check({"child_id": 314, "parent_id": 1, "name": "x"}, session=sess)
        assert actual == Error({"name": Error("duplicate")})

    def test_duplicate_field_merges_with_other_errors(self, sess):
        cn = sut.FromModel(Child)
        sess.add(Parent(parent_id=1))
        sess.add(Child(name=11 * "x", parent_id=1))

        actual = cn.check({"child_id": 314, "parent_id": 1, "name": 11 * "x"}, session=sess)
        assert actual == Error({"name": Error("duplicate", "max-size")})
