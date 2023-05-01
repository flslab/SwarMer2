import socket
from message import Message, MessageTypes
from constants import Constants
import pickle


def stop_all():
    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    ser_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    ser_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ser_sock.settimeout(.2)

    stop_message = Message(MessageTypes.STOP).from_server().to_all()
    dumped_stop_msg = pickle.dumps(stop_message)
    ser_sock.sendto(dumped_stop_msg, Constants.BROADCAST_ADDRESS)
