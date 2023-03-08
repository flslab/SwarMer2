import socket
import pickle
import worker
import utils
from config import Config
from constants import Constants
from message import Message, MessageTypes
import numpy as np


if __name__ == '__main__':
    count = Config.NUMBER_POINTS
    np.random.default_rng(1)
    gtl_point_cloud = np.random.randint(10, size=(count, 3))
    el_point_cloud = gtl_point_cloud + np.random.randint(2, size=(count, 3))

    processes = []
    for i in range(count):
        p = worker.WorkerProcess(count, i + 1, gtl_point_cloud[i], el_point_cloud[i])
        p.start()
        processes.append(p)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    server_sock.bind(Constants.SERVER_ADDRESS)
    fin_message_sent = False
    final_point_cloud = np.zeros([count, 3])
    fin_processes = np.zeros(count)

    while True:
        data, _ = server_sock.recvfrom(1024)
        msg = pickle.loads(data)

        if msg.type == MessageTypes.FIN and not fin_message_sent:
            stop_message = Message(MessageTypes.STOP).from_server().to_all()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.2)
            sock.sendto(pickle.dumps(stop_message), Constants.BROADCAST_ADDRESS)
            sock.close()
            fin_message_sent = True

        final_point_cloud[msg.fid - 1] = msg.el
        fin_processes[msg.fid - 1] = 1

        if np.sum(fin_processes) == count:
            break

    server_sock.close()

    print(final_point_cloud)
    print(utils.hausdorff_distance(final_point_cloud, gtl_point_cloud))
    # utils.plot_point_cloud(final_point_cloud)

    for p in processes:
        p.join()
