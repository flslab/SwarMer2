import math

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.spatial import KDTree
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from scipy.sparse.csgraph import min_weight_full_bipartite_matching
from scipy.sparse import csr_matrix
from matching.games import StableRoommates
import networkx.algorithms.approximation as nx_app
import networkx as nx


def construct_graph(points):
    G = nx.Graph()
    G.add_nodes_from(range(len(points)))

    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            distance = np.linalg.norm(points[i] - points[j])
            G.add_edge(i, j, weight=distance)

    return G


def tsp(points):
    return nx_app.christofides(construct_graph(points), weight="weight")


def mwm(points):
    return nx.min_weight_matching(construct_graph(points))


def matching_bi(points):
    distance_matrix = cdist(points, points)

    np.fill_diagonal(distance_matrix, np.inf)
    distance_matrix = csr_matrix(distance_matrix)
    row_ind, col_ind = min_weight_full_bipartite_matching(distance_matrix)

    matches = list(zip(row_ind, col_ind))
    return matches


def k_means(points, k=4):
    kmeans = KMeans(n_clusters=k, random_state=10)
    kmeans.fit(points)

    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_

    return labels, centroids


def matching_lsa(points):
    distance_matrix = squareform(pdist(points))

    np.fill_diagonal(distance_matrix, np.inf)
    row_ind, col_ind = linear_sum_assignment(distance_matrix)

    matches = list(zip(row_ind, col_ind))
    return matches


def matching_kd(point_cloud):
    tree = KDTree(point_cloud)

    pairs = []
    for i, point in enumerate(point_cloud):
        dists, indexes = tree.query(point, k=2)
        nearest_neighbor_index = indexes[1]
        pairs.append((i, nearest_neighbor_index))

    return pairs


def greedy_matching(point_cloud):
    dist_matrix = squareform(pdist(point_cloud))
    pairs = []
    grouped_points = set()

    for i in range(point_cloud.shape[0]):
        if i not in grouped_points:  # Check if point is ungrouped
            for j in range(len(dist_matrix[i])):
                nearest_neighbor_idx = np.argmin(dist_matrix[i])
                if nearest_neighbor_idx != i and nearest_neighbor_idx not in grouped_points:
                    pairs.append((i, nearest_neighbor_idx))
                    grouped_points.add(i)
                    grouped_points.add(nearest_neighbor_idx)
                    break
                else:
                    dist_matrix[i][nearest_neighbor_idx] = np.inf

    return pairs


def sr_matching(points):
    d = squareform(pdist(points))
    closest = np.argsort(d, axis=1)
    preferences = {
        p[0]: p[1:] for p in closest
    }

    game = StableRoommates.create_from_dictionary(preferences)
    solution = game.solve()

    return [(m.name, n.name) for m, n in solution.items()]


if __name__ == "__main__":
    A = np.random.rand(400, 3)
    for i in range(20):
        for j in range(20):
            A[i * 20 + j] = [i, j, 1]

    shape = "grid_400"
    visualize = True
    # A = np.loadtxt(f'../assets/{shape}.txt', delimiter=',')
    G = 5
    k = int(2 ** np.ceil(np.log2(A.shape[0] / G)))
    assignments, centroids = k_means(A, k=k)

    P1 = mwm(centroids)
    C1 = tsp(centroids)
    # print(P1)
    groups = {}
    for i, a in enumerate(assignments):
        if a in groups:
            groups[a].append(i)
        else:
            groups[a] = [i]

    # edges in the cover cycle
    edge_list = list(nx.utils.pairwise(C1))
    gid = len(centroids)
    groups_2 = {2*gid-1: []}
    for e in edge_list:
        l_centroid = centroids[e[0]]
        r_centroid = centroids[e[1]]
        m_centroid = (l_centroid + r_centroid) / 2
        l_half = math.ceil(len(groups[e[0]]) / 2)
        l_points = A[groups[e[0]]]
        l_closest_idx = np.argsort(cdist([m_centroid], l_points), axis=1)[0]
        l_idx = l_closest_idx[:l_half]
        l_remain_idx = l_closest_idx[l_half:]
        m_idx = np.array(groups[e[0]])[l_idx].tolist()
        prev_idx = np.array(groups[e[0]])[l_remain_idx].tolist()
        if gid in groups_2:
            groups_2[gid] += m_idx
        else:
            groups_2[gid] = m_idx
        prev_gid = gid - 1
        if prev_gid < len(edge_list):
            prev_gid = len(edge_list) * 2 - 1
        groups_2[prev_gid] += prev_idx
        gid += 1

    assignments_2 = [0] * len(assignments)
    for gid, idxs in groups_2.items():
        for idx in idxs:
            assignments_2[idx] = gid

    asgn_1 = assignments.reshape(-1, 1)
    asgn_2 = np.array(assignments_2).reshape(-1, 1)
    np.savetxt(f"../assets/{shape}_overlapping.txt", np.hstack((A, asgn_1, asgn_2)), delimiter=',')

    if visualize:
        mpl.use('macosx')
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        for g in groups.values():
            xs = [A[p][0] for p in g]
            ys = [A[p][1] for p in g]
            zs = [A[p][2] for p in g]
            ax.scatter3D(xs, ys, zs, depthshade=False)

        for g in groups_2.values():
            xs = [A[p][0] for p in g]
            ys = [A[p][1] for p in g]
            zs = [A[p][2]+1 for p in g]
            ax.scatter3D(xs, ys, zs, depthshade=False)
        # cycle
        xs = [centroids[p][0] for p in C1]
        ys = [centroids[p][1] for p in C1]
        zs = [centroids[p][2]+2 for p in C1]
        ax.plot3D(xs, ys, zs, '-o')
        # matching
        # for i, j in P1:
        #     p1 = centroids[i]
        #     p2 = centroids[j]
        #     ax.plot3D([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], '-o')
        plt.show()
