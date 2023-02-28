import numpy as np


def hausdorff_distance(a, b):
    dist = np.zeros_like(a)
    t = a - b
    for i in range(a.shape[0]):
        dist[i] = compute_distance(a + t[i], b)

    return np.min(dist)


def compute_distance(a, b):
    dist = np.zeros_like(a)
    for i in range(a.shape[0]):
        dist[i] = np.min(np.linalg.norm(b - a[i], axis=1))
    return np.max(dist)
