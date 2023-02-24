import socket
import pickle
import time
import message
import worker

import numpy as np


if __name__ == '__main__':
    count = 2
    random_point_cloud = np.random.randint(10, size=(10, 3))
    # Create a list of processes
    processes = []
    for i in range(count):
        p = worker.WorkerProcess(i+1, random_point_cloud[i], random_point_cloud[i])
        p.start()
        processes.append(p)

    time.sleep(3)
    # Broadcast STOP message to processes
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    broadcast_address = ("<broadcast>", 5000)
    message = message.Message(message.MessageTypes.STOP).from_server().to_all()
    sock.sendto(pickle.dumps(message), broadcast_address)
    sock.close()
    time.sleep(1)

    # Wait for all worker processes to finish
    for p in processes:
        p.join()
