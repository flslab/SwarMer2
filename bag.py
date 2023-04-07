# https://github.com/rospypi/simple

import rosbag
from flyinglightspeck.msg import FLSLHD, FLSElt, FLSDuration, FLSRGBA

#
# if __name__ == '__main__':
#     bag = rosbag.Bag('test.bag', 'w')
#
#     try:
#         s = FLSLHD()
#         s.l = 1
#         s.h = 2
#         s.d = 3
#
#         s2 = FLSDuration()
#         s2.start = 1
#         s2.end = 2
#
#         bag.write('topic', s)
#         bag.write('topic', s2)
#     finally:
#         bag.close()
#
#     bag = rosbag.Bag('test.bag')
#     for topic, msg, t in bag.read_messages(topics=['topic']):
#         print(topic, t, msg._type)
#     bag.close()


def write_msgs_bag(msgs, output_path):
    bag = rosbag.Bag(output_path, 'w')

    try:
        for msg in msgs:
            bag.write('topic', msg)
    finally:
        bag.close()


def generate_msg_flight_path(location_history):
    fls_elt = FLSElt()

    fls_elt.whatispresent = []
    fls_elt.coordinate = []
    fls_elt.duration = []
    fls_elt.color = []

    last_duration = None
    for hist in location_history:
        coordinate = FLSLHD()
        coordinate.l = hist.value[0]
        coordinate.h = hist.value[1]
        coordinate.d = hist.value[2]
        duration = FLSDuration()
        if last_duration:
            duration.start = last_duration.end
        else:
            duration.start = int(hist.t)
        duration.end = int(hist.t)
        last_duration = duration
        fls_elt.whatispresent.append(1)
        fls_elt.coordinate.append(coordinate)
        fls_elt.duration.append(duration)

    return fls_elt
