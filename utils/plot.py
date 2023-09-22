import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation
from multiprocessing import shared_memory
import numpy as np


def plot_point_cloud(ptcld):
    mpl.use('macosx')
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


if __name__ == '__main__':
    plot_point_cloud(np.random.uniform(0, 5, size=(30, 3)))
