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


class TripleGrandChild(Base):
    __tablename__ = "grand_child_triple"

    triple_grand_child_id = Column(Integer, primary_key=True)

    parent_a_id = Column(Integer, ForeignKey("child_a.child_id"))
    parent_b_id = Column(Integer, ForeignKey("child_b.child_id"))
    parent_c_id = Column(Integer, ForeignKey("child_c.child_id"))


class TestDeclarative(object):
    def test_missing_non_nullable_returns_error(self, sess):
        cn = sut.FromModel(ChildA)
        actual = cn.check({"child_id": 1}, session=sess)
        assert actual == Error({"name": Error("missing")})

    def test_dangling_foreign_key_returns_error(self, sess):
        cn = sut.FromModel(ChildA)
        actual = cn.check({"child_id": 1,
                           "parent_id": 1,
                           "name": "x"},
                          session=sess)
        assert actual == Error({"parent_id": Error("does-not-exist")})

    def test_existing_foreign_key_passes(self, sess):
        cn = sut.FromModel(ChildA)
        sess.add(Parent(parent_id=1))
        actual = cn.check({"child_id": 1,
                           "parent_id": 1,
                           "name": "x"},
                          session=sess)
        assert not actual

    def test_duplicate_field_in_context_returns_error(self, sess):
        cn = sut.FromModel(ChildA)
        sess.add(Parent(parent_id=1))
        sess.add(ChildA(name="x", parent_id=1))

        actual = cn.check({"child_id": 314,
                           "parent_id": 1,
                           "name": "x"},
                          session=sess)
        assert actual == Error({"name": Error("duplicate")})

    def test_duplicate_field_merges_with_other_errors(self, sess):
        cn = sut.FromModel(ChildA)
        sess.add(Parent(parent_id=1))
        sess.add(ChildA(child_id=1, name=11 * "x", parent_id=1))

        actual = cn.check({"child_id": 2,
                           "parent_id": 1,
                           "name": 11 * "x"},
                          session=sess)
        assert actual == Error({"name": Error("max-size", "duplicate")})

    def test_consider_foreign_key_dangling_when_out_of_context(self, sess):
        cn = sut.FromModel(ChildA)
        owner = Owner(owner_id=1)
        sess.add(owner)
        sess.add(Owner(owner_id=2))
        sess.add(Parent(parent_id=1, owner_id=2))

        actual = cn.check({"parent_id": 1,
                           "name": "x"},
                          session=sess,
                          within=owner)

        assert actual == Error({"parent_id": Error("does-not-exist")})


class TestMultiPathConstraints(object):
    def test_no_error_when_paths_lead_to_identical_object(self, sess):
        sess.add(Parent(parent_id=1))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=1, name='B'))
        sess.commit()
        paths = [[GrandChild.__table__, ChildA.__table__, Parent.__table__],
                 [GrandChild.__table__, ChildB.__table__, Parent.__table__]]
        cn = sut.MultiPathConstraint(paths)

        actual = cn.check({"parent_a_id": 1, "parent_b_id": 1}, session=sess)

        assert not actual

    def test_error_when_two_paths_lead_to_different_object(self, sess):
        sess.add(Parent(parent_id=1))
        sess.add(Parent(parent_id=2))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=2, name='B'))
        sess.commit()
        paths = [[GrandChild.__table__, ChildA.__table__, Parent.__table__],
                 [GrandChild.__table__, ChildB.__table__, Parent.__table__]]
        cn = sut.MultiPathConstraint(paths)

        actual = cn.check({"parent_a_id": 1, "parent_b_id": 1}, session=sess)

        assert actual

    def test_error_when_some_paths_lead_to_different_object(self, sess):
        sess.add(Parent(parent_id=1))
        sess.add(Parent(parent_id=2))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=1, name='B'))
        sess.add(ChildC(child_id=1, parent_id=2, name='C'))
        sess.commit()

        paths = [
            [TripleGrandChild.__table__, ChildA.__table__, Parent.__table__],
            [TripleGrandChild.__table__, ChildB.__table__, Parent.__table__],
            [TripleGrandChild.__table__, ChildC.__table__, Parent.__table__]
        ]
        cn = sut.MultiPathConstraint(paths)

        actual = cn.check({"parent_a_id": 1,
                           "parent_b_id": 1,
                           "parent_c_id": 1},
                          session=sess)
        assert actual
