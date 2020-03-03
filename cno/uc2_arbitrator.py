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
from uc2_daemon import get_kafka_producer, \
    write_kafka_uc2_vce, \
    write_kafka_uc2_cno

TS_VCE_1 = 0.0
TS_VCE_2 = 0.0
PROFILE = ["low", "standard", "high"]
RESET_THRESH = 10
BITS_IN_MB = 1000000.0
BITS_IN_KB = 1000.0

BW_REQ = True
BW_REQ_COUNT = 1
BW_REQ_THRESH = 5
BW_EXTRA = 20   #Mbps
BW_CAP = 150    #Mbps
BW_DEFAULT = 50 #Mbps
BW_CURRENT = BW_DEFAULT

BW_REDUCE_REQ = True
BW_REDUCE_REQ_COUNT = 1
BW_REDUCE_REQ_THRESH = 5
BW_REDUCE_OFFSET = 5*BITS_IN_MB

SLEEP_INTERVAL = 4.0

# vce[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
def calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca):
    if (capacity == 0):
        print("No active stream -> effective capacity is zero")
        return 0

    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB

    capacity = capacity * BITS_IN_MB
    tmp_ca = capacity - br_1 - br_2
    bg_traffic = abs(tmp_ca - ava_ca)
    effective_ca = capacity - bg_traffic
    print("ca[{0}] ava_ca[{1}] br1[{2}] "
          "br2[{3}] bg[{4}] eff_ca[{5}]".format(capacity, ava_ca, br_1, br_2,
                                                bg_traffic, effective_ca))
    return effective_ca

def find_optimal_br_single(split_ca):
    br = -1
    for i in range(len(VIDEO_BIT_RATE)):
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB > split_ca):
            index = 0 if i-1 < 0 else i-1
            br = index
            #
        if (i == len(VIDEO_BIT_RATE) - 1 and br == -1):
            br = i
    return br

def find_optimal_br(split_ca):
    br_pair = (-1, -1)
    for i in range(len(VIDEO_BIT_RATE)):
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB > split_ca[0] and br_pair[0] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (index, br_pair[1])
        if (VIDEO_BIT_RATE[i]*BITS_IN_KB> split_ca[1] and br_pair[1] == -1):
            index = 0 if i-1 < 0 else i-1
            br_pair = (br_pair[0], index)

        if (i == len(VIDEO_BIT_RATE) - 1 and br_pair[0] == -1):
            print("find_optimal_br -> ava_ca is higher than max bitrate for vce-1")
            br_pair = (i, br_pair[1])
        if (i == len(VIDEO_BIT_RATE) - 1 and br_pair[1] == -1):
            br_pair = (br_pair[0], i)
            print("find_optimal_br -> ava_ca is higher than max bitrate for vce-2")

    return br_pair

def simple_analysis(vce_1, vce_2):
    if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0):
        return "NO_STREAM"
    elif (float(vce_1[7]) == 0.0 and float(vce_2[7]) != 0.0):
        return "ONE_STREAM_VCE_2"
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) == 0.0):
        return "ONE_STREAM_VCE_1"
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) != 0.0):
        return "TWO_STREAMS"
    else:
        print("simple_analysis() - > **UNKNOWN**")
        return "UNKNOWN"
    
def update_real_split_ca(real_split_ca, capacity):
    freed_ca = 0
    total_ca = real_split_ca[0]+real_split_ca[1]
    max_br = VIDEO_BIT_RATE[len(VIDEO_BIT_RATE)-1] * BITS_IN_KB
    # vcheck ce-1 
    if (real_split_ca[0] > max_br):
        freed_ca += real_split_ca[0] - max_br
        real_split_ca = (max_br, real_split_ca[1])
    if (real_split_ca[1] > max_br):
        freed_ca += real_split_ca[1] - max_br
        real_split_ca = (real_split_ca[0], max_br)
    #
    if (real_split_ca[0] < max_br): # (new, old)
        real_split_ca = (real_split_ca[0]+freed_ca, real_split_ca[1])
        print("update_real_split_ca() -> vce-1 [{0}]".format(real_split_ca))
    elif (real_split_ca[1] < max_br): # (old, new)
        real_split_ca = (real_split_ca[0], real_split_ca[1]+freed_ca)
        print("update_real_split_ca() -> vce-2 [{0}]".format(real_split_ca))
    return real_split_ca

# profile: ["low", "standard", "high"]
# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:   [vce, ts, br_min, br_max, capacity]
def calculate_resources(vce_1, vce_2, bw_dist, counter, producer):
    print ("======================== calculate_resources ({0}) ========================".format(counter))

    ts = generate_timestamp()
    print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))

    # init profile to 0 if there is no streams else to actual video profile
    profile_1 = '0' if vce_1[7] == '0.0' else vce_1[5]
    profile_2 = '0' if vce_2[7] == '0.0' else vce_2[5]

    capacity = BW_CURRENT
    # capacity = (max (float(vce_1[7]), float(vce_2[7])))
    print("max capacity -> {0}".format(capacity))
    
    ava_ca = max(float(vce_1[6]), float(vce_2[6]))
    print("available capacity -> {0}Mbps".format(round(ava_ca/BITS_IN_MB, 2)))

    # If a vce doesn't have a stream we shouldn't consider it in our resource allocations
    dist = bw_dist[(profile_1, profile_2)] # this should be based on max capacity - background traffic
    print("available capacity to share -> vce-1({0}%) |-| vce-2({1}%)".format(dist[0], dist[1]))

    effective_ca = calculate_effective_capacity(vce_1, vce_2, capacity, ava_ca)
    br_1 = 0 if vce_1[7] == '0.0' else VIDEO_BIT_RATE[int(vce_1[2])] * BITS_IN_KB
    br_2 = 0 if vce_2[7] == '0.0' else VIDEO_BIT_RATE[int(vce_2[2])] * BITS_IN_KB
    real_usable_ca = effective_ca - br_1 - br_2
    real_split_ca = (br_1 + dist[0]*real_usable_ca/100.0, br_2+ dist[1]*real_usable_ca/100.0)
    print ("real_split_ca -> vce-1({0}) |-| vce-2({1})".format(real_split_ca[0], real_split_ca[1]))
    
    if (simple_analysis(vce_1, vce_2) == "TWO_STREAMS"):
        real_split_ca = update_real_split_ca(real_split_ca, capacity)
    
    real_split_br_max = find_optimal_br(real_split_ca)
    print("real_split_br_max -> vce-1({0}) |-| vce-2({1})".format(VIDEO_BIT_RATE[real_split_br_max[0]],
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

    res_1 = [1, ts, vce_1[3], str(vce_1_br_max), capacity] # vce_1[7] -> capacity
    res_2 = [2, ts, vce_2[3], str(vce_2_br_max), capacity] # vce_2[7] -> capacity

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

def reset_all(producer):
    global TS_VCE_1, TS_VCE_2
    print("reset_all()")
    f = open("uc2_current_state.log", "w")
    f.close()
    f = open("uc2_resource_dist.log", "w")
    f.close()
    TS_VCE_1 = 0.0
    TS_VCE_2 = 0.0
    vce_1 = ["1", "0", "0", "0", "0", "0", "0", "0.0"]
    vce_2 = ["2", "0", "0", "0", "0", "0", "0", "0.0"]
    write_kafka_uc2_cno(producer, "request", BW_DEFAULT)
    return vce_1, vce_2

def reset_current_state(vce_1, vce_2, producer):
    print("reser_current_state() -> TS_VCE_1[{0}]  TS_VCE_2[{1}]".format(TS_VCE_1, TS_VCE_2))

    if (TS_VCE_1 > RESET_THRESH and TS_VCE_2 > RESET_THRESH):
        return reset_all(producer)
    if (TS_VCE_1 > RESET_THRESH and float(vce_2[7]) == 0.0):
        return reset_all(producer)
    if (TS_VCE_2 > RESET_THRESH and float(vce_1[7]) == 0.0):
        return reset_all(producer)
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

# vce_1:[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:[0-1, 1-ts, 2-vce_1[3], 3-str(vce_1_br_max), 4-vce_1[7]]
def analysis_notifications(vce_1, vce_2, res_1, res_2, producer):
    global BW_REQ, BW_REQ_COUNT, BW_CURRENT
    global BW_REDUCE_REQ_COUNT, BW_REDUCE_REQ

    curr_bw = max(floor(float(vce_1[7])), floor(float(vce_2[7])))
    all_active = False
    
    if (float(vce_1[7]) == 0.0 and float(vce_2[7]) == 0.0):
        print("analysis -> NO active stream!")
        return res_1, res_2
    elif (float(vce_1[7]) == 0.0 and float(vce_2[7]) != 0.0):
        print("analysis -> ONE active session from vce_2...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) == 0.0):
        print("analysis -> ONE active session from vce_1...")
    elif (float(vce_1[7]) != 0.0 and float(vce_2[7]) != 0.0):
        all_active = True
        print("analysis -> TWO active sessions from vce_1 and vce_2...")
    #
    # vce_1:[0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
    # res_1:[0-1, 1-ts, 2-vce_1[3], 3-str(vce_1_br_max), 4-vce_1[7]]
    if (all_active and int(vce_1[3]) == int(res_1[3]) and int(vce_2[3]) == int(res_2[3])):
        if (int(vce_1[6]) == 0 or int(vce_2[6] == 0)): # ava_ca should be zero
            print("analysis -> session(s) operate at their minimum bitrate, "
                  "-> BW_REQ[{0}] BW_REQ_COUNT[{1}]".format(BW_REQ, BW_REQ_COUNT))
            BW_REQ_COUNT += 1
            if (BW_REQ_COUNT % 20 == 0):
                BW_REQ_COUNT = 1
                BW_REQ = True
                
            if (BW_REQ == True and BW_REQ_COUNT >= BW_REQ_THRESH):
                BW_REQ = False
                bw = float(curr_bw + BW_EXTRA)
                res_1[4] = str(bw)
                res_2[4] = str(bw)
                if (bw <= BW_CAP):
                    BW_CURRENT = bw
                    write_kafka_uc2_cno(producer, "request", bw)
    elif (all_active and int(vce_1[4]) == int(res_1[3]) and int(vce_2[4]) == int(res_2[3])):
        br_total = VIDEO_BIT_RATE[int(vce_1[4])]*BITS_IN_KB + VIDEO_BIT_RATE[int(vce_2[4])]*BITS_IN_KB #bps
        if (br_total < float(vce_1[6]) + BW_REDUCE_OFFSET): #bps
            bw = float(VIDEO_BIT_RATE[int(vce_1[4])] + VIDEO_BIT_RATE[int(vce_2[4])]) / BITS_IN_KB #mbps
            print("analysis -> More capacity is avaialble more than required -> "
                  "BW_REDUCE_REQ[{0}] BW_REDUCE_REQ_COUNT[{1}]".format(BW_REDUCE_REQ, BW_REDUCE_REQ_COUNT))
            BW_REDUCE_REQ_COUNT += 1
            if (BW_REDUCE_REQ_COUNT % 20 == 0):
                BW_REDUCE_REQ_COUNT = 1
                BW_REDUCE_REQ = True

            if (BW_REDUCE_REQ == True and BW_REDUCE_REQ_COUNT >= BW_REDUCE_REQ_THRESH):
                BW_REDUCE_REQ = False
                res_1[4] = str(bw) #mbps
                res_2[4] = str(bw) #mbps
                BW_CURRENT = bw
                write_kafka_uc2_cno(producer, "request", bw)
    else:
        print("analysis -> normal condition")
    return res_1, res_2

def main():
    counter = 0
    producer = get_kafka_producer()
    vce_1, vce_2 = reset_all(producer)
    bw_dist = generate_bw_dist()

    while True:
        counter += 1
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        vce_1, vce_2 = reset_current_state(vce_1, vce_2, producer)
        # print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        res_1, res_2 = calculate_resources(vce_1, vce_2, bw_dist, counter, producer)
        # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
        res_1, res_2 = analysis_notifications(vce_1, vce_2, res_1, res_2, producer)
        # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
        write_resource_alloc(res_1, res_2, producer)

        sleep(SLEEP_INTERVAL)

if __name__ == '__main__':
    main()
