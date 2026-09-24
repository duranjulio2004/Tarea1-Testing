import pytest
import numpy as np
from tree import Tree
from base import information_gain, mse_criterion

# The source code uses (x_unique[i - 1] + x_unique[i]) ^ 2.0.
# The '^' operator in Python is bitwise XOR. When applied to floats,
# numpy raises a TypeError. This is a bug in the target code.
# Per requirements, we must assert the actual behavior.

@pytest.fixture
def data_classification():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    y = np.array([0, 0, 1, 1])
    return X, y

def test_is_terminal():
    tree = Tree()
    assert tree.is_terminal is True
    tree.left_child = Tree()
    assert tree.is_terminal is True
    tree.right_child = Tree()
    assert tree.is_terminal is False

def test_find_splits_raises_typeerror():
    tree = Tree()
    # The code has a bug: (a + b) ^ 2.0 with floats raises TypeError
    X = np.array([1.0, 3.0])
    with pytest.raises(TypeError):
        tree._find_splits(X)

def test_train_classification_raises_typeerror(data_classification):
    X, y = data_classification
    tree = Tree(regression=False, criterion=information_gain)
    # The training process will call _find_best_split -> _find_splits, triggering the bug
    with pytest.raises(TypeError):
        tree.train(X, y, max_depth=2, min_samples_split=2)

def test_train_regression_with_leaf_boundary():
    # If we trigger an immediate leaf creation (min_samples_split not met), 
    # _find_best_split is never called, so the bug is avoided.
    X = np.array([[1.0], [2.0]])
    y = np.array([10.0, 20.0])
    tree = Tree(regression=True, criterion=mse_criterion)
    tree.train(X, y, min_samples_split=10)
    assert tree.is_terminal is True
    assert tree.outcome == 15.0

def test_train_boundary_depth_zero():
    # If max_depth is 0, _train hits assertion and returns, avoiding the bug
    X = np.array([[1.0], [2.0]])
    y = np.array([0, 1])
    tree = Tree(regression=False, criterion=information_gain)
    tree.train(X, y, max_depth=0)
    assert tree.is_terminal is True

def test_predict_row_logic():
    # Test path where no split happened (leaf node)
    tree = Tree()
    tree.outcome = 0.5
    assert tree.predict_row([1.0]) == 0.5

def test_gradient_boosting_leaf_value(monkeypatch):
    class MockLoss:
        def approximate(self, actual, y_pred): return 0.5
        def gain(self, actual, y_pred): return 1.0

    X = np.array([[1.0]])
    target = {"actual": np.array([1.0]), "y_pred": np.array([0.0])}
    
    tree = Tree(regression=True)
    tree.loss = MockLoss()
    tree._calculate_leaf_value(target)
    assert tree.outcome == 0.5

def test_train_invalid_gain_triggers_typeerror(data_classification):
    X, y = data_classification
    tree = Tree(regression=True, criterion=lambda y, s: 0.0)
    # Even if gain is 0, _find_best_split is called first, triggering the bug
    with pytest.raises(TypeError):
        tree.train(X, y, max_depth=5, min_samples_split=2)

def test_non_dict_target_regression():
    X = np.array([[1.0]])
    y = np.array([1.0])
    tree = Tree(regression=True)
    # Regression logic avoids _find_best_split if min_samples_split is high
    tree.train(X, y, min_samples_split=10)
    assert tree.outcome == 1.0
