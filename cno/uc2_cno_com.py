#################################################################################
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
import os
import sys
import json
from kafka import KafkaConsumer, KafkaProducer
from uc2_settings import KAFKA_SERVER, \
    KAFKA_CLIENT_ID, \
    KAFKA_API_VERSION, \
    KAFKA_MONITORING_TOPICS, \
    KAFKA_EXECUTION_TOPIC
import csv
from pathlib import Path
from uc2_daemon import *

KAFKA_TOPIC = "uc2_cno"

def change_tm_bw(bw):
    print("change_tm_bw -> {0}".format(bw))
    os.system("sudo tc qdisc replace dev ens3 root tbf rate 20mbit burst 32kbit latency 400ms")
    os.system("sudo tc qdisc replace dev ifb0 root tbf rate 20mbit burst 32kbit latency 400ms")

def main():    
    consumer = get_kafka_consumer(KAFKA_TOPIC)
    print("Listening to kafka topic", KAFKA_MONITORING_TOPICS[KAFKA_TOPIC])
    bw = 0
    for msg in consumer:
        if (msg.value["sender"] == 'UC_2' and msg.value["receiver"] == 'O-CNO' and msg.value["option"] == 'request'):
            print (msg.value)
            bw = msg.value["resource"]["bw"]

        if bw > 0:
            change_tm_bw(bw)
            bw = 0
            f = open('uc2_cno_com.log', 'a')
            f.write(str(msg))
            f.write('\n')
            f.close()
            
if __name__ == '__main__':
    main()
