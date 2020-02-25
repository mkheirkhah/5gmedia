#################################################################################
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################
from math import floor
import argparse
from time import sleep
from datetime import datetime
from rl_uc2 import generate_timestamp
from rl_uc2 import VIDEO_BIT_RATE, VCE
from uc2_daemon import get_kafka_producer, write_kafka_uc2_vce

TS_VCE_1 = 0.0
TS_VCE_2 = 0.0
PROFILE = ["low", "standard", "high"]
RESET_THRESH = 6
# BW_UNIT = VIDEO_BIT_RATE[1] - VIDEO_BIT_RATE[0] # 6000 - 5000 = 1000 MBps
BITS_IN_MB = 1000000.0
BITS_IN_KB = 1000.0

# vce[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
def calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca):
    if (capacity == 0):
        print("No active stream -> effective capacity is zero")
        return 0

    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB
    # br_1 = 3000000.0 #VIDEO_BIT_RATE[br_1] * BITS_IN_KB
    # br_2 = 3000000.0 #VIDEO_BIT_RATE[br_2] * BITS_IN_KB

    capacity = capacity * BITS_IN_MB
    tmp_ca = capacity - br_1 - br_2
    bg_traffic = abs(tmp_ca - ava_ca)
    effective_ca = capacity - bg_traffic
    print("ca[{0}] ava_ca[{1}] br1[{2}] "
          "br2[{3}] bg[{4}] eff_ca[{5}]".format(capacity, ava_ca, br_1, br_2,
                                                bg_traffic, effective_ca))
    return effective_ca

def find_optimal_br(split_ca):
    br_pair = (-1, -1)
    for i in range(len(VIDEO_BIT_RATE)):
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB > split_ca[0] and br_pair[0] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (index, br_pair[1])
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB> split_ca[1] and br_pair[1] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (br_pair[0], index)
    return br_pair

# profile: ["low", "standard", "high"]
# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:   [vce, ts, br_min, br_max, capacity]
def calculate_resources(vce_1, vce_2, bw_dist, counter):
    print ("======================== calculate_resources ({0}) ========================".format(counter))

    ts = generate_timestamp()
    print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))

    # init profile to 0 if there is no streams else to actual video profile
    profile_1 = '0' if vce_1[7] == '0.0' else vce_1[5]
    profile_2 = '0' if vce_2[7] == '0.0' else vce_2[5]

    capacity = (max (float(vce_1[7]), float(vce_2[7])))
    print("max capacity -> {0}".format(capacity))

    ava_ca = max(float(vce_1[6]), float(vce_2[6]))
    # ava_ca_bw_unit = floor(ava_ca/(BW_UNIT*1000))
    print("available capacity -> {0}Mbps".format(round(ava_ca/1000000.0, 2)))

    # If a vce doesn't have a stream we shouldn't consider it in our resource allocations
    dist = bw_dist[(profile_1, profile_2)] # this should be based on max capacity - background traffic
    print("available capacity to share -> vce-1({0}%) |-| vce-2({1}%)".format(dist[0], dist[1]))

    effective_ca = calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca)
    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB
    real_usable_ca = effective_ca - br_1 - br_2
    real_split_ca = (br_1 + dist[0]*real_usable_ca/100.0, br_2+ dist[1]*real_usable_ca/100.0)
    print ("real_split_ca -> vce-1({0}) |-| vce-2({1})".format(real_split_ca[0], real_split_ca[1]))
    real_split_br_max = find_optimal_br(real_split_ca)
    print("rea_split_br_max -> vce-1({0}) |-| vce-2({1})".format(VIDEO_BIT_RATE[real_split_br_max[0]],
                                                                 VIDEO_BIT_RATE[real_split_br_max[1]]))
        
    # split_ca = (dist[0]*effective_ca/100.0, dist[1]*effective_ca/100.0)
    # print ("split_ca -> vce-1({0}) |-| vce-2({1})".format(split_ca[0], split_ca[1]))

    # split_br_max = find_optimal_br(split_ca)
    # print("split_br_max -> vce-1({0}) |-| vce-2({1})".format(VIDEO_BIT_RATE[split_br_max[0]],
    #                                                          VIDEO_BIT_RATE[split_br_max[1]]))

    # vce_1_br_max = split_br_max[0] if split_br_max[0] < int(vce_1[4]) else int(vce_1[4])
    # vce_2_br_max = split_br_max[1] if split_br_max[1] < int(vce_2[4]) else int(vce_2[4])

    vce_1_br_max = real_split_br_max[0] if real_split_br_max[0] < int(vce_1[4]) else int(vce_1[4])
    vce_2_br_max = real_split_br_max[1] if real_split_br_max[1] < int(vce_2[4]) else int(vce_2[4])

    res_1 = [1, ts, vce_1[3], str(vce_1_br_max), vce_1[7]]
    res_2 = [2, ts, vce_2[3], str(vce_2_br_max), vce_2[7]]

    return res_1, res_2

# res_x: [vce, ts, br_min, br_max, capacity]
def write_resource_alloc(res_1, res_2, producer):
    m_1 = "".join(str(e) + "\t" for e in res_1) + "\n"
    m_2 = "".join(str(e) + "\t" for e in res_2) + "\n"    
    try:
        with open("uc2_resource_dist.log", "a") as ff:
            if (float(res_1[4]) != 0.0):
                ff.write(m_1)
                write_kafka_uc2_vce(producer, res_1, VCE[res_1[0]], VIDEO_BIT_RATE) # for vce_1
                print ("res_1 -> {0}".format(res_1))
            if (float(res_2[4]) != 0.0):
                ff.write(m_2)
                write_kafka_uc2_vce(producer, res_2, VCE[res_2[0]], VIDEO_BIT_RATE) # for vce_2
                print ("res_2 -> {0}".format(res_2))
    except Exception as ex:
        print(ex)

def reset_all():
    global TS_VCE_1, TS_VCE_2
    f = open("uc2_current_state.log", "w")
    f.close()
    f = open("uc2_resource_dist.log", "w")
    f.close()
    TS_VCE_1 = 0.0
    TS_VCE_2 = 0.0
    vce_1 = ["1", "0", "0", "0", "0", "0", "0", "0.0"]
    vce_2 = ["2", "0", "0", "0", "0", "0", "0", "0.0"]
    return vce_1, vce_2

def reset_current_state(vce_1, vce_2):
    print("TS_VCE_1 -> {0}\nTS_VCE_2 -> {1}".format(TS_VCE_1, TS_VCE_2))
    
    if (TS_VCE_1 > RESET_THRESH and TS_VCE_2 > RESET_THRESH):
        return reset_all()
    if (TS_VCE_1 > RESET_THRESH and float(vce_2[7]) == 0.0):
        return reset_all()
    if (TS_VCE_2 > RESET_THRESH and float(vce_1[7]) == 0.0):
        return reset_all()    
    if (TS_VCE_1 > RESET_THRESH):
        vce_1[7] = "0.0"
    if (TS_VCE_2 > RESET_THRESH):
        vce_2[7] = "0.0"
    return vce_1, vce_2

# [vce, ts, br, br_min, br_max, profile, ava_ca, capacity]
def read_current_state(vce_1, vce_2):
    global TS_VCE_1
    global TS_VCE_2
    try:
        with open("uc2_current_state.log", "r") as ff:
            for line in ff:
                col = line.split()
                if (int(col[0]) == int (vce_1[0])):   # vce_1
                    if (float(col[1]) > float(vce_1[1])):
                        vce_1 = col
                        TS_VCE_1 = 0.0
                    elif (float(col[1]) == float(vce_1[1])):
                        TS_VCE_1 += 1
                elif (int(col[0]) == int(vce_2[0])):  # vce_2
                    if (float(col[1]) > float(vce_2[1])):
                        vce_2 = col
                        TS_VCE_2 = 0.0
                    elif(float(col[1]) == float(vce_2[1])):
                        TS_VCE_2 += 1
        return vce_1, vce_2
    except Exception as ex:
        f = open('uc2_current_state.log', 'w')
        f.close()
        print(ex)
        return vce_1, vce_2

def generate_bw_dist():
    bw_dist = {}
    bw_dist[("high","high")] = (50,50)
    bw_dist[("high","standard")] = (75,25)
    bw_dist[("high","low")] = (100,0)
    bw_dist[("standard","high")] = (25,75)
    bw_dist[("standard","standard")] = (50,50)
    bw_dist[("standard","low")] = (100,0)
    bw_dist[("low","high")] = (0,100)
    bw_dist[("low","standard")] = (25,75)
    bw_dist[("low","low")] = (50,50)
    bw_dist[("high","0")] = (100, 0)
    bw_dist[("standard","0")] = (100,0)
    bw_dist[("low","0")] = (100,0)
    bw_dist[("0","high")] = (0, 100)
    bw_dist[("0","standard")] = (0, 100)
    bw_dist[("0","low")] = (0, 100)
    bw_dist[("0","0")] = (0, 0)

    return bw_dist

# res_1 =  [0-1, 1-ts, 2-vce_1[3], 3-str(vce_1_br_max), 4-vce_1[7]]
# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
def analysis_notifications(vce_1, vce_2, res_1, res_2):
    reduction_thresh = 1*BITS_IN_MB
    
    if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0):
        print("analysis -> NO active stream!")
        return
    elif (float(vce_1[7]) == 0.0 and float(vce_2[7]) != 0.0):
        print("analysis -> ONE active session from vce_2...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) == 0.0):
        print("analysis -> ONE active session from vce_1...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) != 0.0):
        print("analysis -> TWO active sessions from vce_1 and vce_2...")
    else:
        pass

    if (int(vce_1[3]) == int(res_1[3]) and int(vce_2[3]) == int(res_2[3])):
        if (int(vce_1[6]) == 0 or int(vce_2[6] == 0)): # ava_ca should be zero
            print("analysis -> session(s) operate at their minimum bitrate, "
                  "we probaly can ask O-CNO for extra badnwidth...")
    elif (int(vce_1[4]) == int(res_1[3]) and int(vce_2[4]) == int(res_2[3])):
        if (int(vce_1[4]) + int(vce_2[4]) < int(vce_1[6]) + reduction_thresh):
            # aggregate of the max bitrates are smaller then the ava_ca
            print("analysis -> session(s) can operate at their maximum bitrate, "
                  "we can either increase the quiality or "
                  "ask O-CNO to allocated less resource to this service...")
    else:
        print("analysis -> normal condition")


def main():
    producer = get_kafka_producer()
    counter = 0
    vce_1, vce_2 = reset_all()
    
    # bandwidth distribution policy
    bw_dist = generate_bw_dist()
    # print ("bw_dist -> {0}".format(bw_dist))
    
    while True:
        counter += 1
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        vce_1, vce_2 = reset_current_state(vce_1, vce_2)
        # print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        res_1, res_2 = calculate_resources(vce_1, vce_2, bw_dist, counter)
        # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
        write_resource_alloc(res_1, res_2, producer)
        analysis_notifications(vce_1, vce_2, res_1, res_2)
        sleep(4.0)

if __name__ == '__main__':
    main()
