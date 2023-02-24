import socket
import pickle
import worker

import numpy as np


if __name__ == '__main__':
    count = 3
    np.random.default_rng(1)
    gtl_point_cloud = np.random.randint(10, size=(count, 3))
    el_point_cloud = gtl_point_cloud + np.random.randint(2, size=(count, 3))
    print(gtl_point_cloud)
    print(el_point_cloud)

    # Create a list of processes
    processes = []
    for i in range(count):
        p = worker.WorkerProcess(count, i+1, gtl_point_cloud[i], el_point_cloud[i])
        p.start()
        processes.append(p)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.bind(("", 6000))
    fins = 0
    final_point_cloud = np.zeros([count, 3])
    while True:
        data, _ = sock.recvfrom(1024)
        msg = pickle.loads(data)
        final_point_cloud[fins] = msg.el
        fins += 1

        if fins == count:
            break

    print(final_point_cloud)

    # Wait for all worker processes to finish
    for p in processes:
        p.join()
