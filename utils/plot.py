import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.animation as animation


mpl.use('macosx')


def plot_point_cloud(ptcld, shared_el):
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    graph = ax.scatter(ptcld[:, 0], ptcld[:, 1], ptcld[:, 2])
    # ani = animation.FuncAnimation(fig, update, fargs=[shared_el, graph], frames=100, interval=50, blit=True)
    plt.show()


def update(num, shared_el, graph):
    graph._offsets3d = (shared_el[:, 0], shared_el[:, 1], shared_el[:, 2])
    return graph,



