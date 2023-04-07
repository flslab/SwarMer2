import multiprocessing
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
    count = 94
    # np.random.default_rng(1)
    mat = scipy.io.loadmat('butterfly.mat')
    butterfly = mat['p']
    # count = butterfly.shape[0]
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
        gtl_point_cloud[i] = np.array([butterfly[i][0], butterfly[i][1], 10.0])

    # np.random.shuffle(gtl_point_cloud)

    processes = []
    shared_arrays = []
    shared_mems = []
    for i in range(count):
        # if i == 2:
        shm = shared_memory.SharedMemory(create=True, size=sample.nbytes)
        shared_array = np.ndarray(sample.shape, dtype=sample.dtype, buffer=shm.buf)
        shared_array[:] = sample[:]
        # print(shared_array)
        shared_arrays.append(shared_array)
        shared_mems.append(shm)
        p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], np.array([0, 0, 0]), shm.name, None)
        p.start()
        processes.append(p)
        # else:
        #     p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], np.array([0, 0, 0]), None, None)
        #     p.start()
        #     processes.append(p)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    server_sock.bind(Constants.SERVER_ADDRESS)
    fin_message_sent = False
    final_point_cloud = np.zeros([count, 3])
    fin_processes = np.zeros(count)
    flight_path = {}

    # utils.plot_point_cloud(gtl_point_cloud, None)

    # press_enter_to_proceed()
    # barrier.wait()

    compute_hd(shared_arrays, gtl_point_cloud)

    num_round = 0
    max_rounds = Config.NUMBER_ROUND
    round_time = [(time.time(), num_round)]

    while True:
        data, _ = server_sock.recvfrom(2048)
        msg = pickle.loads(data)

        if msg.type == MessageTypes.FIN and not fin_message_sent:
            num_round += 1
            round_time.append((time.time(), num_round))
            if num_round < max_rounds:
                msg_type = MessageTypes.THAW_SWARM
            else:
                msg_type = MessageTypes.STOP
                fin_message_sent = True

            server_message = Message(msg_type).from_server().to_all()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            sock.sendto(pickle.dumps(server_message), Constants.BROADCAST_ADDRESS)
            sock.close()
            continue

        final_point_cloud[msg.fid - 1] = msg.el
        flight_path[msg.fid - 1] = msg.args[0]
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

    with open(f'packets{num_round}.txt', 'w') as f:
        for key, value in flight_path.items():
            f.write(f"{key} {value['bytes_sent']} {value['bytes_received']}")
            f.write("\n")

    # print(final_point_cloud)
    # for a in shared_arrays:
    #     print(a)

    for s in shared_mems:
        s.close()
        s.unlink()

    print('\n'.join([f'{a[0]} {a[1]}' for a in hds]))
    print('\n'.join([f'{b[0]} {b[1]}' for b in round_time]))
    # print(f"hd: {utils.hausdorff_distance(final_point_cloud, gtl_point_cloud)}")
    # print(final_point_cloud)
    # print(flight_path)

    # utils.plot_point_cloud(final_point_cloud, None)

    # print(flight_path)
    # print(flight_path.values())
    # print("writing bag file...")
    # import bag
    #
    # msgs = [bag.generate_msg_flight_path(path) for path in flight_path.values()]
    # bag.write_msgs_bag(msgs, 'test.bag')

    # bag = rosbag.Bag('test.bag')
    # for topic, msg, t in bag.read_messages(topics=['topic']):
    #     print(msg)
    # bag.close()

    # shm.close()
    # shm.unlink()
