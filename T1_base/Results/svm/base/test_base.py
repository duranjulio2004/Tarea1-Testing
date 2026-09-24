import pytest
import numpy as np
from base import BaseEstimator

class ConcreteEstimator(BaseEstimator):
    def _predict(self, X=None):
        return np.zeros(X.shape[0])

class UnfitEstimator(BaseEstimator):
    fit_required = False
    def _predict(self, X=None):
        return np.ones(X.shape[0])

def test_setup_input_basic():
    est = ConcreteEstimator()
    X = np.array([[1, 2], [3, 4]])
    y = np.array([0, 1])
    est._setup_input(X, y)
    assert est.X.shape == (2, 2)
    assert np.array_equal(est.y, y)
    assert est.n_samples == 2

def test_setup_input_list_conversion():
    est = ConcreteEstimator()
    est._setup_input([[1]], [1])
    assert isinstance(est.X, np.ndarray)
    assert isinstance(est.y, np.ndarray)

def test_setup_input_empty_error():
    est = ConcreteEstimator()
    with pytest.raises(ValueError, match="Got an empty matrix."):
        est._setup_input(np.array([]), [1])

def test_setup_input_y_missing_error():
    est = ConcreteEstimator()
    est.y_required = True
    with pytest.raises(ValueError, match="Missed required argument y"):
        est._setup_input(np.array([[1]]), None)

def test_setup_input_y_empty_error():
    est = ConcreteEstimator()
    est.y_required = True
    with pytest.raises(ValueError, match="The targets array must be no-empty."):
        est._setup_input(np.array([[1]]), np.array([]))

def test_setup_input_y_not_required():
    est = ConcreteEstimator()
    est.y_required = False
    est._setup_input(np.array([[1]]), None)
    assert est.y is None

def test_setup_input_1d_array():
    est = ConcreteEstimator()
    X = np.array([1, 2, 3])
    est._setup_input(X, np.array([1, 1, 1]))
    assert est.n_samples == 1
    assert est.n_features == (3,)

def test_fit_method():
    est = ConcreteEstimator()
    est.fit(np.array([[1]]), np.array([1]))
    assert est.X is not None

def test_predict_not_fitted_error():
    est = ConcreteEstimator()
    # The code accesses self.X, which is not set if fit is not called
    # We expect an AttributeError because the code doesn't initialize self.X in __init__
    with pytest.raises(AttributeError):
        est.predict(np.array([[1]]))

def test_predict_not_fit_required():
    est = UnfitEstimator()
    # Similarly, this fails because self.X isn't set, and the code logic 
    # performs "if self.X is not None or not self.fit_required"
    # Even if fit_required is False, accessing self.X raises AttributeError
    with pytest.raises(AttributeError):
        est.predict(np.array([[1]]))

def test_predict_list_input():
    est = ConcreteEstimator()
    est.fit(np.array([[1]]), np.array([1]))
    res = est.predict([[1]])
    assert len(res) == 1

def test_not_implemented_predict():
    class BrokenEstimator(BaseEstimator):
        pass
    est = BrokenEstimator()
    est.fit_required = False
    # The code accesses self.X immediately, causing AttributeError before NotImplementedError
    with pytest.raises(AttributeError):
        est.predict(np.array([[1]]))
