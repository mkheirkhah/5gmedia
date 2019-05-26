from time import sleep
from uc2_daemon import *
from uc2_metric_generator import *
from datetime import *
import sys
import numpy as np
VALUE_DEFAULT = 1000000
VIDEO_BIT_RATE = [3855, 7551, 11244, 18740, 37480, 56220]  # kbps

try:
    value = sys.argv[1]
except Exception as ex:
    index = np.random.randint(0, len(VIDEO_BIT_RATE) - 1)
    value = VIDEO_BIT_RATE[index]
    print (ex, "-> No input from cmdd, then use the default value {0} {1} {2}".format(VALUE_DEFAULT, index, value))

#value = 10000
# temp = get_msg_temp_uc3()
# print("***", temp, type(temp))

try:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    tmp_metric = METRIC_TEMPLATE_UC2_EXEC
    metric = generate_metric_uc2_exec(value, now, tmp_metric)
    print("@@@@", metric)
    #print(metric["execution"])
    producer = get_kafka_producer()
    t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_exec"], metric)
    print(KAFKA_EXECUTION_TOPIC["uc2_exec"])
    result = t.get(timeout=60)
except Exception as ex:
    print (ex)

# try:
#     now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
#     tmp_metric = METRIC_TEMPLATE_UC2_CONF
#     metric = generate_metric_uc2_conf(value, now, tmp_metric)
#     print("@@@@", metric)
#     #print(metric["execution"])
#     producer = get_kafka_producer()
#     t = producer.send(KAFKA_EXECUTION_TOPIC["uc2_conf"], metric)
#     print(KAFKA_EXECUTION_TOPIC["uc2_conf"])
#     result = t.get(timeout=60)
# except Exception as ex:
#     print (ex)

    
def extract_ts(line):
    extract = line[line.find("T") + 1:line.find("Z")]
    ts_list = extract.split(":")
    return ts_list, extract


def compare_timestamps(ts_new, ts_cur):
    if ts_new[0] > ts_cur[0]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] > ts_cur[1]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] == ts_cur[
            1] and ts_new[2] > ts_cur[2]:
        return True
    else:
        return False


# cur_ts = "00:00:00.0000"
# with open("uc2_read_from_kafka.log", "r") as ff:
#     for line in ff:
#         ts_cur, ts_cur_extract = extract_ts(cur_ts)
#         ts_new, ts_new_extract = extract_ts(line)
#         result = compare_timestamps(ts_new, ts_cur)
#         print(result, ts_new_extract, ts_cur_extract)
#         cur_ts = ts_new_extract
#         sleep(1)

#
# import os

# from uc2_settings import KAFKA_MONITORING_TOPICS, KAFKA_EXECUTION_TOPIC, METRIC_TEMPLATE

# message = METRIC_TEMPLATE
# for key, value in message.items():
#     if (type(value) == dict):
#         print("key:", key)
#         for k, v in value.items():
#             print(k, v)
#             if (k == "metric"):
#                 print("metric:", v)
#                 v["name"] = "MORTEZA"
#                 print("metric:", v)

# print("\n")
# print(message.get("mano"))
# print(message["mano"])
# print("\n")
# print(message["mano"].get("vnf").get("id"))
# print(message["mano"]["vnf"]["id"])

#import uc2_settings, uc2_read_kafka, uc2_daemon
