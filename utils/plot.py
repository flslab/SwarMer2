import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation
from multiprocessing import shared_memory
import numpy as np


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

    # Fixing random state for reproducibility
    np.random.seed(19680801)

    # generate some random test data
    all_data = [[946.7285602, 1394.370517, 2736.752941, 758.0871108, 1763.43048, 1561.556781, 1754.412206, 1571.212268, 712.2744441, 2680.026877],
                [2719.029322, 3354.961837, 3602.834491, 2835.905622, 4229.982035, 8047.31485, 2630.513689, 3015.31166, 3005.62969, 4246.568515],
                [161.7461169, 288.7125499, 314.2994595, 211.4374239, 234.6104085, 181.6258986, 213.6726103, 224.6476183, 130.7561095, 154.7783368],
                [7538.208493, 6133.081297, 8040.665102, 6566.946958, 12620.58903, 6061.415786, 8686.28949, 7082.164474, 10714.34987, 6828.353063]]
    labels = ['Chess piece', 'Dragon', 'Skateboard', 'Race car']

    # plot violin plot
    # axs[0].violinplot(all_data,
    #                   showmeans=False,
    #                   showmedians=True)
    # axs[0].set_title('Execution time (Second)')
    # axs[0].set_yscale('log')

    # plot box plot
    axs.boxplot(all_data, showmeans=True)
    axs.set_title('Execution time (Second)')
    axs.set_yscale('log')

    # adding horizontal grid lines
    # for ax in axs:
    axs.yaxis.grid(True)
    axs.set_xticks([y + 1 for y in range(len(all_data))],
                  labels=labels)
    axs.set_yticks([100, 1000, 10000])
    print(np.median(all_data, axis=1).tolist())
    # ax.set_xlabel('Four separate samples')
    # ax.set_ylabel('Observed values')

    plt.show()


if __name__ == '__main__':
    boxplot()
