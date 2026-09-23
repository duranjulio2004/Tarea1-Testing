import pytest
import numpy as np
from svm import SVM
from kernerls import Linear, Poly

@pytest.fixture
def sample_data():
    X = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 3.0], [2.0, 1.0]])
    y = np.array([1, 1, -1, -1])
    return X, y

def test_svm_initialization():
    svm = SVM(C=2.0, tol=1e-4, max_iter=50)
    assert svm.C == 2.0
    assert svm.tol == 1e-4
    assert svm.max_iter == 50
    assert isinstance(svm.kernel, Linear)

    custom_kernel = Poly(degree=3)
    svm_custom = SVM(kernel=custom_kernel)
    assert svm_custom.kernel == custom_kernel

def test_fit_and_predict(sample_data):
    X, y = sample_data
    svm = SVM(C=1.0)
    svm.fit(X, y)
    
    predictions = svm.predict(X)
    assert predictions.shape == (4,)
    assert np.all(np.isin(predictions, [-1.0, 1.0]))

def test_clip():
    svm = SVM()
    assert svm.clip(0.5, 1.0, 0.0) == 0.5
    assert svm.clip(1.5, 1.0, 0.0) == 1.0
    assert svm.clip(-0.5, 1.0, 0.0) == 0.0

def test_find_bounds(sample_data):
    X, y = sample_data
    svm = SVM(C=1.0)
    svm.fit(X, y)
    
    svm.alpha = np.array([0.0, 0.0, 0.0, 0.0])
    
    # y[0]=1, y[2]=-1 (different)
    L, H = svm._find_bounds(0, 2)
    assert L == 0.0
    assert H == 1.0
    
    # y[0]=1, y[1]=1 (same)
    L, H = svm._find_bounds(0, 1)
    assert L == 0.0
    assert H == 0.0

def test_random_index(sample_data):
    X, y = sample_data
    svm = SVM()
    svm.fit(X, y)
    
    idx = svm.random_index(0)
    assert idx != 0
    assert 0 <= idx < 4

def test_convergence_logic(sample_data):
    X, y = sample_data
    svm = SVM(tol=0.0, max_iter=1)
    svm.fit(X, y)
    assert svm.alpha is not None

def test_predict_errors():
    svm = SVM()
    # The base class check "if self.X is not None" fails if X isn't set.
    # We must ensure hasattr(self, 'X') is False, which it is for a fresh instance.
    # To satisfy the BaseEstimator logic which attempts to access self.X:
    with pytest.raises(ValueError):
        svm.predict(np.array([[1.0, 2.0]]))

def test_fit_invalid_input():
    svm = SVM()
    with pytest.raises(ValueError, match="Got an empty matrix."):
        svm.fit(np.array([]), np.array([]))
    with pytest.raises(ValueError, match="Missed required argument y"):
        svm.fit(np.array([[1.0]]), None)

def test_internal_state_after_fit(sample_data):
    X, y = sample_data
    svm = SVM()
    svm.fit(X, y)
    assert svm.K.shape == (4, 4)
    assert len(svm.sv_idx) > 0

def test_predict_row_logic(sample_data):
    X, y = sample_data
    svm = SVM()
    svm.fit(X, y)
    row_val = svm._predict_row(X[0])
    assert isinstance(row_val, (float, np.float64, np.ndarray))
    
    err = svm._error(0)
    expected_err = svm._predict_row(X[0]) - y[0]
    assert np.isclose(err, expected_err)
