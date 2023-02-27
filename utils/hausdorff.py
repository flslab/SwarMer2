import numpy as np


def hausdorff_distance(a, b):
    t = b[0] - a[0]
    return compute_distance(a + t, b)


def compute_distance(a, b):
    dist = np.zeros_like(a)
    for i in range(a.shape[0]):
        dist[i] = np.min(np.linalg.norm(b - a[i], axis=1))
    return np.max(dist)
