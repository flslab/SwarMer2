import socket
import pickle
import time
import message
from worker import WorkerProcess


if __name__ == '__main__':
    count = 10
    # Create a list of processes
    processes = []
    for i in range(count):
        p = WorkerProcess(i)
        p.start()
        processes.append(p)

    time.sleep(2)
    # Broadcast STOP message to processes
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    broadcast_address = ("<broadcast>", 5000)
    message = message.Message(message.MessageTypes.STOP, "Thank you worker")
    sock.sendto(pickle.dumps(message), broadcast_address)
    sock.close()
    time.sleep(1)

    # Wait for all worker processes to finish
    for p in processes:
        p.join()
