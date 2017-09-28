# pylint: disable=no-self-use
from pytest import mark

import constraints.base as sut
from constraints.error import Error


class TestMaxSize(object):

    def test_non_trivial_result_on_input_too_large(self):
        actual = sut.MaxSize(1).check("test")
        assert Error('max-size') == actual

    def test_trivial_result_on_input_short_enough(self):
        actual = sut.MaxSize(4).check("test")
        assert not actual


class TestInstanceOf(object):

    @mark.parametrize("inp,ty", [
        (True, str),
        ("str", bool)])
    def test_non_trivial_result_when_input_of_wrong_type(self, inp, ty):
        actual = sut.InstanceOf(ty).check(inp)
        assert Error('wrong-type') == actual

    @mark.parametrize("inp,ty", [
        (True, bool),
        ("str", str)])
    def test_trivial_result_when_input_of_correct_type(self, inp, ty):
        actual = sut.InstanceOf(ty).check(inp)
        assert not actual


class TestDict(object):

    def test_run_all_constraints_for_a_single_field(self):
        cn = sut.Dict(key=[sut.InstanceOf(bool), sut.InstanceOf(str)])
        actual = cn.check({"key": 1})
        assert Error({"key": Error("wrong-type", "wrong-type")}) == actual

    def test_for_missing_keys(self):
        cn = sut.Dict(key=[])
        actual = cn.check({})
        assert Error({"key": Error("missing")}) == actual

    def test_allow_optional_keys(self):
        cn = sut.Dict(key=[])
        cn.optional = set(["key"])
        actual = cn.check({})
        assert not actual

    def test_return_empty_list_on_success(self):
        cn = sut.Dict(key=[sut.InstanceOf(bool)])
        actual = cn.check({"key": True})
        assert not actual

    def test_return_wrong_type_on_non_dict(self):
        cn = sut.Dict(key=[sut.InstanceOf(bool)])
        actual = cn.check("test")
        assert Error("wrong-type") == actual


class GenericTest(object):

    def test_return_specified_error_on_predicate_failure(self):
        cn = sut.Generic("code", lambda x: x != 1)
        actual = cn.check(2)
        assert Error("code") == actual

    def test_return_empty_list_on_predicate_success(self):
        cn = sut.Generic("code", lambda x: x != 1)
        actual = cn.check(1)
        assert Error("code") == actual
