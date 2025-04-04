import numpy as np


def nan_average(arr: np.ndarray, weights: np.ndarray, axis: int = None) -> np.ndarray:
    """
    Calculate the weighted average of an array, ignoring NaNs.
    Each NaN value is excluded from the weighted sum along the specified axis.
    """
    mask = ~np.isnan(arr)

    if weights.ndim == 1 and axis is not None:
        weights = np.expand_dims(weights, axis=axis)

    weighted_sum = np.nansum(arr * weights * mask, axis=axis)
    valid_weights = np.nansum(weights * mask, axis=axis)

    return weighted_sum / valid_weights
