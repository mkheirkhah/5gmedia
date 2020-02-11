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
from rl_uc2 import VIDEO_BIT_RATE

TS_VCE_1 = 0.0
TS_VCE_2 = 0.0
PROFILE = ["low", "standard", "high"]
RESET_THRESH = 6
BW_UNIT = VIDEO_BIT_RATE[1] - VIDEO_BIT_RATE[0] # 6000 - 5000 = 1000 MBps
BITS_IN_MB = 1000000.0

# profile: ["low", "standard", "high"]
# vce_1:   [0-vce, 1-ts, 2-br, 3-br_min, 4-br_max, 5-profile, 6-ava_ca, 7-capacity]
# res_1:   [vce, ts, br_min, br_max, capacity]
def calculate_resources(vce_1, vce_2, bw_dist):
    print ("========================calculate_resources====================")

    ts = generate_timestamp()
    print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))

    # init profile 0 if there is no stream else actual video profile
    profile_1 = '0' if vce_1[7] == '0.0' else vce_1[5]
    profile_2 = '0' if vce_2[7] == '0.0' else vce_2[5]

    capacity = (max (float(vce_1[7]), float(vce_2[7])))
    print("max capacity -> {0}".format(capacity))

    # If a vce doesn't have a stream we shouldn't consider it in our resource allocations
    dist = bw_dist[(profile_1, profile_2)]
    print("available capacity to distribution -> vce-1({0}%) vce-2({1}%)".format(dist[0], dist[1]))

    ava_ca = max(float(vce_1[6]), float(vce_2[6]))
    ava_ca_bw_unit = floor(ava_ca/(BW_UNIT*1000))
    print("available capacity -> {0}Mbps - BW_UNIT[{1}]x".format(round(ava_ca/1000000.0,2), ava_ca_bw_unit))

    
    # diff_1 = VIDEO_BIT_RATE[int(vce_1[4])] -VIDEO_BIT_RATE[int(vce_1[2])]
    # diff_2 = VIDEO_BIT_RATE[int(vce_2[4])] -VIDEO_BIT_RATE[int(vce_2[2])]
    # print ("diff_1 -> {0}\ndiff_2 -> {1}".format(diff_1, diff_2))

    
    if (ava_ca_bw_unit < 0): # very small avaialble capacity
        pass
    else:
        pass

    if (profile_1 != '0' and profile_2 != '0'):
        # if (int(vce_1[2]) >= int(vce_1[3]) and int(vce_2[2] >= int(vce_2[3]))):
        #     if int(vce_1[2]) == int(vce_1[4]):
        #         pass
        #     if int(vce_2[2]) == int(vce_2[4]):
        #         pass
        # else:
        #     pass # we need to request from O-CNO for more bandwidth
        pass
    elif (profile_1 == '0' and profile_2 != '0'):
        pass
    elif (profile_2 == '0' and profile_1 != '0'):
        pass

    res_1 = [1, ts, vce_1[3], vce_1[4], vce_1[7]]
    res_2 = [2, ts, vce_2[3], vce_2[4], vce_2[7]]
    return res_1, res_2


# [vce, ts, br_min, br_max, capacity]
def write_resource_alloc(res_1, res_2):
    m_1 = "".join(str(e) + "\t" for e in res_1) + "\n"
    m_2 = "".join(str(e) + "\t" for e in res_2) + "\n"    
    try:
        with open("uc2_resource_dist.log", "a") as ff:
            if (float(res_1[4]) != 0.0):
                ff.write(m_1)
                print ("res_1 -> {0}".format(res_1));
            if (float(res_2[4]) != 0.0):
                ff.write(m_2)
                print ("res_2 -> {0}".format(res_2));
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

def main():
    vce_1, vce_2 = reset_all()

    # bandwidth distribution policy
    bw_dist = generate_bw_dist()
    # print ("bw_dist -> {0}".format(bw_dist))
    
    while True:
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        vce_1, vce_2 = reset_current_state(vce_1, vce_2)
        # print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        res_1, res_2 = calculate_resources(vce_1, vce_2, bw_dist)
        # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
        write_resource_alloc(res_1, res_2)
        sleep(4.0)

if __name__ == '__main__':
    main()
