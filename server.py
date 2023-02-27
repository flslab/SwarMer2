import socket
import pickle
import time

import worker
import utils
from message import Message, MessageTypes

import numpy as np


if __name__ == '__main__':
    count = 10
    np.random.default_rng(1)
    gtl_point_cloud = np.random.randint(10, size=(count, 3))
    el_point_cloud = gtl_point_cloud + np.random.randint(2, size=(count, 3))
    print(gtl_point_cloud)

    # Create a list of processes
    processes = []
    for i in range(count):
        p = worker.WorkerProcess(count, i+1, gtl_point_cloud[i], el_point_cloud[i])
        p.start()
        processes.append(p)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    server_sock.bind(("", 6000))
    fins = -1
    final_point_cloud = np.zeros([count, 3])

    while True:
        data, _ = server_sock.recvfrom(1024)
        msg = pickle.loads(data)

        if msg.type == MessageTypes.FIN:
            fins += 1

        if fins == 0:
            stop_message = Message(MessageTypes.STOP).from_server().to_all()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            broadcast_address = ("<broadcast>", 5000)
            sock.sendto(pickle.dumps(stop_message), broadcast_address)
            sock.close()
            continue

        final_point_cloud[msg.fid - 1] = msg.el

        if fins == count:
            break

    server_sock.close()

    print(final_point_cloud)
    print(utils.hausdorff_distance(final_point_cloud, gtl_point_cloud))
    # utils.plot_point_cloud(final_point_cloud)

    # Wait for all worker processes to finish
    for p in processes:
        p.join()
