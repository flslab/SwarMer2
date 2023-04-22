import os
import json
import csv
import shutil

from config import Config
import pandas as pd
import glob


def write_json(file_name, results, directory):
    with open(os.path.join(directory, 'json', f"{file_name}.json"), "w") as f:
        json.dump(results, f)


def create_csv_from_json(directory):
    if not os.path.exists(directory):
        return

    headers = []
    rows = []

    json_dir = os.path.join(directory, 'json')

    for filename in os.listdir(json_dir):
        if filename.endswith('.json'):
            with open(os.path.join(json_dir, filename)) as f:
                data = json.load(f)
                if len(headers) == 0:
                    headers = list(data.keys())
                    rows.append(['fid'] + headers)

                fid = filename.split('.')[0]
                row = [fid] + [data[h] if h in data else 0 for h in headers]
                rows.append(row)

    with open(os.path.join(directory, 'metrics.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_hds(hds, rounds, directory):
    if not os.path.exists(directory):
        return

    headers = ['round', 'time(s)', 'hd']
    rows = [headers]

    for i in range(len(hds)):
        row = [i+1, rounds[i+1] - rounds[0], hds[i][1]]
        rows.append(row)

    with open(os.path.join(directory, 'hd.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_swarms(swarms, rounds, directory):
    headers = ['times(s)', 'num_swarms', 'average_swarm_size', 'largest_swarm', 'smallest_swarm']

    rows = [headers]

    for i in range(len(swarms)):
        t = swarms[i][0] - rounds[0]
        num_swarms = len(swarms[i][1])
        sizes = swarms[i][1].values()

        row = [t, num_swarms, sum(sizes)/num_swarms, max(sizes), min(sizes)]
        rows.append(row)

    with open(os.path.join(directory, 'swarms.csv'), 'w', newline='') as csvfile:
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


def combine_csvs(directory):
    from datetime import datetime
    current_datetime = datetime.now()
    current_date_time = current_datetime.strftime("%H:%M:%S_%m:%d:%Y")

    csv_files = glob.glob(f"{directory}/*.csv")
    xslx_dir = os.path.join(*directory.split('/')[:-1])

    with pd.ExcelWriter(os.path.join(xslx_dir, f'{Config.SHAPE}_{current_date_time}.xlsx')) as writer:
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            sheet_name = csv_file.split('/')[-1][:-4]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    shutil.rmtree(os.path.join(directory))
