import socket
import pickle
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


hd_timer = None
hd_round = []
hd_time = []
should_stop = False


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
        swarm_id = arr[3]
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

    results_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE, experiment_name)
    shape_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE)
    if not os.path.exists(results_directory):
        os.makedirs(os.path.join(results_directory, 'json'), exist_ok=True)
    mat = scipy.io.loadmat(f'assets/{Config.SHAPE}.mat')
    point_cloud = mat['p']

    if Config.SAMPLE_SIZE != 0:
        np.random.shuffle(point_cloud)
        point_cloud = point_cloud[:Config.SAMPLE_SIZE]

    total_count = point_cloud.shape[0]
    h = np.log2(total_count)

    gtl_point_cloud = np.random.uniform(0, 5, size=(total_count, 3))
    # x y z swarm_id is_failed
    sample = np.array([0.0, 0.0, 0.0, 0.0, 0.0])

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
    except OSError as e:
        print(e)
        for p in processes:
            p.terminate()
        for s in shared_memories:
            s.close()
            s.unlink()
        exit()

    gtl_point_cloud = local_gtl_point_cloud

    fin_message_sent = False
    final_point_cloud = np.zeros([count, 3])
    fin_processes = np.zeros(count)
    metrics = {}

    # compute_hd(shared_arrays, gtl_point_cloud)

    num_round = 0
    max_rounds = Config.NUMBER_ROUND
    round_time = [time.time()]
    swarms_metrics = []

    threading.Timer(Config.DURATION, set_stop).start()

    print('waiting for processes ...')

    ser_sock = worker.WorkerSocket()

    if Config.PROBABILISTIC_ROUND:
        while True:
            time.sleep(1)
            t = time.time()

            hdt = compute_hd([arr[:3] for arr in shared_arrays], gtl_point_cloud)
            hd_time.append((t, hdt))

            swarms = compute_swarm_size(shared_arrays)
            if 1 in swarms:
                print(swarms[1])
                if Config.DURATION < 660:
                    swarms_metrics.append((t, swarms))

            if should_stop:
                stop_message = Message(MessageTypes.STOP).from_server().to_all()
                dumped_stop_msg = pickle.dumps(stop_message)
                ser_sock.broadcast(dumped_stop_msg)
                time.sleep(1)
                break

    elif Config.CENTRALIZED_ROUND:
        reset = True
        last_thaw_time = time.time()
        round_duration = 0
        while True:
            time.sleep(0.1)
            t = time.time()

            # surviving_flss = []
            # gtl_p = []
            # for i in range(len(shared_arrays)):
            #     arr = shared_arrays[i]
            #     if arr[4] < 1:
            #         surviving_flss.append(arr[:3])
            #         gtl_p.append(gtl_point_cloud[i])

            swarms = compute_swarm_size(shared_arrays)
            merged_flss = max(swarms.values())
            # print(merged_flss)
            # if Config.DURATION < 660:
            #     swarms_metrics.append((t, swarms))

            # if N == 1 or nid == 0:
            # if t - last_thaw_time >= h:
            if (merged_flss == count or (round_duration != 0 and t - last_thaw_time >= round_duration)) and reset:
                print(merged_flss)
                thaw_message = Message(MessageTypes.THAW_SWARM, args=(t,)).from_server().to_all()
                ser_sock.broadcast(thaw_message)
                if round_duration == 0:
                    round_duration = t - last_thaw_time
                last_thaw_time = t
                reset = False
            if merged_flss != count:
                reset = True

            if should_stop:
                # hdt = compute_hd(surviving_flss, np.stack(gtl_p))
                # hd_time.append((t, hdt))
                if N == 1 or nid == 0:
                    stop_all()
                time.sleep(1)
                break

    elif Config.CENTRALIZED_SWARM_SIZE:
        thaw_message = Message(MessageTypes.THAW_SWARM).from_server().to_all()
        dumped_thaw_msg = pickle.dumps(thaw_message)

        while True:
            swarms = compute_swarm_size(shared_arrays)
            # print(swarms)
            if 1 in swarms:
                t = time.time()
                print(swarms[1])
                if Config.DURATION < 660:
                    swarms_metrics.append((t, swarms))

                if should_stop and Config.FAILURE_TIMEOUT:
                    stop_message = Message(MessageTypes.STOP).from_server().to_all()
                    dumped_stop_msg = pickle.dumps(stop_message)
                    ser_sock.broadcast(dumped_stop_msg)
                    time.sleep(1)
                    break

                if len(swarms) == 1 and swarms[1] == count:
                    num_round += 1
                    print(f'one swarm was detected by the server round{num_round}')
                    round_time.append(t)
                    hd_round.append((t, compute_hd([arr[:3] for arr in shared_arrays], gtl_point_cloud)))
                    if should_stop:
                        stop_message = Message(MessageTypes.STOP).from_server().to_all()
                        dumped_stop_msg = pickle.dumps(stop_message)
                        ser_sock.broadcast(dumped_stop_msg)
                        time.sleep(1)
                        break
                    else:
                        ser_sock.broadcast(dumped_thaw_msg)
            time.sleep(1)
    else:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        server_sock.bind(Constants.SERVER_ADDRESS)

        while True:
            data, _ = server_sock.recvfrom(2048)
            msg = pickle.loads(data)

            if msg.type == MessageTypes.FIN and not fin_message_sent:
                num_round += 1
                round_time.append(time.time())
                if num_round < max_rounds:
                    msg_type = MessageTypes.THAW_SWARM
                    msg_args = (round_time,)
                else:
                    msg_type = MessageTypes.STOP
                    fin_message_sent = True
                    msg_args = None

                server_message = Message(msg_type, args=msg_args).from_server().to_all()
                # send_message_to_all(server_message)
                continue

            final_point_cloud[msg.fid - 1] = msg.el
            if msg.args is not None:
                metrics[msg.fid] = msg.args[0]
            fin_processes[msg.fid - 1] = 1

            shared_memories[msg.fid - 1].close()
            shared_memories[msg.fid - 1].unlink()

            print(f"process {msg.fid} finished")

            if np.sum(fin_processes) == count:
                if hd_timer is not None:
                    hd_timer.cancel()
                start_time = time.time()
                final_hd = utils.hausdorff_distance(final_point_cloud, gtl_point_cloud)
                end_time = time.time()
                print(f"final hd: {final_hd} computed in {end_time-start_time} (s)")
                break
        server_sock.close()

    for p in processes:
        p.join(45)
        if p.is_alive():
            stop_all()
            time.sleep(45)
            break

    for p in processes:
        if p.is_alive():
            print("timeout")
            p.terminate()

    print("done")
    # if Config.PROBABILISTIC_ROUND or Config.CENTRALIZED_ROUND:
        # utils.write_hds_time(hd_time, results_directory, nid)
    # else:
    #     utils.write_hds_round(hd_round, round_time, results_directory, nid)
    # if Config.DURATION < 660:
    #     utils.write_swarms(swarms_metrics, round_time, results_directory, nid)

    if nid == 0:
        utils.write_configs(results_directory)

    # if N > 1 and nid == 0:
    #     print("wait a fixed time for other nodes")
    #     time.sleep(90)
    #
    #     utils.create_csv_from_json(results_directory)
    #     utils.combine_csvs(results_directory, shape_directory)

    for s in shared_memories:
        s.close()
        s.unlink()
