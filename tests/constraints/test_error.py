# pylint: disable=no-self-use
from constraints.error import Error

class TestError(object):

    def test_merge_list_of_atomic_errors(self):
        errors = Error("1", "2", "3")
        errors.merge(Error("4", "5", "6"))
        assert errors == Error("1", "2", "3", "4", "5", "6")

    def test_merge_nested_errors(self):
        errors = Error({"u": Error("1"), "v": Error("3")})
        errors.merge(Error({"u": Error("2"), "w": Error("4")}))
        assert errors == Error({"u": Error("1", "2"),
                                "v": Error("3"), "w": Error("4")})

    def test_merge_mixed_errors(self):
        errors = Error("1", {"u": Error("2")})
        errors.merge(Error("3", {"v": Error("4")}))
        assert errors == Error("1", "3", {"u": Error("2"), "v": Error("4")})

    def test_convert_list_of_atomic_errors_to_unwrap(self):
        errors = Error("1", "2", "3")
        assert errors.unwrap() == ["1", "2", "3"]

    def test_convert_nested_errors_to_unwrap(self):
        errors = Error({"u": Error("1"), "v": Error("2")})
        assert errors.unwrap() == [{"u": ["1"], "v": ["2"]}]

    def test_convert_mixed_errors_to_unwrap(self):
        errors = Error("1", {"u": Error("2")})
        assert errors.unwrap() == ["1", {"u": ["2"]}]
