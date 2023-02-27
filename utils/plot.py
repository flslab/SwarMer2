import matplotlib.pyplot as plt
import matplotlib as mpl


mpl.use('macosx')


def plot_point_cloud(ptcld):
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(ptcld[:, 0], ptcld[:, 1], ptcld[:, 2])
    plt.show()
