import os
import json
import csv
from config import Config


def write_json(file_name, dictionary):
    directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(os.path.join(directory, f"{file_name}.json"), "w") as f:
        json.dump(dictionary, f)


def create_csv_from_json():
    directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE)
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

    with open(os.path.join(directory, 'all.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


if __name__ == '__main__':
    create_csv_from_json()
