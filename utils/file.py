import os
import json
import csv
from config import Config
import pandas as pd
import glob


def write_json(file_name, results, directory):
    with open(os.path.join(directory, f"{file_name}.json"), "w") as f:
        json.dump(results, f)


def create_csv_from_json(directory):
    if not os.path.exists(directory):
        return

    headers = []
    rows = []

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename)) as f:
                data = json.load(f)
                if len(headers) == 0:
                    headers = list(data.keys())
                    rows.append(['fid'] + headers)

                fid = filename.split('.')[0]
                row = [fid] + [data[h] for h in headers]
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


def combine_csvs(directory):
    csv_files = glob.glob(f"{directory}/*.csv")

    with pd.ExcelWriter(os.path.join(directory, f'{Config.SHAPE}.xlsx')) as writer:
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            sheet_name = csv_file.split('/')[-1][:-4]
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    with open(os.path.join(directory, 'config.txt'), 'w') as f:
        for a, b in vars(Config).items():
            if not a.startswith('__'):
                f.write(f"{a}: {b}\n")

