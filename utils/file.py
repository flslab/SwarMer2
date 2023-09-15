import heapq
import os
import json
import csv
import matplotlib as mpl

import numpy as np
from matplotlib import pyplot as plt

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


def gen_sliding_window_chart_data(timeline, start_time, value_fn, sw=0.001):  # 0.01
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
            r_xs = chart_data[0]
            t_idx = next(i for i, v in enumerate(r_xs) if v > 300)
            r_xs = chart_data[0][:t_idx]
            r_ys = chart_data[1][:t_idx]
            s_ys = chart_data[2][:t_idx]
            l_ys = chart_data[3][:t_idx]
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

    ax.step(r_xs, r_ys, where='post', label="Hausdorff distance", color="#00d5ff")
    # ax.step(s_xs, s_ys, where='post', label="Sent bytes", color="black")
    # ax.step(h_xs, h_ys, where='post', label="Heuristic invoked")
    ax.legend()
    # plt.ylim([10e-13, 10e3])
    # plt.yscale('log')
    # plt.show()
    plt.savefig(f'{path}/{fid}.png', dpi=300)


if __name__ == '__main__':

    paths = [
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_17_38_36",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_18_30_13",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/24_Aug_18_52_48",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/25_Aug_19_25_07",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692899950",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692902499",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692903856",
        # "/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer-2node/results/dragon/1692992188",
        "/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/1694542758",
    ]
    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/results/chess/1693587710", "*", False)
    for path in paths:
        gen_sw_charts(path, "*", False)
        create_csv_from_json(path)
        combine_csvs(path, path)

    # gen_sw_charts("/Users/hamed/Documents/Holodeck/SwarMerPy/scripts/aws/results/swarmer/results/dragon/04_Aug_22_33_20", "*", False)
    # results_directory = "/Users/hamed/Desktop/60s/results/skateboard/11-Jun-14_38_12"
    # shape_directory = "/Users/hamed/Desktop/60s/results/skateboard"
    # create_csv_from_json(results_directory)
    # combine_csvs(results_directory, shape_directory)
