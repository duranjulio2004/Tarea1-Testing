import pytest
import numpy as np
from base import (
    f_entropy,
    information_gain,
    mse_criterion,
    xgb_criterion,
    get_split_mask,
    split,
    split_dataset,
)


def test_f_entropy():
    # Test entropy calculation
    p = np.array([0, 0, 1, 1])
    assert f_entropy(p) == pytest.approx(0.693147, rel=1e-5)
    
    # Test entropy with empty input handling
    # bincount on empty array is empty, which scipy.stats.entropy handles as 0.0
    p_empty = np.array([], dtype=int)
    assert f_entropy(p_empty) == 0.0

    # Test path where result is -inf (log of 0), code checks if == -inf then returns 0.0
    # Note: scipy.entropy returns 0 for empty/uniform inputs, but we test the branch explicitly
    class MockStats:
        def entropy(self, x):
            return -float("inf")
    
    import base
    old_stats = base.stats
    base.stats = MockStats()
    try:
        assert f_entropy(np.array([1])) == 0.0
    finally:
        base.stats = old_stats


def test_information_gain():
    y = np.array([0, 0, 1, 1])
    splits = [np.array([0, 0]), np.array([1, 1])]
    # Entropy of y (0.693) - (0.5 * entropy(0) + 0.5 * entropy(0)) = 0.693
    gain = information_gain(y, splits)
    assert gain == pytest.approx(0.693147)


def test_mse_criterion():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    splits = [np.array([1.0, 2.0]), np.array([3.0, 4.0])]
    # mean=2.5. Split1 (1,2): sum((1-2.5)^2 + (2-2.5)^2) = 2.25+0.25 = 2.5
    # Split2 (3,4): sum((3-2.5)^2 + (4-2.5)^2) = 0.25+2.25 = 2.5
    # criterion = -(2.5 * 0.5 + 2.5 * 0.5) = -2.5
    assert mse_criterion(y, splits) == -2.5


def test_xgb_criterion():
    class MockLoss:
        def gain(self, a, b):
            return np.sum(a) + np.sum(b)

    y = {"actual": np.array([1]), "y_pred": np.array([0])}
    left = {"actual": np.array([1]), "y_pred": np.array([0])}
    right = {"actual": np.array([0]), "y_pred": np.array([0])}
    
    # left(1) + right(0) - initial(1) = 0
    assert xgb_criterion(y, left, right, MockLoss()) == 0


def test_get_split_mask():
    X = np.array([[1, 2], [3, 4], [5, 6]])
    left, right = get_split_mask(X, 0, 3)
    np.testing.assert_array_equal(left, [True, False, False])
    np.testing.assert_array_equal(right, [False, True, True])


def test_split():
    X = np.array([1, 2, 3, 4])
    y = np.array([10, 20, 30, 40])
    left, right = split(X, y, 3)
    np.testing.assert_array_equal(left, [10, 20])
    np.testing.assert_array_equal(right, [30, 40])


def test_split_dataset():
    X = np.array([[1], [5]])
    target = {"a": np.array([10, 50])}
    
    # Test return_X=True
    l_X, r_X, left, right = split_dataset(X, target, 0, 3, return_X=True)
    np.testing.assert_array_equal(l_X, [[1]])
    np.testing.assert_array_equal(r_X, [[5]])
    np.testing.assert_array_equal(left["a"], [10])
    np.testing.assert_array_equal(right["a"], [50])

    # Test return_X=False
    l2, r2 = split_dataset(X, target, 0, 3, return_X=False)
    assert "a" in l2
    assert "a" in r2
    np.testing.assert_array_equal(l2["a"], [10])
