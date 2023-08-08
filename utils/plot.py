import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation
from multiprocessing import shared_memory
import numpy as np
from matplotlib import rcParams
rcParams['font.family'] = 'Times New Roman'

# mpl.use('macosx')


def plot_point_cloud(ptcld, shm_name):
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    graph = ax.scatter(ptcld[:, 0], ptcld[:, 1], ptcld[:, 2])
    # count = ptcld.shape[0]
    # ani = animation.FuncAnimation(fig, update, fargs=[graph, shm_name, count], frames=100, interval=50, blit=True)
    plt.show()


def update(num, graph, shm_name, count):
    shared_mem = shared_memory.SharedMemory(name=shm_name)
    shared_array = np.ndarray((count, 3), dtype=np.float64, buffer=shared_mem.buf)
    # print(graph._offsets3d)
    graph._offsets3d = (shared_array[:, 0], shared_array[:, 1], shared_array[:, 2])
    return graph,


def boxplot():
    fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(6, 4))

    # Duration CANF G=10
    # all_data = [[946.7285602, 1394.370517, 2736.752941, 758.0871108, 1763.43048, 1561.556781, 1754.412206, 1571.212268, 712.2744441, 2680.026877],
    #             [2719.029322, 3354.961837, 3602.834491, 2835.905622, 4229.982035, 8047.31485, 2630.513689, 3015.31166, 3005.62969, 4246.568515],
    #             [161.7461169, 288.7125499, 314.2994595, 211.4374239, 234.6104085, 181.6258986, 213.6726103, 224.6476183, 130.7561095, 154.7783368],
    #             [7538.208493, 6133.081297, 8040.665102, 6566.946958, 12620.58903, 6061.415786, 8686.28949, 7082.164474, 10714.34987, 6828.353063]]

    # Avg Dist CANF G=10
    all_data = [[8.473661671, 8.65789498, 8.473495652, 8.454763316, 9.059855066, 9.373376612, 9.134603579, 8.559328861, 8.476735389, 8.554042898],
                [4.597325949, 5.191147703, 5.001052744, 4.652282735, 5.015244406, 4.268838355, 3.920798704, 4.179868799, 3.84371417, 4.554568034],
                [3.164096215, 2.841743255, 2.882807451, 2.833583283, 3.190280822, 2.82194163, 3.087084859, 3.076004453, 3.208613985, 2.892591629],
                [2.040837016, 2.093522472, 2.042492589, 2.065352536, 2.053521794, 2.085753322, 2.082353737, 2.063859078, 2.144676911, 2.11702264]]

    labels = ['Chess piece\n454 points', 'Dragon\n760 points', 'Skateboard\n1727 points', 'Race car\n11894 points']

    # plot violin plot
    # axs[0].violinplot(all_data,
    #                   showmeans=False,
    #                   showmedians=True)
    # axs[0].set_title('Execution time (Second)')
    # axs[0].set_yscale('log')

    # plot box plot
    axs.boxplot(all_data, showmeans=True)
    # axs.set_title('Execution time (Second)', loc='left')
    axs.set_title('Average distance (Display cell)', loc='left')
    # axs.set_yscale('log')

    # adding horizontal grid lines
    # for ax in axs:
    axs.yaxis.grid(True)
    axs.set_xticks([y + 1 for y in range(len(all_data))],
                  labels=labels)
    # axs.set_yticks([100, 1000, 10000], ['100', '1,000', '10,000'])
    axs.spines['top'].set_color('white')
    axs.spines['right'].set_color('white')
    print(np.median(all_data, axis=1).tolist())
    # ax.set_xlabel('Four separate samples')
    # ax.set_ylabel('Observed values')

    # plt.show()
    plt.savefig('/Users/hamed/Desktop/avg_dist_shapes_g10.png')


if __name__ == '__main__':
    boxplot()
