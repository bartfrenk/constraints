# pylint: disable=redefined-outer-name, no-self-use
import constraints.declarative as sut
from constraints.error import Error

from .fixtures import Parent, ChildA, ChildB, ChildC, GrandChild, TripleGrandChild, Owner
from .fixtures import sess  # pylint: disable=unused-import


class TestFromModel(object):
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
        # TODO: refactor this test
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

    def test_multi_path_constraints_trigger(self, sess):
        # TODO: refactor this test
        sess.add(Parent(parent_id=1))
        sess.add(Parent(parent_id=2))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=2, name='B'))
        sess.commit()
        cn = sut.FromModel(GrandChild)

        actual = cn.check({"parent_a_id": 1, "parent_b_id": 1}, session=sess)

        unwrapped = actual.unwrap()
        assert len(unwrapped) == 1
        assert set(unwrapped[0].keys()[0]) == {"parent_a_id", "parent_b_id"}
        assert unwrapped[0].keys()[1] == "name"
        assert unwrapped[0].values() == [["mismatch (parent)"], ["missing"]]

    def test_ignore_correctly_applied_to_multi_path_constraints(self, sess):
        sess.add(Parent(parent_id=1))
        sess.add(Parent(parent_id=2))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=2, name='B'))
        sess.commit()
        cn = sut.FromModel(GrandChild, ignore=set([Parent]))

        actual = cn.check({"parent_a_id": 1, "parent_b_id": 1}, session=sess)

        assert actual == Error({"name": Error("missing")})


class TestMultiPathConstraints(object):
    # TODO: refactor these tests
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

        unwrapped = actual.unwrap()
        assert len(unwrapped) == 1
        assert set(*unwrapped[0].keys()) == {"parent_a_id", "parent_b_id"}
        assert unwrapped[0].values() == [["mismatch (parent)"]]

    def test_that_key_map_is_applied_appropriately(self, sess):
        def key_map(attr):
            if attr == "parent_a_id":
                return "A"
            elif attr == "parent_b_id":
                return "B"

        sess.add(Parent(parent_id=1))
        sess.add(ChildA(child_id=1, parent_id=1, name='A'))
        sess.add(ChildB(child_id=1, parent_id=1, name='B'))
        sess.commit()
        paths = [[GrandChild.__table__, ChildA.__table__, Parent.__table__],
                 [GrandChild.__table__, ChildB.__table__, Parent.__table__]]
        cn = sut.MultiPathConstraint(paths, key_map=key_map)

        actual = cn.check({"A": 1, "B": 1}, session=sess)

        assert not actual

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

        unwrapped = actual.unwrap()
        assert len(unwrapped) == 1
        assert set(*unwrapped[0].keys()) == {"parent_a_id", "parent_b_id",
                                             "parent_c_id"}
        assert unwrapped[0].values() == [["mismatch (parent)"]]


class TestCreateMultiPathConstraints(object):
    def test_find_all_multi_path_constraints(self):
        # pylint: disable=protected-access
        actual = sut.create_multi_path_constraints(GrandChild.__table__)
        expected = sut.MultiPathConstraint(
            [[GrandChild.__table__, ChildA.__table__, Parent.__table__],
             [GrandChild.__table__, ChildB.__table__, Parent.__table__]])

        assert len(actual) == 1
        assert actual[0]._foreign_keys == expected._foreign_keys

    def test_ignore_multi_path_constraints_ending_in_ignore_set(self):
        actual = sut.create_multi_path_constraints(GrandChild.__table__,
                                                   ignore={Parent.__table__})
        assert not actual
