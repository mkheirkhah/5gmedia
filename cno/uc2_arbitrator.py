#################################################################################
# Author:      Morteza Kheirkhah
# Institution: University College London (UCL), UK
# Email:       m.kheirkhah@ucl.ac.uk
# Homepage:    http://www.uclmail.net/users/m.kheirkhah/
#################################################################################

import argparse
from time import sleep
from datetime import datetime
from rl_uc2 import generate_timestamp

TS_VCE_1 = 0.0
TS_VCE_2 = 0.0

# Profile: ["low", "standard", "high"]
# vce_1: [vce, ts, br, br_min, br_max, profile, ava_ca, capacity]
# res_1: [vce, ts, br_min, br_max, capacity]
def calculate_resources(vce_1, vce_2):
    ts = generate_timestamp()
    res_1 = [1, ts, 0, 5, vce_1[7]]
    res_2 = [2, ts, 5, 9, vce_2[7]]
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

    if (TS_VCE_1 > 5 and TS_VCE_2 > 5):
        return reset_all()
    if (TS_VCE_1 > 5 and float(vce_2[7]) == 0.0):
        return reset_all()
    if (TS_VCE_2 > 5 and float(vce_1[7]) == 0.0):
        return reset_all()
    
    if (TS_VCE_1 > 5):
        vce_1[7] = "0.0"
    if (TS_VCE_2 > 5):
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

def main():
    vce_1, vce_2 = reset_all()
    while True:
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        vce_1, vce_2 = reset_current_state(vce_1, vce_2)
        print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        res_1, res_2 = calculate_resources(vce_1, vce_2)
        # print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2));
        write_resource_alloc(res_1, res_2)
        sleep(4.0)

if __name__ == '__main__':
    main()
