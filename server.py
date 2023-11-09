import json
import socket
import pickle
import struct

import numpy as np
from multiprocessing import shared_memory
import scipy.io
import time
import os
import threading
from config import Config
from constants import Constants
from message import Message, MessageTypes
import worker
import utils
import glob
import sys
from stop import stop_all
import psutil
from datetime import datetime

hd_timer = None
hd_round = []
hd_time = []
should_stop = False


def join_config_properties(conf, props):
    return "_".join(
        f"{k[1] if isinstance(k, tuple) else k}{getattr(conf, k[0] if isinstance(k, tuple) else k)}" for k in
        props)


def query_swarm_client(connection):
    query_msg = Message(MessageTypes.QUERY_SWARM)
    connection.send(pickle.dumps(query_msg))


def pull_swarm_client(connection):
    data = recv_msg(connection)
    message = pickle.loads(data)
    return message.args[0], message.args[1]


def send_msg(sock, msg):
    # Prefix each message with a 4-byte big-endian unsigned integer (network byte order)
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)


def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data


def stop_client(connection):
    stop_msg = Message(MessageTypes.STOP)
    connection.send(pickle.dumps(stop_msg))


def wait_for_client(sock):
    sock.recv(1)
    sock.close()


def set_stop():
    global should_stop
    should_stop = True
    print('will stop next round')


def compute_hd(sh_arrays, gtl):
    hd_t = utils.hausdorff_distance(np.stack(sh_arrays), gtl)
    print(f"__hd__ {hd_t}")
    return hd_t


def compute_swarm_size(sh_arrays):
    swarm_counts = {}
    for arr in sh_arrays:
        swarm_id = arr[0]
        if swarm_id in swarm_counts:
            swarm_counts[swarm_id] += 1
        else:
            swarm_counts[swarm_id] = 1
    return swarm_counts


if __name__ == '__main__':
    N = 1
    nid = 0
    experiment_name = str(int(time.time()))
    if len(sys.argv) > 1:
        N = int(sys.argv[1])
        nid = int(sys.argv[2])
        experiment_name = sys.argv[3]

    IS_CLUSTER_SERVER = N != 1 and nid == 0
    IS_CLUSTER_CLIENT = N != 1 and nid != 0

    if IS_CLUSTER_SERVER:
        ServerSocket = socket.socket()
        ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while True:
            try:
                ServerSocket.bind(Constants.SERVER_ADDRESS)
            except OSError:
                time.sleep(10)
                continue
            break
        ServerSocket.listen(N - 1)

        clients = []
        for i in range(N - 1):
            client, address = ServerSocket.accept()
            print(address)
            clients.append(client)

    if IS_CLUSTER_CLIENT:
        client_socket = socket.socket()
        while True:
            try:
                client_socket.connect(Constants.SERVER_ADDRESS)
            except OSError:
                time.sleep(10)
                continue
            break

    dir_name = None
    current_date_time = datetime.now().strftime("%H%M%S_%m%d%Y")
    if len(Config.FILE_NAME_KEYS):
        keys = join_config_properties(Config, Config.FILE_NAME_KEYS)
    else:
        keys = current_date_time
    file_name = f"{Config.SHAPE}_{keys}_{experiment_name}"

    if len(Config.DIR_KEYS):
        dir_name = join_config_properties(Config, Config.DIR_KEYS)

    main_dir = Config.RESULTS_PATH if dir_name is None else os.path.join(Config.RESULTS_PATH, Config.SHAPE, dir_name)
    results_directory = os.path.join(main_dir, file_name)
    shape_directory = main_dir
    print(main_dir)
    # exit()

    # results_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE, experiment_name)
    # shape_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE)
    if not os.path.exists(results_directory):
        os.makedirs(os.path.join(results_directory, 'json'), exist_ok=True)
    mat = scipy.io.loadmat(f'assets/{Config.SHAPE}.mat')
    point_cloud = mat['p']

    if Config.SAMPLE_SIZE != 0:
        # np.random.shuffle(point_cloud)
        point_cloud = point_cloud[:Config.SAMPLE_SIZE]

    total_count = point_cloud.shape[0]
    h = np.log2(total_count)

    gtl_point_cloud = np.random.uniform(0, 5, size=(total_count, 3))
    # x y z swarm_id is_failed
    sample = np.array([0.0])

    node_point_idx = []
    for i in range(total_count):
        if i % N == nid:
            node_point_idx.append(i)
            gtl_point_cloud[i] = np.array([point_cloud[i][0], point_cloud[i][1], point_cloud[i][2]])

    count = len(node_point_idx)
    print(count)

    processes = []
    shared_arrays = []
    shared_memories = []

    local_gtl_point_cloud = []
    try:
        for i in node_point_idx:
            shm = shared_memory.SharedMemory(create=True, size=sample.nbytes)
            shared_array = np.ndarray(sample.shape, dtype=sample.dtype, buffer=shm.buf)
            shared_array[:] = sample[:]

            shared_arrays.append(shared_array)
            shared_memories.append(shm)
            local_gtl_point_cloud.append(gtl_point_cloud[i])
            p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], np.array([0, 0, 0]), shm.name, results_directory)
            p.start()
            processes.append(p)
            # time.sleep(0.1)
    except OSError as e:
        print(e)
        for p in processes:
            p.terminate()
        for s in shared_memories:
            s.close()
            s.unlink()
        exit()

    gtl_point_cloud = local_gtl_point_cloud

    if nid == 0:
        threading.Timer(Config.DURATION, set_stop).start()

    print('waiting for processes ...')

    ser_sock = worker.WorkerSocket()

    if IS_CLUSTER_CLIENT:
        while True:
            server_msg = client_socket.recv(2048)
            server_msg = pickle.loads(server_msg)

            if server_msg.type == MessageTypes.QUERY_SWARM:
                swarms = compute_swarm_size(shared_arrays)
                response = Message(MessageTypes.REPLY_SWARM, args=(swarms, psutil.cpu_percent()))
                send_msg(client_socket, pickle.dumps(response))
            elif server_msg.type == MessageTypes.STOP:
                break
    else:
        reset = True
        last_thaw_time = time.time()
        round_duration = 0
        last_merged_flss = 0
        no_change_counter = 0
        server_cpu = []
        server_time = []
        while True:
            time.sleep(0.2)
            t = time.time()

            swarms = compute_swarm_size(shared_arrays)
            server_cpu.append([psutil.cpu_percent()])
            server_time.append(time.time())

            if IS_CLUSTER_SERVER:
                for i in range(N - 1):
                    query_swarm_client(clients[i])

                for i in range(N - 1):
                    client_swarms, client_cpu = pull_swarm_client(clients[i])
                    server_cpu[-1].append(client_cpu)
                    for sid in client_swarms:
                        if sid in swarms:
                            swarms[sid] += client_swarms[sid]
                        else:
                            swarms[sid] = client_swarms[sid]

            largest_swarm = max(swarms.values())
            num_swarms = len(swarms)
            thaw_condition = False

            # if Config.THAW_INTERVAL:
            #     thaw_condition |= t - last_thaw_time > Config.THAW_INTERVAL
            # if Config.THAW_MIN_NUM_SWARMS:
            #     thaw_condition |= num_swarms == Config.THAW_MIN_NUM_SWARMS
            # if Config.THAW_PERCENTAGE_LARGEST_SWARM:
            #     thaw_condition |= merged_flss / total_count >= Config.THAW_PERCENTAGE_LARGEST_SWARM
            if (largest_swarm == total_count or num_swarms == 1 or
                # (round_duration != 0 and t - last_thaw_time >= round_duration) or
                    (t - last_thaw_time >= h)):
                if reset:
                    print(largest_swarm, num_swarms)
                    thaw_message = Message(MessageTypes.THAW_SWARM, args=(t,)).from_server().to_all()
                    ser_sock.broadcast(thaw_message)
                    if round_duration == 0 and largest_swarm == total_count:
                        round_duration = t - last_thaw_time
                    last_thaw_time = t
                    reset = False
            if largest_swarm != count:
                reset = True

            if should_stop:
                stop_all()
                break

    if IS_CLUSTER_SERVER:
        for i in range(N - 1):
            stop_client(clients[i])

        client_threads = []
        for client in clients:
            t = threading.Thread(target=wait_for_client, args=(client,))
            t.start()
            client_threads.append(t)
        for t in client_threads:
            t.join()

        ServerSocket.close()
        print("secondary nodes are done")

    for p in processes:
        p.join(30)
        if p.is_alive():
            continue

    for p in processes:
        if p.is_alive():
            print("timeout")
            p.terminate()

    # if Config.PROBABILISTIC_ROUND or Config.CENTRALIZED_ROUND:
        # utils.write_hds_time(hd_time, results_directory, nid)
    # else:
    #     utils.write_hds_round(hd_round, round_time, results_directory, nid)
    # if Config.DURATION < 660:
    #     utils.write_swarms(swarms_metrics, round_time, results_directory, nid)

    if nid == 0:
        utils.write_configs(results_directory)
        print("primary node is done")

    for s in shared_memories:
        s.close()
        s.unlink()

    if IS_CLUSTER_CLIENT:
        time.sleep(10)
        client_socket.send(struct.pack('b', True))
        client_socket.close()

    if nid == 0:
        with open(f"{results_directory}/utilization.json", "w") as f:
            json.dump([server_time, server_cpu], f)
        # print("wait a fixed time for other nodes")
        # time.sleep(90)

        # utils.create_csv_from_json(results_directory)
        # utils.combine_csvs(results_directory, shape_directory)
        utils.create_csv_from_json(results_directory)
        utils.combine_csvs(results_directory, results_directory)
        utils.gen_sw_charts(results_directory, "*", keys, False)
