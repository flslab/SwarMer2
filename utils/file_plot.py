import heapq
import os
import json
import csv
import matplotlib as mpl

import numpy as np
from matplotlib import pyplot as plt, ticker

from config import Config
import pandas as pd
import glob

from utils import hausdorff_distance
from worker.metrics import TimelineEvents


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
    ys = [-1]
    swarm_ys = [-1]
    lease_exp_ys = [0]

    current_points = {}
    current_swarms = {}
    gtl_points = {}

    while len(timeline):
        event = timeline[0]
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
            elif e_type == TimelineEvents.SWARM:
                current_swarms[e_fid] = event[2]
            elif e_type == TimelineEvents.LEASE_EXP:
                lease_exp_ys[-1] += 1
            timeline.pop(0)
        else:
            swarm_ys[-1] = len(set(current_swarms.values()))
            # print(len(current_swarms))
            if len(current_points) > 1 and len(gtl_points):
                ys[-1] = hausdorff_distance(np.stack(list(current_points.values())), np.stack(list(gtl_points.values())))
                # ys[-1] = 1
            xs.append(xs[-1] + sw)
            ys.append(-1)
            swarm_ys.append(-1)
            lease_exp_ys.append(0)

    if ys[-1] == -1:
        xs.pop(-1)
        ys.pop(-1)
        swarm_ys.pop(-1)
        lease_exp_ys.pop(-1)

    print(sum(lease_exp_ys))
    return xs, ys, swarm_ys, lease_exp_ys


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


def gen_sw_charts(path, fid, read_from_file=True):
    fig = plt.figure()
    ax = fig.add_subplot()

    if read_from_file:
        with open(f"{path}/charts.json") as f:
            chart_data = json.load(f)
            # r_xs = chart_data[0]
            # t_idx = next(i for i, v in enumerate(r_xs) if v > 300)
            r_xs = chart_data[0]
            r_ys = chart_data[1]
            s_ys = chart_data[2]
            l_ys = chart_data[3]
    else:
        data = read_timelines(path, fid)
        r_xs, r_ys, s_ys, l_ys = gen_sliding_window_chart_data(data['timeline'], data['start_time'], lambda x: x[2])
        with open(f"{path}/charts.json", "w") as f:
            json.dump([r_xs, r_ys, s_ys, l_ys], f)

    # s_xs, s_ys = gen_sliding_window_chart_data(data['sent_bytes'], data['start_time'], lambda x: x[2])
    # h_xs, h_ys = gen_sliding_window_chart_data(data['heuristic'], data['start_time'], lambda x: 1)
    ax.step(r_xs, s_ys, where='post', label="Number of swarms", color="#ee2010")
    ax.step(r_xs, l_ys, where='post', label="Number of expired leases")
    while True:
        if r_ys[0] == -1:
            r_ys.pop(0)
            r_xs.pop(0)
        else:
            break

    # ax.step(s_xs, s_ys, where='post', label="Sent bytes", color="black")
    # ax.step(h_xs, h_ys, where='post', label="Heuristic invoked")
    ax.legend()
    # plt.xlim([0, 60])
    # plt.show()
    plt.savefig(f'{path}/{fid}.png', dpi=300)

    fig = plt.figure()
    ax = fig.add_subplot()
    ax.step(r_xs, r_ys, where='post', label="Hausdorff distance", color="#00d5ff")
    ax.legend()
    plt.ylim([10e-13, 10e3])
    plt.yscale('log')
    plt.savefig(f'{path}/{fid}h.png', dpi=300)


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
    fig = plt.figure(figsize=(6.5, 3))
    ax = fig.add_subplot()
    for path, label, pos, color in zip(paths, labels, poses, colors):
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
            ax.step(t, ys, where='post', color=color, label=label)
            # plt.text(pos[0], pos[1], label, color=color, fontweight='bold')

    ax.set_ylabel('Hausdorff distance (Display cell)', loc='top', rotation=0, labelpad=-133)
    ax.set_xlabel('Time (Second)', loc='right')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    plt.tight_layout()
    # plt.yscale('log')
    # plt.ylim([1e-3, 80])
    plt.ylim([0, 55])
    plt.xlim([0, 100])
    plt.legend()
    # y_locator = ticker.FixedLocator([1e-3, 1e-2, 1e-1, 1, 10, 100])
    # ax.yaxis.set_major_locator(y_locator)
    # y_formatter = ticker.FixedFormatter(["0.001", "0.01", "0.1", "1", "10", "100"])
    # ax.yaxis.set_major_formatter(y_formatter)
    # plt.savefig(dest, dpi=300)
    plt.show()


if __name__ == '__main__':
    mpl.rcParams['font.family'] = 'Times New Roman'
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
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_18_49",  # 0.001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_41_43",  # 0.0001
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-16-400-node-failure/results/skateboard/20_Sep_21_24_39",  # 0.001
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
        "No Packet loss",
        "0.1% Packet loss",
        "1% Packet loss",
        "10% Packet loss",
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
        "Asymmetric packet loss at receiver",
        "Symmetric packet loss",
        "Asymmetric packet loss at transmitter",
        "No packet loss",
    ]
    loss_poses = [
        (8, 0.003),
        (30, 0.25),
        (55, 0.06),
        (28, 1.1),
    ]

    loss_path = [
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_14_23",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_09_00",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_19_11_38",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/skateboard/19_Sep_18_56_55",

        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_37_35",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_40_23",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/hat/20_Sep_01_43_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/hat/19_Sep_19_29_54",

        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_21_00",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_24_02",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/results/dragon/20_Sep_01_26_34",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-6-12-16-400-node-3/results/dragon/19_Sep_19_24_01",

    ]
    tab_colors = [
        'tab:blue',
        'tab:orange',
        'tab:purple',
        'tab:green',
    ]

    cmp_colors = [
        'tab:green',
        'tab:olive',
        'tab:orange',
        'tab:red',
    ]

    dest = "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-8-16-400-node-d-h/skateboard_packet_loss_comp.svg"
    gen_shape_comp_hd(loss_path, loss_labels, loss_poses, cmp_colors, dest)
    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/1693587710", "*", False)
    # for path in paths:
    #     json_files = glob.glob(f"{path}/timeline_*.json")
    #     print(len(json_files))
    # #     # continue
    #     create_csv_from_json(path)
    #     combine_csvs(path, path)
    #     gen_util_chart(path)
    #     gen_sw_charts(path, "*", False)

    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer/results/dragon/04_Aug_22_33_20", "*", False)
    # results_directory = "/Users/hamed/Desktop/60s/results/skateboard/11-Jun-14_38_12"
    # shape_directory = "/Users/hamed/Desktop/60s/results/skateboard"
    # create_csv_from_json(results_directory)
    # combine_csvs(results_directory, shape_directory)
