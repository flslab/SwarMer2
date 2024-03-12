import json
import math
from copy import deepcopy

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
    hierarchical = True
    # A = np.random.rand(25, 3)
    # for i in range(5):
    #     for j in range(5):
    #         A[i * 5 + j] = [i, j, 1]

    shape = "chess"
    visualize = True

    if visualize:
        mpl.use('macosx')

    A = np.loadtxt(f'../assets/{shape}.txt', delimiter=',')
    G = 5
    k = int(2 ** np.ceil(np.log2(A.shape[0] / G)))
    assignments, centroids = k_means(A, k=k)

    groups = {}
    for i, a in enumerate(assignments):
        if a in groups:
            groups[a].append(i)
        else:
            groups[a] = [i]

    max_dist_1 = []
    for g in groups.values():
        max_dist_1.append(np.max(squareform(pdist(A[g]))))

    if hierarchical:
        h_groups = deepcopy(groups)
        h_centroids = centroids
        gid = k
        localizer = {}
        dists = []

        height = int(np.log2(k))
        while height > 0:
            pairs = mwm(h_centroids)
            offset = 2*(gid - k)
            new_centroids = [(h_centroids[i] + h_centroids[j]) / 2 for i, j in pairs]
            # print(pairs)
            for i, j in pairs:
                l_gid = i + offset
                r_gid = j + offset
                l_group = h_groups[l_gid]
                r_group = h_groups[r_gid]
                if height > 1:
                    h_groups[gid] = l_group + r_group
                xdist = cdist(A[l_group], A[r_group])
                am = np.argmin(xdist)
                dists.append(xdist[am // len(r_group), am % len(r_group)])
                l_idx = l_group[am // len(r_group)]
                r_idx = r_group[am % len(r_group)]
                if l_idx in localizer:
                    localizer[l_idx].append((r_idx, l_gid))
                else:
                    localizer[l_idx] = [(r_idx, l_gid)]
                if r_idx in localizer:
                    localizer[r_idx].append((l_idx, r_gid))
                else:
                    localizer[r_idx] = [(l_idx, r_gid)]
                gid += 1
            h_centroids = np.array(new_centroids)
            height -= 1

        # print(h_groups)
        # print(localizer)
        # print(dists)

        point_groups = []
        for i in range(len(A)):
            point_groups.append([])

        for gid, pts in h_groups.items():
            for p in pts:
                point_groups[p].append(gid)

        fig = plt.figure()
        ax = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)
        ax.hist(max_dist_1)
        ax2.hist(dists)
        plt.savefig(f"../assets/{shape}_hierarchical_hist.svg")

        np.savetxt(f"../assets/{shape}_hierarchical.txt", np.hstack((A, point_groups)), delimiter=',')

        with open(f"../assets/{shape}_hierarchical_localizer.json", "w") as f:
            json.dump(localizer, f)

    else:
        C1 = tsp(centroids)

        # edges in the cover cycle
        edge_list = list(nx.utils.pairwise(C1))
        gid = len(centroids)
        groups_2 = {2 * gid - 1: []}
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

        fig = plt.figure()
        ax = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        max_dist_2 = []

        for g in groups_2.values():
            max_dist_2.append(np.max(squareform(pdist(A[g]))))

        np.savetxt(f"../assets/{shape}_overlapping_max_dist.txt", np.vstack((max_dist_1, max_dist_2)), delimiter=',')

        ax.hist(max_dist_1)
        ax2.hist(max_dist_2)
        plt.savefig(f"../assets/{shape}_hist.svg")

        if visualize:
            fig = plt.figure(figsize=(15, 5))
            ax = fig.add_subplot(1, 3, 1, projection='3d')
            ax2 = fig.add_subplot(1, 3, 2, projection='3d')
            ax3 = fig.add_subplot(1, 3, 3, projection='3d')
            for g in groups.values():
                xs = [A[p][0] for p in g]
                ys = [A[p][1] for p in g]
                zs = [A[p][2] for p in g]
                ax.plot3D(xs, ys, zs, '-o')

            for g in groups_2.values():
                xs = [A[p][0] for p in g]
                ys = [A[p][1] for p in g]
                zs = [A[p][2] for p in g]
                ax2.plot3D(xs, ys, zs, '-o')
            # cycle
            xs = [centroids[p][0] for p in C1]
            ys = [centroids[p][1] for p in C1]
            zs = [centroids[p][2] for p in C1]
            ax3.plot3D(xs, ys, zs, '-o')
            # matching
            # for i, j in P1:
            #     p1 = centroids[i]
            #     p2 = centroids[j]
            #     ax.plot3D([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], '-o')
            plt.savefig(f"../assets/{shape}_groups.svg")
