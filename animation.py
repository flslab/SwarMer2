import itertools
import json
import math
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
import scipy
from matplotlib.animation import FuncAnimation, FFMpegWriter
import matplotlib as mpl

from utils.file import read_timelines
from worker.metrics import TimelineEvents



ticks_gap = 20

start_time = 0
duration = 100
fps = 30
frame_rate = 1/fps
total_points = 11888

# t30_d1_g0	t30_d1_g20	t30_d5_g0	t30_d5_g20	t600_d1_g0	t600_d1_g20	t600_d5_g0	t600_d5_g20
output_name = "testd"
input_path = f"/Users/hamed/Desktop/{output_name}/timeline.json"


def set_axis(ax, length, width, height, title=""):
    ax.axes.set_xlim3d(left=0, right=length)
    ax.axes.set_ylim3d(bottom=0, top=width)
    ax.axes.set_zlim3d(bottom=0, top=height)
    ax.set_aspect('equal')
    ax.grid(False)
    ax.set_xticks(range(0, length+1, ticks_gap))
    ax.set_yticks(range(0, width+1, ticks_gap))
    ax.set_zticks(range(0, height+1, ticks_gap))
    ax.set_title(title, y=.9)
    # ax.set_title(title)

def set_axis_2d(ax, length, width, title):
    ax.axes.set_xlim(0, length)
    ax.axes.set_ylim(0, width)
    ax.set_aspect('equal')
    ax.grid(False)
    ax.axis('off')
    ax.set_title(title)


def set_text(tx, t, hd):
    hs_f = "{:.3f}".format(round(hd, 3)) if hd > 0.001 else "{:.2e}".format(hd)
    tx.set(text=f"Elapsed time: {int(t)} (Second)\nHausdorff distance: {hs_f} (Display cell)")
    # tx.set(text=f"Elapsed time: {int(t)} seconds")


def draw_figure():
    px = 1/plt.rcParams['figure.dpi']
    fig_width = 1920*px
    fig_height = 1080*px
    fig = plt.figure(figsize=(fig_width, fig_height))
    spec = fig.add_gridspec(3, 6, left=0.04, right=0.96, top=0.92, bottom=0.08)
    ax = fig.add_subplot(spec[0:2, 0:3], projection='3d', proj_type='ortho')

    ax1 = fig.add_subplot(spec[0:2, 3:6], projection='3d', proj_type='ortho')

    ax2 = fig.add_subplot(spec[2, 0:2])
    ax3 = fig.add_subplot(spec[2, 2:4])
    ax4 = fig.add_subplot(spec[2, 4:6])

    # ax = fig.add_subplot(2, 1, 1, projection='3d', proj_type='ortho')
    # ax2 = fig.add_subplot(2, 1, 2, projection='3d', proj_type='ortho')
    tx = fig.text(0.05, 0.88, s="", fontsize=16)
    line1 = ax.scatter([], [], [])
    return fig, ax, ax1, ax2, ax3, ax4, tx


def read_point_cloud(path):
    data = read_timelines(path, "*")
    timeline = data['timeline']
    start_time = data['start_time']

    height = 0
    width = 0
    length = 0
    filtered_events = []
    gtl = []
    for e in timeline:
        if e[1] == TimelineEvents.FAIL:
            e[0] -= start_time
            filtered_events.append(e)
        elif e[1] == TimelineEvents.COORDINATE:
            e[0] -= start_time
            filtered_events.append(e)
            length = max(int(e[2][0]), length)
            width = max(int(e[2][1]), width)
            height = max(int(e[2][2]), height)
        elif e[1] == TimelineEvents.ILLUMINATE:
            gtl.append(e[2])
    length = math.ceil(length / ticks_gap) * ticks_gap
    width = math.ceil(width / ticks_gap) * ticks_gap
    height = math.ceil(height / ticks_gap) * ticks_gap

    return filtered_events, length, width, height, np.stack(gtl)


def init(ax, ax1, ax2, ax3, ax4):
    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax.zaxis.set_pane_color((0, 0, 0, 0.025))
    ax.view_init(elev=14, azim=-136, roll=0)
    ax1.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax1.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax1.zaxis.set_pane_color((0, 0, 0, 0.025))
    ax1.view_init(elev=14, azim=-136, roll=0)
    # ax2.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax2.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax2.zaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax2.view_init(elev=0, azim=0, roll=0)
    # ax3.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax3.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax3.zaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax3.view_init(elev=0, azim=90, roll=0)
    # ax4.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax4.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax4.zaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    # ax4.view_init(elev=90, azim=90, roll=0)
    # return line1,


def update(frame):
    t = start_time + frame * frame_rate
    while len(filtered_events):
        # print(t)
        event_time = filtered_events[0][0]
        if event_time <= t:
            event = filtered_events.pop(0)
            event_type = event[1]
            fls_id = event[-1]
            if event_type == TimelineEvents.COORDINATE:
                points[fls_id] = event[2]
            elif event_type == TimelineEvents.FAIL:
                points.pop(fls_id)
        else:
            t += frame_rate
            break
    coords = points.values()
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    ax.clear()
    ln = ax.scatter(xs, ys, zs, c='purple', s=2, alpha=1)
    set_axis(ax, length, width, height)

    ax1.clear()
    ln1 = ax1.scatter(gtl[:, 0], gtl[:, 1], gtl[:, 2], c='blue', s=2, alpha=1)
    set_axis(ax1, length, width, height, "Ground Truth")

    ax2.clear()
    if name.startswith('skateboard'):
        ln2 = ax2.scatter(ys, xs, c='purple', s=2, alpha=1)
        set_axis_2d(ax2, width, length, "Top")

    else:
        ln2 = ax2.scatter(xs, ys, c='purple', s=2, alpha=1)
        set_axis_2d(ax2, length, width, "Top")

    ax3.clear()
    ln3 = ax3.scatter(xs, zs, c='purple', s=2, alpha=1)
    set_axis_2d(ax3, length, height, "Front")

    ax4.clear()
    ln4 = ax4.scatter(ys, zs, c='purple', s=2, alpha=1)
    set_axis_2d(ax4, width, height, "Side")

    idx = find_nearest(time_stamps, t)
    hd = hds[idx]
    set_text(tx, t, hd)
    return [ln, ln1, ln2, ln3, ln4]


def show_last_frame(events, t=30):
    final_points = dict()
    for event in events:
        event_time = event[0]
        if event_time > t:
            break
        event_type = event[1]
        fls_id = event[-1]
        if event_type == TimelineEvents.ILLUMINATE or event_type == TimelineEvents.ILLUMINATE_STANDBY:
            final_points[fls_id] = event[2]
        else:
            final_points.pop(fls_id)

    coords = final_points.values()
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]

    return xs, ys, zs


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


if __name__ == '__main__':
    # mpl.use('macosx')
    #
    # filtered_events, length, width, height = read_point_cloud(input_path)
    # fig, ax, tx = draw_figure()
    # points = dict()
    # ani = FuncAnimation(
    #     fig, partial(update,),
    #     frames=30 * duration,
    #     init_func=partial(init, ax))
    # #
    # # plt.show()
    # writer = FFMpegWriter(fps=fps)
    # ani.save(f"results/{output_name}.mp4", writer=writer)
    # exit()
    # configs = [
    #     {
    #         "keys": ["K"],
    #         "values": ["0", "3"]
    #     },
    #     {
    #         "keys": ["D"],
    #         "values": ["5"]
    #     },
    #     {
    #         "keys": ["R"],
    #         "values": ["1", "inf"]
    #     },
    #     {
    #         "keys": ["T"],
    #         "values": ["30", "120"]
    #     }
    # ]
    #
    # props_values = [p["values"] for p in configs]
    # combinations = list(itertools.product(*props_values))
    # # print(combinations)
    #
    # exp_dir = "/Users/hamed/Desktop/chess_30_min"
    #
    # for c in combinations:
    #     exp_name = f"chess_K{c[0]}_D{c[1]}_R{c[2]}_T{c[3]}"
    #     print(exp_name)
    #     input_path = f"{exp_dir}/{exp_name}/timeline.json"
    #     filtered_events, length, width, height = read_point_cloud(input_path)
    #     fig, ax, _ = draw_figure()
    #     init(ax)
    #     xs, ys, zs = show_last_frame(filtered_events, t=1799)
    #     ax.scatter(xs, ys, zs, c='blue', s=2, alpha=1)
    #     set_axis(ax, length, width, height)
    #     # plt.show()
    #     plt.savefig(f"{exp_dir}/{exp_name}.png")
    #     plt.close()
    #     # break
    # exit()
    paths = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/hat/19_Sep_19_29_54",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",

        "/Users/hamed/Desktop/swarmer_fail/21_Sep_12_32_19",  # 0.001
        "/Users/hamed/Desktop/swarmer_fail/21_Sep_12_42_41",  # 0.0001

        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_21_51",  # 0.05
        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_58_07",  # 0.45
        "/Users/hamed/Desktop/swarmer_st/21_Sep_02_32_31",  # 1.5

        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_54_42",  # skateboard 0.01
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_20_09_23",  # skateboard 0.1
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_47_01",  # skateboard 0.001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_42_34",  # skateboard 0.0001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_23_39",  # skateboard lambda 0.05
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_26_58",  # skateboard lambda 1.5
    ]

    names = ['dragon', 'hat', 'skateboard', 'chess_0.1', 'chess_0.01', 'chess_0.05', 'chess_0.45', 'chess_1.50',
             'skateboard_0.01', 'skateboard_0.1',
             'skateboard_0.001', 'skateboard_0.0001', 'skateboard_lambda_0.05', 'skateboard_lambda_1.5']
    for path, name in zip(paths[10:], names[10:]):

        filtered_events, length, width, height, _ = read_point_cloud(path)
        mat = scipy.io.loadmat(f'/Users/hamed/Documents/Holodeck/SwarMerPy/assets/skateboard.mat')
        gtl = mat['p']

        with open(f"{path}/charts.json") as f:
            chart_data = json.load(f)
            time_stamps = chart_data[0]
            hds = chart_data[1]
            while True:
                if hds[0] == -1:
                    hds.pop(0)
                    time_stamps.pop(0)
                else:
                    break
        fig, ax, ax1, ax2, ax3, ax4, tx = draw_figure()
        points = dict()
        ani = FuncAnimation(
            fig, partial(update,),
            frames=30 * duration,
            init_func=partial(init, ax, ax1, ax2, ax3, ax4))
        #
        # plt.show()
        writer = FFMpegWriter(fps=fps)
        ani.save(f"/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/{name}_all_views.mp4", writer=writer)
