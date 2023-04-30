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


hd_timer = None
hds = []
should_stop = False


def set_stop():
    global should_stop
    should_stop = True
    print('will stop next round')


def compute_hd(sh_arrays, gtl):
    global hd_timer, hds
    if hd_timer is not None:
        hd_timer.cancel()
        hd_timer = None

    # hd_timer = threading.Timer(Config.HD_TIMOUT, compute_hd, args=(sh_arrays, gtl))
    # hd_timer.start()

    # sh_mem = shared_memory.SharedMemory(name=shm_name)
    # sh_array = np.ndarray((count, 3), dtype=np.float64, buffer=sh_mem.buf)
    # print(sh_array)
    hd_t = utils.hausdorff_distance(np.stack(sh_arrays), gtl)
    print(f"__hd__ {hd_t}")
    hds.append((time.time(), hd_t))


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
    # if len(sys.argv) > 1:
    #     Config.set_from_file(sys.argv[1])

    # print(vars(Config))
    # count = Config.NUMBER_POINTS
    # count = 30
    # np.random.default_rng(1)
    results_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE, str(int(time.time())))
    shape_directory = os.path.join(Config.RESULTS_PATH, Config.SHAPE)
    if not os.path.exists(results_directory):
        os.makedirs(os.path.join(results_directory, 'json'), exist_ok=True)
    mat = scipy.io.loadmat(f'assets/{Config.SHAPE}.mat')
    point_cloud = mat['p']

    if Config.SAMPLE_SIZE != 0:
        np.random.shuffle(point_cloud)
        point_cloud = point_cloud[:Config.SAMPLE_SIZE]

    count = point_cloud.shape[0]
    print(count)
    # np.random.shuffle(gtl_point_cloud)
    # print(gtl_point_cloud)
    gtl_point_cloud = np.random.uniform(0, 5, size=(count, 3))
    sample = np.array([0.0, 0.0, 0.0, 0.0])
    # gtl_point_cloud = np.array([[0, 0, 1], [0, 0, 2], [5, 5, 1], [5, 5, 2]])
    # el_point_cloud = gtl_point_cloud + np.random.randint(2, size=(count, 3))

    # shm = shared_memory.SharedMemory(create=True, size=gtl_point_cloud.nbytes)
    # shared_array = np.ndarray(gtl_point_cloud.shape, dtype=gtl_point_cloud.dtype, buffer=shm.buf)

    # utils.plot_point_cloud(gtl_point_cloud, None)
    # barrier = multiprocessing.Barrier(count+1, action=press_enter_to_proceed)

    for i in range(count):
        # o = np.array([0, 0, 10.0])
        # rx = np.array([16.0, 0, 0])
        # ry = np.array([0, 16.0, 0])
        # gtl_point_cloud[i] = o + rx * np.sin(i*2*np.pi/count) + ry * np.cos(i*2*np.pi/count)
        # gtl_point_cloud[i] = np.array([i, i, i])
        gtl_point_cloud[i] = np.array([point_cloud[i][0], point_cloud[i][1], point_cloud[i][2]])

    # np.random.shuffle(gtl_point_cloud)

    processes = []
    shared_arrays = []
    shared_mems = []

    try:
        for i in range(count):
            shm = shared_memory.SharedMemory(create=True, size=sample.nbytes)
            shared_array = np.ndarray(sample.shape, dtype=sample.dtype, buffer=shm.buf)
            shared_array[:] = sample[:]

            shared_arrays.append(shared_array)
            shared_mems.append(shm)
            p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], np.array([0, 0, 0]), shm.name, results_directory)
            p.start()
            processes.append(p)
    except OSError as e:
        print(e)
        for p in processes:
            p.terminate()
        for s in shared_mems:
            s.close()
            s.unlink()
        exit()

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

    if Config.CENTRALIZED_SWARM_SIZE:
        ser_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ser_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        ser_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ser_sock.settimeout(.2)

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
                    ser_sock.sendto(dumped_stop_msg, Constants.BROADCAST_ADDRESS)
                    time.sleep(1)
                    break

                if len(swarms) == 1 and swarms[1] == count:
                    num_round += 1
                    print(f'one swarm was detected by the server round{num_round}')
                    round_time.append(t)
                    compute_hd([arr[:3] for arr in shared_arrays], gtl_point_cloud)
                    if should_stop:
                        stop_message = Message(MessageTypes.STOP).from_server().to_all()
                        dumped_stop_msg = pickle.dumps(stop_message)
                        ser_sock.sendto(dumped_stop_msg, Constants.BROADCAST_ADDRESS)
                        time.sleep(1)
                        break
                    else:
                        ser_sock.sendto(dumped_thaw_msg, Constants.BROADCAST_ADDRESS)
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

            shared_mems[msg.fid - 1].close()
            shared_mems[msg.fid - 1].unlink()

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
        p.join(5)
        if p.is_alive():
            json_files = glob.glob(os.path.join(results_directory, "json", "*.json"))
            print(len(json_files))
            if len(json_files) == count:
                break

    for p in processes:
        if p.is_alive():
            p.terminate()

    timestamp = int(time.time())

    utils.write_hds(hds, round_time, results_directory)
    if Config.DURATION < 660:
        utils.write_swarms(swarms_metrics, round_time, results_directory)
    utils.write_configs(results_directory)
    utils.create_csv_from_json(results_directory)
    utils.combine_csvs(results_directory, shape_directory)
    # utils.plot_point_cloud(np.stack(shared_arrays), None)

    # compute_hd([arr[:3] for arr in shared_arrays], gtl_point_cloud)
    for s in shared_mems:
        s.close()
        s.unlink()

    # print("writing bag file...")
    # import bag
    #
    # msgs = [bag.generate_msg_metrics(path) for path in metrics.values()]
    # bag.write_msgs_bag(msgs, 'test.bag')

    # bag = rosbag.Bag('test.bag')
    # for topic, msg, t in bag.read_messages(topics=['topic']):
    #     print(msg)
    # bag.close()
