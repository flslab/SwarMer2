import heapq
import math
import os
import json
import csv
import subprocess

import matplotlib as mpl

import numpy as np
from matplotlib import pyplot as plt, ticker

from config import Config
import pandas as pd
import glob

from utils import hausdorff_distance
from utils.chamfer import chamfer_distance_optimized
from worker.metrics import TimelineEvents
import pandas as pd


def write_json(fid, results, directory):
    with open(os.path.join(directory, 'json', f"{fid:05}.json"), "w") as f:
        json.dump(results, f)


def create_csv_from_json(directory):
    if not os.path.exists(directory):
        return

    headers_set = set()
    rows = []

    json_dir = os.path.join(directory, 'json')
    filenames = os.listdir(json_dir)
    filenames.sort()

    for filename in filenames:
        if filename.endswith('.json'):
            with open(os.path.join(json_dir, filename)) as f:
                try:
                    data = json.load(f)
                    headers_set = headers_set.union(set(list(data.keys())))
                except json.decoder.JSONDecodeError:
                    print(filename)

    headers = list(headers_set)
    headers.sort()
    rows.append(['fid'] + headers)

    for filename in filenames:
        if filename.endswith('.json'):
            with open(os.path.join(json_dir, filename)) as f:
                try:
                    data = json.load(f)
                    fid = filename.split('.')[0]
                    row = [fid] + [data[h] if h in data else 0 for h in headers]
                    rows.append(row)
                except json.decoder.JSONDecodeError:
                    print(filename)

    with open(os.path.join(directory, 'metrics.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_hds_time(hds, directory, nid):
    if not os.path.exists(directory):
        return

    headers = ['timestamp(s)', 'relative_time(s)', 'hd']
    rows = [headers]

    for i in range(len(hds)):
        row = [hds[i][0], hds[i][0] - hds[0][0], hds[i][1]]
        rows.append(row)

    with open(os.path.join(directory, f'hd-n{nid}.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_hds_round(hds, rounds, directory, nid):
    if not os.path.exists(directory):
        return

    headers = ['round', 'time(s)', 'hd']
    rows = [headers]

    for i in range(len(hds)):
        row = [i+1, rounds[i+1] - rounds[0], hds[i][1]]
        rows.append(row)

    with open(os.path.join(directory, f'hd-n{nid}.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_swarms(swarms, rounds, directory, nid):
    headers = [
        'timestamp(s)',
        'relative times(s)',
        'num_swarms',
        'average_swarm_size',
        'largest_swarm',
        'smallest_swarm',
    ]

    rows = [headers]

    for i in range(len(swarms)):
        t = swarms[i][0] - rounds[0]
        num_swarms = len(swarms[i][1])
        sizes = swarms[i][1].values()

        row = [swarms[i][0], t, num_swarms, sum(sizes)/num_swarms, max(sizes), min(sizes)]
        rows.append(row)

    with open(os.path.join(directory, f'swarms-n{nid}.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_configs(directory):
    headers = ['config', 'value']
    rows = [headers]

    for k, v in vars(Config).items():
        if not k.startswith('__'):
            rows.append([k, v])

    with open(os.path.join(directory, 'config.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def combine_csvs(directory, xslx_dir):
    from datetime import datetime
    current_datetime = datetime.now()
    current_date_time = current_datetime.strftime("%H:%M:%S_%m:%d:%Y")

    csv_files = glob.glob(f"{directory}/*.csv")

    with pd.ExcelWriter(os.path.join(xslx_dir, f'{Config.SHAPE}_{current_date_time}.xlsx')) as writer:
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            sheet_name = csv_file.split('/')[-1][:-4]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    # shutil.rmtree(os.path.join(directory))


def read_timelines(path, fid='*'):
    json_files = glob.glob(f"{path}/timeline_{fid}.json")
    timelines = []

    for jf in json_files:
        with open(jf) as f:
            timelines.append(json.load(f))

    start_time = min([tl[0][0] for tl in timelines if len(tl)])

    merged_timeline = merge_timelines(timelines)

    return {
        "start_time": start_time,
        "timeline": merged_timeline,
    }


def gen_sliding_window_chart_data(timeline, start_time, value_fn, sw=0.01):  # 0.01
    xs = [0]
    hd = [-1]
    cd = [-1]
    current_points = {}
    current_swarms = {}
    gtl_points = {}
    total_failures = 0

    # for event in timeline:
    #     e_type = event[1]
    #     t = event[0] - start_time
    #     if t > 200:
    #         break
    #     if e_type == TimelineEvents.FAIL:
    #         total_failures += 1
    # print(total_failures)
    # return
    i = 0
    while i < len(timeline):
        event = timeline[i]
        e_type = event[1]
        e_fid = event[-1]
        t = event[0] - start_time
        # if t < 15.65:
        #     timeline.pop(0)
        #     continue
        # print(t)
        if t > 300:
            break
        if xs[-1] <= t < xs[-1] + sw:
            if e_type == TimelineEvents.COORDINATE:
                current_points[e_fid] = event[2]
            elif e_type == TimelineEvents.FAIL:
                current_points.pop(e_fid)
                gtl_points.pop(e_fid)
            elif e_type == TimelineEvents.ILLUMINATE:
                gtl_points[e_fid] = event[2]
            i += 1
        else:
            # swarm_ys[-1] = len(set(current_swarms.values()))
            # print(len(current_swarms))
            if len(current_points) > 1 and len(gtl_points):
                a = np.stack(list(current_points.values()))
                b = np.stack(list(gtl_points.values()))
                hd[-1] = hausdorff_distance(a, b)
                cd[-1] = chamfer_distance_optimized(a, b)
                # ys[-1] = 1
            xs.append(xs[-1] + sw)
            hd.append(-1)
            cd.append(-1)

    return xs, hd, cd


def merge_timelines(timelines):
    lists = timelines
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heap.append((lst[0][0], i, 0))
    heapq.heapify(heap)

    merged = []
    while heap:
        val, lst_idx, elem_idx = heapq.heappop(heap)
        merged.append(lists[lst_idx][elem_idx] + [lst_idx])
        if elem_idx + 1 < len(lists[lst_idx]):
            next_elem = lists[lst_idx][elem_idx + 1][0]
            heapq.heappush(heap, (next_elem, lst_idx, elem_idx + 1))
    return merged


def gen_sw_charts(path, fid, name, read_from_file=True):
    # fig = plt.figure(figsize=(5, 2.5))
    # ax = fig.add_subplot()

    if read_from_file:
        with open(f"{path}/charts.json") as f:
            chart_data = json.load(f)
            # r_xs = chart_data[0]
            # t_idx = next(i for i, v in enumerate(r_xs) if v > 300)
            t = chart_data['t']
            hd = chart_data['hd']
            cd = chart_data['cd']
    else:
        data = read_timelines(path, fid)
        t, hd, cd = gen_sliding_window_chart_data(data['timeline'], data['start_time'], lambda x: x[2])
        # gen_sliding_window_chart_data(data['timeline'], data['start_time'], lambda x: x[2])
        # return
        with open(f"{path}/charts.json", "w") as f:
            json.dump({'t': t, 'hd': hd, 'cd': cd}, f)

    # s_xs, s_ys = gen_sliding_window_chart_data(data['sent_bytes'], data['start_time'], lambda x: x[2])
    # h_xs, h_ys = gen_sliding_window_chart_data(data['heuristic'], data['start_time'], lambda x: 1)
    # ax.step(r_xs, s_ys, where='post', label="Number of swarms", color="tab:purple")
    # ax.step(r_xs, l_ys, where='post', label="Number of expired leases")
    while True:
        if hd[0] == -1:
            hd.pop(0)
            cd.pop(0)
            t.pop(0)
        else:
            break

    # ax.step(s_xs, s_ys, where='post', label="Sent bytes", color="black")
    # ax.step(h_xs, h_ys, where='post', label="Heuristic invoked")
    # ax.legend()
    # ax.legend()
    # ax.set_ylabel('Number of swarms', loc='top', rotation=0, labelpad=-90)
    # ax.set_xlabel('Time (Second)', loc='right')
    # ax.spines['top'].set_color('white')
    # ax.spines['right'].set_color('white')
    # plt.xlim([0, 60])
    # plt.show()
    # plt.savefig(f'{path}/{name}_{fid}.png', dpi=300)

    fig, ax = plt.subplots(figsize=(5, 2.5), layout="constrained")
    ax.step(t, hd, where='post', label="Hausdorff distance", color="tab:blue")
    ax.step(t, cd, where='post', label="Chamfer distance", color="tab:orange")
    ax.legend()
    # ax.set_ylabel(f'HD, {name}', loc='top', rotation=0, labelpad=-133)
    ax.set_title(f'HD, CD {name}', fontsize=10, loc="left")
    ax.set_xlabel('Time (Second)', loc='right')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    # y_locator = ticker.FixedLocator(list(range(0, int(max_y), 10)) + [math.floor(max_y)])

    ax.set_xlim(0, 60)
    # plt.tight_layout()
    # plt.ylim([10e-13, 10e3])
    plt.yscale('log')
    plt.savefig(f'{path}/{name}_{fid}h.png', dpi=300)


def gen_util_chart(path):
    fig = plt.figure()
    ax = fig.add_subplot()

    with open(f"{path}/utilization.json") as f:
        chart_data = json.load(f)
        t = chart_data[0]
        ys = chart_data[1]

    for i in range(1):
        ax.step(t, [y[i] for y in ys], where='post', label=f"server-{i+1}")

    ax.legend()

    # plt.show()
    plt.savefig(f'{path}/cpu_utilization.png', dpi=300)


def gen_shape_comp_hd(paths, labels, poses, colors, dest):
    lss = ['solid', 'dashdot', 'dashed', 'dotted']
    lss += lss
    fig = plt.figure(figsize=(5, 2.4))
    ax = fig.add_subplot()
    # ax2 = fig.add_axes([0.57, 0.48, 0.38, 0.42])
    ax2 = fig.add_axes([0.57, 0.58, 0.38, 0.32])
    max_y = 80
    t_e2s = []
    for path, label, pos, color, ls in zip(paths, labels, poses, colors, lss):
        with open(f"{path}/charts.json") as f:
            chart_data = json.load(f)
            t = chart_data[0]
            ys = chart_data[1]
            t_100 = 0
            t_e2 = 0
            while True:
                t_100 += 1
                if t[t_100] >= 100:
                    break

            while True:
                if ys[0] == -1:
                    ys.pop(0)
                    t.pop(0)
                else:
                    break
            while True:
                t_e2 += 1
                if ys[t_e2] < 1e-2:
                    break
            ax.plot(t, ys, linestyle=ls, linewidth=1.4, color=color, label=label)
            ax2.plot(t, ys, linestyle=ls, linewidth=1.4, color=color, label=label)
            max_y = max(max_y, max(ys[:t_100]))
            if ys[t_e2] < 1e-2 and ys[t_e2] != -1:
                print(ys[t_e2])
                t_e2s.append(t[t_e2])
            else:
                t_e2s.append(-1)
            # plt.text(pos[0], pos[1], label, color=color, fontweight='bold')

    ax.set_ylabel('Hausdorff distance (Display cell)', loc='top', rotation=0, labelpad=-133)
    ax.set_xlabel('Time (Second)', loc='right')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    ax.set_ylim(0, max_y + 10)
    # y_locator = ticker.FixedLocator(list(range(0, int(max_y), 10)) + [math.floor(max_y)])
    y_locator = ticker.FixedLocator(list(range(0, int(max_y), 10)))
    ax.yaxis.set_major_locator(y_locator)
    ax.set_xlim(0, 200)
    plt.tight_layout()


    # plt.yscale('log')
    # plt.ylim([1e-3, 149])
    # plt.xlim([0, 100])
    # y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    # ax.yaxis.set_major_locator(y_locator)
    # y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    # ax.yaxis.set_major_formatter(y_formatter)

    # ax2.legend()
    ax2.set_ylabel('Log scale', loc='top', rotation=0, labelpad=-50)
    # ax2.set_xlabel('Time (Second)', loc='right')
    ax2.spines['top'].set_color('white')
    ax2.spines['right'].set_color('white')
    # plt.tight_layout()
    ax2.set_yscale('log')
    ax2.set_ylim([1e-3, 200])
    ax2.set_xlim([0, 100])
    y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    # y_locator = ticker.FixedLocator([1e-2, 1e-1, 1, 10, 100])
    ax2.yaxis.set_major_locator(y_locator)
    y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    # y_formatter = ticker.FixedFormatter(["0.01", "0.1", "1", "10", "100"])
    ax2.yaxis.set_major_formatter(y_formatter)
    ax2.yaxis.grid(True, which='minor')
    # ax2.legend(loc="upper right", fontsize="small")
    ax.legend(loc="upper left", fontsize="small", bbox_to_anchor=(0.05, .88))
    # ax.legend(loc="upper left", fontsize="small", bbox_to_anchor=(0.08, .8))

    plt.savefig(dest, dpi=300)
    return t_e2s


def gen_shape_comp_hd_2(paths, labels, colors, dest, ylim=100):
    lss = ['solid', 'dashdot', 'dashed', 'dotted']
    fig = plt.figure(figsize=(5, 2.4))
    ax = fig.add_subplot()
    # ax2 = fig.add_axes([0.57, 0.48, 0.38, 0.42])
    for path, label, color in zip(paths, labels, colors):
        with open(f"{path}/charts.json") as f:
            chart_data = json.load(f)
            t = chart_data[0]
            ys = chart_data[1]
            while True:
                if ys[0] == -1:
                    ys.pop(0)
                    t.pop(0)
                else:
                    break
            ax.plot(t, ys, linewidth=1.4, color=color, label=label)
            # ax2.plot(t, ys, linewidth=1.4, color=color, label=label)
            # plt.text(pos[0], pos[1], label, color=color, fontweight='bold')

    ax.set_ylabel('Hausdorff distance (Display cell)', loc='top', rotation=0, labelpad=-133)
    ax.set_xlabel('Time (Second)', loc='right')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    # ax.set_yscale('log')
    # ax.set_ylim([1e-3, 200])
    ax.set_xlim([0, ylim])
    plt.tight_layout()
    y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    ax.yaxis.set_major_locator(y_locator)
    y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    ax.yaxis.set_major_formatter(y_formatter)


    # plt.yscale('log')
    # plt.ylim([1e-3, 149])
    # plt.xlim([0, 100])
    # y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    # ax.yaxis.set_major_locator(y_locator)
    # y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    # ax.yaxis.set_major_formatter(y_formatter)

    # ax2.legend()
    # ax2.set_ylabel('Log scale', loc='top', rotation=0, labelpad=-50)
    # # ax2.set_xlabel('Time (Second)', loc='right')
    # ax2.spines['top'].set_color('white')
    # ax2.spines['right'].set_color('white')
    # # plt.tight_layout()
    # ax2.set_yscale('log')
    # ax2.set_ylim([1e-3, 200])
    # ax2.set_xlim([0, 50])
    # y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    # ax2.yaxis.set_major_locator(y_locator)
    # y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    # ax2.yaxis.set_major_formatter(y_formatter)
    # ax2.yaxis.grid(True, which='minor')
    # ax2.legend(loc="upper right", fontsize="small")
    ax.legend(loc="upper right", fontsize="small")

    plt.savefig(dest, dpi=300)


def find_time_by_hd(path):
    print(path)
    with open(f"{path}/charts.json") as f:
        chart_data = json.load(f)
        t = chart_data[0]
        ys = chart_data[1]

    for i, y in enumerate(ys):
        if 0.9 < y <= 10:
            print(i, t[i], y)
        elif 0.09 < y <= 0.15:
            print(i, t[i], y)
        elif 0.009 < y <= 0.015:
            print(i, t[i], y)
        elif 0.0009 < y <= 0.0019:
            print(i, t[i], y)


def find_time_to_reach_hd(path, hd=1e-2):
    with open(f"{path}/charts.json") as f:
        chart_data = json.load(f)
        t = chart_data[0]
        ys = chart_data[1]

    t_i = 0
    while True:
        t_i += 1
        if t_i >= len(ys):
            break
        if ys[t_i] != -1 and ys[t_i] < hd:
            return t[t_i], ys[t_i]

    return -1, -1


def gen_shape_fig_by_time(path, target, sw=0.01):
    data = read_timelines(path, "*")
    timeline = data['timeline']
    start_time = data['start_time']
    xs = [0]
    ys = [-1]
    current_points = {}
    gtl_points = {}

    i = 0
    while i < len(timeline):
        event = timeline[i]
        e_type = event[1]
        e_fid = event[-1]
        t = event[0] - start_time
        # if t < 15.65:
        #     timeline.pop(0)
        #     continue
        # print(t)
        if len(xs) == target - 1:
            break
        if xs[-1] <= t < xs[-1] + sw:
            if e_type == TimelineEvents.COORDINATE:
                current_points[e_fid] = event[2]
            elif e_type == TimelineEvents.FAIL:
                current_points.pop(e_fid)
                gtl_points.pop(e_fid)
            elif e_type == TimelineEvents.ILLUMINATE:
                gtl_points[e_fid] = event[2]
            # elif e_type == TimelineEvents.SWARM:
            #     current_swarms[e_fid] = event[2]
            # elif e_type == TimelineEvents.LEASE_EXP:
            #     lease_exp_ys[-1] += 1
            i += 1
        else:
            pass
            # swarm_ys[-1] = len(set(current_swarms.values()))
            # print(len(current_swarms))
            # if len(current_points) > 1 and len(gtl_points):
            #     ys[-1] = hausdorff_distance(np.stack(list(current_points.values())),
            #                                 np.stack(list(gtl_points.values())))
                # ys[-1] = 1
            xs.append(xs[-1] + sw)
            # ys.append(-1)
            # swarm_ys.append(-1)
            # lease_exp_ys.append(0)
    # print(hausdorff_distance(np.stack(list(current_points.values())), np.stack(list(gtl_points.values()))))
    ptcld = np.stack(list(current_points.values()))
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(ptcld[:, 0], ptcld[:, 1], ptcld[:, 2])
    # plt.show()
    return ptcld, round(hausdorff_distance(ptcld, np.stack(list(gtl_points.values()))), 4)


def quad(ptlds, hds, dest):
    # pylab.rcParams['xtick.major.pad'] = '1'
    # pylab.rcParams['ytick.major.pad'] = '1'
    # pylab.rcParams['ztick.major.pad'] = '8'
    # title_offset = [-.25, -.25, -.02, -.02]
    shapes_labels = [f'HD={hd}' for hd in hds]
    fig = plt.figure(figsize=(5, 4), layout='constrained')

    for i, ptcld in enumerate(ptlds):
        # mat = scipy.io.loadmat(f'../assets/{shapes[i]}.mat')
        # ptcld = mat['p']

        ticks_gap = 10
        length = math.ceil(np.max(ptcld[:, 0]) / ticks_gap) * ticks_gap
        width = math.ceil(np.max(ptcld[:, 1]) / ticks_gap) * ticks_gap
        height = math.ceil(np.max(ptcld[:, 2]) / ticks_gap) * ticks_gap
        ax = fig.add_subplot(2, 2, i + 1, projection='3d', proj_type='ortho')
        ax.scatter(ptcld[:, 0], ptcld[:, 1], ptcld[:, 2], c='blue', s=1, alpha=1, edgecolors='none')
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
        ax.zaxis.set_pane_color((0, 0, 0, 0.025))
        # ax.view_init(elev=16, azim=137, roll=0)
        ax.view_init(elev=16, azim=-120, roll=0)
        ax.axes.set_xlim3d(left=1, right=length)
        ax.axes.set_ylim3d(bottom=1, top=width)
        ax.axes.set_zlim3d(bottom=1, top=height)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(length))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(width))
        ax.zaxis.set_major_locator(ticker.MultipleLocator(height))
        ax.set_aspect('equal')
        ax.grid(False)
        # ax.set_xticks(range(0, length + 1, length))
        # ax.set_yticks(range(0, width + 1, width))
        # ax.set_zticks(range(0, height + 1, height))
        ax.tick_params(pad=-2)
        ax.tick_params(axis='x', pad=-6)
        ax.tick_params(axis='y', pad=-6)
        ax.set_title(shapes_labels[i], y=-.01)

    plt.margins(x=0, y=0)
    # plt.tight_layout()
    # plt.show()
    plt.savefig(dest, dpi=300)


def get_table_vals(st_path):
    df = pd.read_csv(f"{st_path}/metrics.csv")
    return {
        # "Avg Xmit Bytes": df['A4_bytes_sent'].mean(),
        "Total Xmit bytes": format(df['A4_bytes_sent'].sum(), ','),
        # "Avg Xmit Bytes": df['A4_bytes_sent'].mean(),
        "Total # Localizations": format(df['A3_num_localize'].sum(), ','),
        "Total # Anchors": format(df['A3_num_anchor'].sum(), ','),
        "Total # times swarms thawed": format(df['C0_num_received_THAW_SWARM'].sum(), ','),
        "Total # times leases expired": f"{df['A2_num_expired_leases'].sum()} ({round(df['A2_num_expired_leases'].sum() / df['A2_num_granted_leases'].sum() * 100, 2)}\%)",
        "Avg distance traveled": round(df['A0_total_distance'].mean(), 2),
    }



if __name__ == '__main__':
    mpl.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams.update({'font.size': 10})

    path = "/Users/hamed/Documents/Holodeck/SwarMer2/results/grid_36_spanning_2/Rgrid_36_spanning_2/grid_36_spanning_2_Rgrid_36_spanning_2_D5_X0.0_MTrue_1711820026"
    gen_sw_charts(path, "*", "_", False)
    exit()

    paths = [
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_17_38_36",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_18_30_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_18_52_48",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/25_Aug_19_25_07",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692899950",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692902499",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692903856",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692992188",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/1694542758",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node/results/chess/16_Sep_22_40_46",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node/results/chess/16_Sep_23_03_14",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node/results/chess/16_Sep_23_09_43",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node/results/chess/16_Sep_23_23_26"
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node-3/results/chess/18_Sep_23_41_16",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-5-96-node-4/results/dragon/19_Sep_16_26_59",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_12_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_14_58",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_18_27",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_21_00",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_24_02",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_26_34",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_31_50",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_34_32",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_37_35",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_40_23",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_43_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_18_49",  # 0.001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_41_43",  # 0.0001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_24_39",  # 0.001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_30_13",  # 0.0001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_20_09_23",  # skateboard 0.1
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_54_42",  # skateboard 0.01
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_47_01",  # skateboard 0.001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_42_34",  # skateboard 0.0001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_23_39",  # skateboard lambda 0.05
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_26_58",  # skateboard lambda 1.5
    ]
    comp_labels = [
        # "Dragon, 760 FLSs",
        # "Hat, 1562 FLSs",
        # "Skateboard, 1727 FLSs",
        "Dragon",
        "Hat",
        "Skateboard",
    ]
    comp_poses = [
        (7, 0.05),
        (30, 0.025),
        (50, 0.05)
    ]
    comp_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/hat/19_Sep_19_29_54",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",
    ]

    loss_r_labels = [
        # "Dragon, 760 FLSs",
        # "Hat, 1562 FLSs",
        # "Skateboard, 1727 FLSs",
        "No packet loss",
        "0.1% packet loss",
        "1% packet loss",
        "10% packet loss",
    ]
    loss_r_poses = [
        (43, 0.2),
        (36, 0.035),
        (70, 0.05),
        (5, 0.1),
    ]
    loss_r_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_59_40",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_02_20",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_14_23",
        #
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/hat/19_Sep_19_29_54",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_31_50",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_34_32",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_37_35",

        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_12_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_18_27",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_21_00",
    ]

    loss_labels = [
        # "Dragon, 760 FLSs",
        # "Hat, 1562 FLSs",
        # "Skateboard, 1727 FLSs",
        "No packet loss",
        "Asymmetric, receiver",
        "Symmetric",
        "Asymmetric, transmitter",
    ]
    loss_poses = [
        (28, 1.1),
        (8, 0.003),
        (30, 0.25),
        (55, 0.06),
    ]
    loss_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_14_23",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_09_00",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_11_38",

        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_37_35",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_40_23",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_43_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/hat/19_Sep_19_29_54",

        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_21_00",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_24_02",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_26_34",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",

    ]

    fail_path = [
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_18_49",
        # # 0.001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_41_43",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_24_39",
        # # 0.001
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_30_13",
        # # 0.0001
        "/Users/hamed/Desktop/swarmer_fail/21_Sep_12_32_19",  # 0.001
        "/Users/hamed/Desktop/swarmer_fail/21_Sep_12_42_41"  # 0.0001
    ]

    st_path = [
        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_21_51",  # 0.05
        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_35_10",  # 0.20
        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_44_43",  # 0.30
        "/Users/hamed/Desktop/swarmer_st/21_Sep_00_58_07",  # 0.45
        "/Users/hamed/Desktop/swarmer_st/21_Sep_01_20_29",  # 0.70
        "/Users/hamed/Desktop/swarmer_st/21_Sep_01_47_21",  # 0.1
    ]

    st_labels = [
        "50 ms",
        "200 ms",
        "300 ms",
        "450 ms",
        "700 ms",
        "1000 ms",
    ]


    sk_st_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_23_39",  # skateboard lambda 0.05
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_26_58",  # skateboard lambda 1.5
    ]

    sk_st_labels = [
        "50 ms",
        # "500 ms",
        "1500 ms",
    ]

    fail_labels = [
        "0.1% failure, 33 failures",
        "0.01% failure, 1 failure",
    ]

    sk_fail_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_20_09_23",  # skateboard 0.1
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_54_42",  # skateboard 0.01
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_47_01",  # skateboard 0.001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-22-400-node-failure/results/skateboard/22_Sep_18_42_34",  # skateboard 0.0001
    ]

    sk_fail_labels = [
        "10% failure, 17752 failures",
        "1% failure, 1765 failures",
        "0.1% failure, 219 failures",
        "0.01% failure, 12 failures",
    ]

    chess_ss_err_plain_path_m1 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM1_NS1/chess_X0.01_09_Nov_11_19_37",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM1_NS10/chess_X0.01_09_Nov_11_32_34",  # sampling
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS1/08_Nov_13_38_46",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS1/08_Nov_14_11_09",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS1/08_Nov_14_43_31",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS1/08_Nov_15_15_57",
    ]

    chess_ss_err_plain_path_m2_x10 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM2_NS1/chess_X0.01_P0.99_09_Nov_11_22_54",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM2_NS10/chess_X0.01_P0.99_09_Nov_11_35_46",  # sampling
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS1/08_Nov_13_38_46",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_15_48_18",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_16_20_36",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_16_53_02",
    ]

    chess_ss_err_plain_path_m2_x50 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS1/08_Nov_13_38_46",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_17_25_24",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_17_57_56",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_18_30_19",
    ]

    chess_ss_err_plain_path_m2_x90 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS1/08_Nov_13_38_46",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_19_02_45",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_19_35_18",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS1/08_Nov_20_07_51",
    ]

    chess_ss_err_plain_path_m3 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM3_NS1/chess_P0.99_09_Nov_11_26_09",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM3_NS10/chess_P0.99_09_Nov_11_38_59",  # sampling
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS1/08_Nov_13_38_46",  # no error
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS1/08_Nov_20_40_25",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS1/08_Nov_21_45_22",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS1/08_Nov_21_12_53",
    ]

    chess_ss_err_plain_path_m1_sampling = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS10/08_Nov_22_21_13",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS10/08_Nov_22_50_16",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS10/08_Nov_23_22_37",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM1_NS10/08_Nov_23_55_03",
    ]

    chess_ss_err_plain_path_m2_x10_sampling = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS10/08_Nov_22_21_13",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_00_27_38",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_01_00_00",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_01_32_21",
    ]

    chess_ss_err_plain_path_m2_x50_sampling = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS10/08_Nov_22_21_13",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_02_04_40",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_02_37_07",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_03_09_28",
    ]

    chess_ss_err_plain_path_m2_x90_sampling = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS10/08_Nov_22_21_13",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_03_41_51",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_04_14_19",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM2_NS10/09_Nov_04_46_41",
    ]

    chess_ss_err_plain_path_m3_sampling = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM0_NS10/08_Nov_22_21_13",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS10/09_Nov_05_18_59",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS10/09_Nov_05_51_29",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/EM3_NS10/09_Nov_06_23_49",
    ]

    m1_avg = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM1_NS1/chess_X0.01_09_Nov_11_19_37",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_avg/EM1_NS10/chess_X0.01_09_Nov_13_38_32",  # 10
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_avg/EM1_NS20/chess_X0.01_09_Nov_13_41_44",  # 20
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_avg/EM1_NS100/chess_X0.01_09_Nov_13_44_56",  # 100
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_avg/EM1_NS1000/chess_X0.01_09_Nov_13_48_09",  # 1000
    ]

    m2_avg = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM2_NS1/chess_X0.01_P0.99_09_Nov_11_22_54",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM2_NS10/chess_X0.01_P0.99_09_Nov_11_35_46",  # sampling median
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min_avg/EM2_NS10/chess_X0.01_P0.99_09_Nov_12_39_42",  # 10
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min_avg/EM2_NS20/chess_X0.01_P0.99_09_Nov_12_49_23",  # 20
    ]

    m3_avg = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM0_NS1/chess_111636_11092023_09_Nov_11_16_25",  # no error
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM3_NS1/chess_P0.99_09_Nov_11_26_09",  # no sampling
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min/EM3_NS10/chess_P0.99_09_Nov_11_38_59",  # sampling median
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min_avg/EM3_NS10/chess_P0.99_09_Nov_12_42_55",  # 10
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess_min_avg/EM3_NS20/chess_P0.99_09_Nov_12_52_40",  #20
    ]

    sk_no_standby = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0.1_16_Nov_13_24_02",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0.01_16_Nov_13_28_22",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0.001_16_Nov_13_32_47",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0.0001_16_Nov_13_37_19",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0_16_Nov_13_00_54",  # no failure
    ]

    sk_standby = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/STrue/skateboard_F0.1_16_Nov_13_05_20",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/STrue/skateboard_F0.01_16_Nov_13_09_48",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/STrue/skateboard_F0.001_16_Nov_13_14_14",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/STrue/skateboard_F0.0001_16_Nov_13_18_44",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard/SFalse/skateboard_F0_16_Nov_13_00_54",
        # no failure
    ]

    sk_no_standby_labels = [
        "10% failure, 938 failures",
        "1% failure, 65 failures",
        "0.1% failure, 1 failure",
        "0.01% failure, 0 failure",
        "No failures"
    ]

    sk_standby_labels = [
        "10% failure, 771 failures",
        "1% failure, 61 failures",
        "0.1% failure, 2 failures",
        "0.01% failure, 1 failure",
        "No failures"
    ]

    sk_10 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard_2/STrue/skateboard_F0.1_16_Nov_18_28_16",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard_2/SFalse/skateboard_F0.1_16_Nov_18_24_22",
    ]

    sk_1 = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard_2/STrue/skateboard_F0.01_16_Nov_18_36_03",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/skateboard_2/SFalse/skateboard_F0.01_16_Nov_18_32_10",
    ]

    sk_10_labels = [
        "10%, 1660 failures, w/ standby",
        "10%, 1855 failures, no standby"
    ]

    sk_1_labels = [
        "1%, 82 failures, w/ standby",
        "1%, 82 failures, no standby"
    ]

    chess_ss_err_plain_labels_m1 = [
        "No error",
        "M1, x=1%",
        "M1, x=1% w/ 10 samples",
        "M1, x=1% w/ 20 samples",
        "M1, x=1% w/ 100 samples",
        "M1, x=1% w/ 1000 samples",
        # "M1, x=10%",
        # "M1, x=50%",
        # "M1, x=90%",
    ]

    chess_ss_err_plain_labels_m2_x10 = [
        "No error",
        "M2, x=1%, p=99%",
        "M2, x=1%, p=99% w/ median of samples",
        "M2, x=1%, p=99% w/ mean of samples",
        # "M2, x=10%, p=90%",
        # "M2, x=10%, p=50%",
        # "M2, x=10%, p=10%",
    ]

    chess_ss_err_plain_labels_m2_x50 = [
        "No error",
        "M2, x=50%, p=90%",
        "M2, x=50%, p=50%",
        "M2, x=50%, p=10%",
    ]

    chess_ss_err_plain_labels_m2_x90 = [
        "No error",
        "M2, x=90%, p=90%",
        "M2, x=90%, p=50%",
        "M2, x=90%, p=10%",
    ]

    chess_ss_err_plain_labels_m3 = [
        "No error",
        "M3, p=99%",
        "M3, p=99% w/ median of samples",
        "M3, p=99% w/ mean of samples",
        # "M3, p=90%",
        # "M3, p=50%",
        # "M3, p=10%",
    ]

    fail_poses = [
        (50, 10),
        (50, 0.5),
        (55, 0.06),
        (28, 1.1),
        (28, 1.1),
        (28, 1.1),
    ]

    tab_colors = [
        'tab:purple',
        'tab:orange',
        'tab:cyan',
        'tab:blue',
        'tab:pink',
        'tab:olive',
    ]

    cmp_colors = [
        'tab:blue',
        'tab:olive',
        'tab:orange',
        'tab:red',
        'tab:green',
    ]

    # for c_name, t_path in zip(st_labels, st_path):
    #     cols = get_table_vals(t_path)
    #     print(f"{c_name} & {' & '.join([str(x) for x in cols.values()])} \\\\")
    #     print("\hline")
    #
    # # print(f"{' & '.join([str(x) for x in cols.keys()])} \\")
    #
    # exit()
        
        
    dest = "/Users/hamed/Documents/Holodeck/SwarMerPy/results/"
    # gen_shape_comp_hd(comp_path, comp_labels, comp_poses, tab_colors, dest + "hd_comp.png")
    # gen_shape_comp_hd(loss_r_path, loss_r_labels, loss_r_poses, tab_colors, dest + "skateboard_receiver_packet_loss_comp.png")
    # gen_shape_comp_hd(loss_path, loss_labels, loss_poses, tab_colors, dest + "skateboard_packet_loss_comp.png")
    # gen_shape_comp_hd(sk_fail_path, sk_fail_labels, fail_poses, tab_colors, dest + "skateboard_failure_comp.png")
    # gen_shape_comp_hd(fail_path, fail_labels, fail_poses, tab_colors, dest + "200_failure_comp.png")
    # gen_shape_comp_hd_2(st_path, st_labels, tab_colors, dest + "challenge_interval_comp.png")
    # gen_shape_comp_hd_2(sk_st_path, sk_st_labels, tab_colors, dest + "skateboard_challenge_interval_comp.png")
    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/1693587710", "*", False)

    # gen_shape_comp_hd_2(chess_ss_err_plain_path_m1, chess_ss_err_plain_labels_m1, tab_colors, dest + "chess_100_ss_m1_2.png")
    # time_to_e2 = []
    # time_to_e2 += gen_shape_comp_hd(sk_10, sk_10_labels, fail_poses, tab_colors, dest + "skateboard_10_percent.png")
    # time_to_e2 += gen_shape_comp_hd(sk_1, sk_1_labels, fail_poses, tab_colors, dest + "skateboard_1_percent.png")

   # time_to_e2 += gen_shape_comp_hd(sk_standby, sk_standby_labels, fail_poses, tab_colors, dest + "skateboard_100_with_standby.png")
    # time_to_e2 += gen_shape_comp_hd(sk_no_standby, sk_no_standby_labels, fail_poses, tab_colors, dest + "skateboard_100_without_standby.png")[1:]

    # time_to_e2 += gen_shape_comp_hd(m1_avg, chess_ss_err_plain_labels_m1, fail_poses, tab_colors, dest + "chess_100_ss_m1_avg.png")
    # time_to_e2 += gen_shape_comp_hd(m2_avg, chess_ss_err_plain_labels_m2_x10, fail_poses, tab_colors, dest + "v2_m2_min_cmp.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(m3_avg, chess_ss_err_plain_labels_m3, fail_poses, tab_colors, dest + "v2_m3_min_cmp.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m1, chess_ss_err_plain_labels_m1, fail_poses, tab_colors, dest + "chess_100_ss_m1.png")
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x10, chess_ss_err_plain_labels_m2_x10, fail_poses, tab_colors, dest + "chess_100_ss_m2_x10.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x50, chess_ss_err_plain_labels_m2_x50, fail_poses, tab_colors, dest + "chess_100_ss_m2_x50.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x90, chess_ss_err_plain_labels_m2_x90, fail_poses, tab_colors, dest + "chess_100_ss_m2_x90.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m3, chess_ss_err_plain_labels_m3, fail_poses, tab_colors, dest + "chess_100_ss_m3.png")[1:]

    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m1_sampling, chess_ss_err_plain_labels_m1, fail_poses, tab_colors,
    #                                 dest + "chess_100_ss_m1_sampling.png")
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x10_sampling, chess_ss_err_plain_labels_m2_x10, fail_poses,
    #                                 tab_colors, dest + "chess_100_ss_m2_x10_sampling.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x50_sampling, chess_ss_err_plain_labels_m2_x50, fail_poses,
    #                                 tab_colors, dest + "chess_100_ss_m2_x50_sampling.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m2_x90_sampling, chess_ss_err_plain_labels_m2_x90, fail_poses,
    #                                 tab_colors, dest + "chess_100_ss_m2_x90_sampling.png")[1:]
    # time_to_e2 += gen_shape_comp_hd(chess_ss_err_plain_path_m3_sampling, chess_ss_err_plain_labels_m3, fail_poses, tab_colors,
    #                                 dest + "chess_100_ss_m3_sampling.png")[1:]

    # print(time_to_e2)
    # exit()

    # fig, ax = plt.subplots()
    #
    # labels = chess_ss_err_plain_labels_m1 + \
    #          chess_ss_err_plain_labels_m2_x10[1:] + \
    #          chess_ss_err_plain_labels_m2_x50[1:] + \
    #          chess_ss_err_plain_labels_m2_x90[1:] + \
    #          chess_ss_err_plain_labels_m3[1:]
    # counts = time_to_e2
    # # bar_labels = ['red', 'blue', '_red', 'orange']
    # # bar_colors = ['tab:red', 'tab:blue', 'tab:red', 'tab:orange']
    #
    # ax.bar(labels, counts)
    #
    # # ax.set_ylabel('Error Moded')
    # ax.set_title('Time to reach HD<=1e-2')
    # # ax.legend(title='Fruit color')
    #
    # fig.autofmt_xdate()
    #
    # plt.savefig(dest + "chess_time_to_e_2_sampling", dpi=300)

    # exit()

    for i in range(1):
        path = comp_path[0]
        # json_files = glob.glob(f"{path}/timeline_*.json")
        # print(len(json_files))
        # # continue
        # create_csv_from_json(path)
        # combine_csvs(path, path)
        # gen_util_chart(path)
        gen_sw_charts(path, "*", "", True)

    exit()

    dragon_time = [987, 1780, 2219, 2585]
    hat_time = [1150, 3120, 4026, 5245]
    skateboard_time = [2731, 4348, 5189, 6876]
    # find_time_by_hd(comp_path[1])
    # exit()
    # ptlds = []
    # for t, hd in zip(dragon_time, dragon_hd):
    #     ptlds.append(gen_shape_fig_by_time(comp_path[0], t, hd))
    #
    # quad(ptlds, dest + 'Dragon_HD_comp.png')

    times = [dragon_time, hat_time, skateboard_time]
    # times = [dragon_time]
    labels = ['dragon_HD_comp.png', 'hat_HD_comp.png', 'skateboard_HD_comp.png']
    # labels = ['dragon_HD_comp.png']

    for path, name, hd_t in zip(comp_path, labels, times):
        ptlds = []
        hds = []
        for t in hd_t:
            ptld, h = gen_shape_fig_by_time(path, t)
            ptlds.append(ptld)
            hds.append(h)

        quad(ptlds, hds, dest + name)

    exit()

    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer/results/dragon/04_Aug_22_33_20", "*", False)
    # results_directory = "/Users/hamed/Desktop/60s/results/skateboard/11-Jun-14_38_12"
    # shape_directory = "/Users/hamed/Desktop/60s/results/skateboard"
    # create_csv_from_json(results_directory)
    # combine_csvs(results_directory, shape_directory)
