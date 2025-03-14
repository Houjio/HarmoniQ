import harmoniq.core.utils as utils

import numpy as np


def test_nan_mean():
    arr = np.array([4, 4, np.nan, 4, 4])
    weight = np.array([1, 1, 1, 1, 1])
    assert utils.nan_average(arr, weight) == 4


def test_nan_mean_weighted():
    arr = np.array([5, 2, np.nan, 4, 3])
    weight = np.array([1, 2, 3, 4, 5])
    assert utils.nan_average(arr, weight) == np.average(
        [5, 2, 4, 3], weights=[1, 2, 4, 5]
    )


def test_nan_mean_axis():
    arr = np.array([[5, 2, np.nan, 4, 3], [5, 2, 3, 4, 3]])
    weight0 = np.array([1, 2, 3, 4, 5])
    assert np.allclose(
        utils.nan_average(arr, weight0, axis=0), np.array([5.0, 2.0, 3.0, 4.0, 3.0])
    )

    weight1 = np.array([1, 2])
    assert np.allclose(utils.nan_average(arr, weight1, axis=1), np.array([3.5, 3.4]))
