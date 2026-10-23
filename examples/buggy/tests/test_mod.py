from pkg.mod import add, mean


def test_add():
    assert add(2, 3) == 5


def test_mean():
    assert mean([1, 2, 3]) == 2.0
