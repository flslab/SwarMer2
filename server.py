import threading
import socket
import pickle
import numpy as np
from multiprocessing import shared_memory
import scipy.io
import time

from config import Config
from constants import Constants
from message import Message, MessageTypes
import worker
import utils


hd_timer = None
hds = []


def compute_hd(sh_arrays, gtl):
    global hd_timer, hds
    if hd_timer is not None:
        hd_timer.cancel()
        hd_timer = None

    hd_timer = threading.Timer(1, compute_hd, args=(sh_arrays, gtl))
    hd_timer.start()

    # sh_mem = shared_memory.SharedMemory(name=shm_name)
    # sh_array = np.ndarray((count, 3), dtype=np.float64, buffer=sh_mem.buf)
    # print(sh_array)
    hds.append((time.time(), utils.hausdorff_distance(np.stack(sh_arrays), gtl)))


if __name__ == '__main__':
    # count = Config.NUMBER_POINTS
    # count = 4
    # np.random.default_rng(1)
    mat = scipy.io.loadmat(f'{Config.SHAPE}.mat')
    point_cloud = mat['p']
    count = point_cloud.shape[0]
    # print(count)
    # np.random.shuffle(gtl_point_cloud)
    # print(gtl_point_cloud)
    gtl_point_cloud = np.random.uniform(0, 5, size=(count, 3))
    sample = np.array([0.0, 0.0, 0.0])
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
        gtl_point_cloud[i] = np.array([point_cloud[i][0], point_cloud[i][1], 10.0])

    # np.random.shuffle(gtl_point_cloud)

    processes = []
    shared_arrays = []
    shared_mems = []
    for i in range(count):
        shm = shared_memory.SharedMemory(create=True, size=sample.nbytes)
        shared_array = np.ndarray(sample.shape, dtype=sample.dtype, buffer=shm.buf)
        shared_array[:] = sample[:]

        shared_arrays.append(shared_array)
        shared_mems.append(shm)
        p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], np.array([0, 0, 0]), shm.name)
        p.start()
        processes.append(p)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    server_sock.bind(Constants.SERVER_ADDRESS)
    fin_message_sent = False
    final_point_cloud = np.zeros([count, 3])
    fin_processes = np.zeros(count)
    metrics = {}

    compute_hd(shared_arrays, gtl_point_cloud)

    num_round = 0
    max_rounds = Config.NUMBER_ROUND
    round_time = [time.time()]

    while True:
        data, _ = server_sock.recvfrom(2048)
        msg = pickle.loads(data)

        if msg.type == MessageTypes.FIN and not fin_message_sent:
            num_round += 1
            round_time.append(time.time())
            if num_round < max_rounds:
                msg_type = MessageTypes.THAW_SWARM
                msg_args = None
            else:
                msg_type = MessageTypes.STOP
                fin_message_sent = True
                msg_args = (round_time,)

            server_message = Message(msg_type, args=msg_args).from_server().to_all()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            sock.sendto(pickle.dumps(server_message), Constants.BROADCAST_ADDRESS)
            sock.sendto(pickle.dumps(server_message), Constants.BROADCAST_ADDRESS)
            sock.close()
            continue

        final_point_cloud[msg.fid - 1] = msg.el
        metrics[msg.fid] = msg.args[0]
        fin_processes[msg.fid - 1] = 1

        if np.sum(fin_processes) == count:
            print(f"hd: {utils.hausdorff_distance(final_point_cloud, gtl_point_cloud)}")

            hd_timer.cancel()
            break

    server_sock.close()

    # print(shared_array)
    # utils.plot_point_cloud(shared_array, None)

    for p in processes:
        p.join()

    timestamp = int(time.time())
    with open(f'packets_{Config.SHAPE}_{timestamp}.txt', 'w') as f:
        headers = " ".join(metrics[1].keys())
        f.write(f"fid {headers}\n")
        for key, value in metrics.items():
            values = " ".join([str(v) for v in value.values()])
            f.write(f"{key} {values}\n")

    with open(f'hd_{Config.SHAPE}_{timestamp}.txt', 'w') as f:
        for hd in hds:
            f.write(f"{hd[0]} {hd[1]}\n")
        for rt in round_time:
            f.write(f"{rt}\n")

    # utils.plot_point_cloud(np.stack(shared_arrays), None)

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
