import numpy as np


from scipy.spatial.distance import cdist


def hausdorff_distance_optimized(a, b):
    """Optimized Hausdorff distance calculation using SciPy."""
    assert a.shape[1] == b.shape[1] == 3, "Point sets must have 3D coordinates"

    ca = np.average(a, axis=0)
    cb = np.average(b, axis=0)
    t2 = cb - ca

    a = a + t2

    distance_matrix = cdist(a, b)
    max_dist_a_to_b = np.max(np.min(distance_matrix, axis=1))
    max_dist_b_to_a = np.max(np.min(distance_matrix, axis=0))

    return max(max_dist_a_to_b, max_dist_b_to_a)


def hausdorff_distance(a, b):
    # dist = np.zeros(a.shape[0])
    # t = b - a
    # for i in range(a.shape[0]):
    #     dist[i] = max(compute_distance(a + t[i], b), compute_distance(b, a + t[i]))
    #
    # return np.min(dist)

    ca = np.average(a, axis=0)
    cb = np.average(b, axis=0)
    t2 = cb - ca

    dist2 = max(compute_distance(a + t2, b), compute_distance(b, a + t2))
    return dist2


def compute_distance(a, b):
    dist = np.zeros(a.shape[0])
    for i in range(a.shape[0]):
        dist[i] = np.min(np.linalg.norm(b - a[i], axis=1))
    return np.max(dist)
