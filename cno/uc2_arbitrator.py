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
            ff.write(m_1)
            ff.write(m_2)
    except Exception as ex:
        print(ex)


# [vce, ts, br, br_min, br_max, profile, ava_ca, capacity]
def read_current_state(vce_1, vce_2):
    try:
        with open("uc2_current_state.log", "r") as ff:
            for line in ff:
                col = line.split()
                if (int(col[0]) == int (vce_1[0])):   # vce_1
                    if (float(col[1]) > float(vce_1[1])):
                        vce_1 = col
                elif (int(col[0]) == int(vce_2[0])):  # vce_2
                    if (float(col[1]) > float(vce_2[1])):
                        vce_2 = col
        return vce_1, vce_2
    except Exception as ex:
        print(ex)

def main():
    vce_1 = [1, 0.0]
    vce_2 = [2, 0.0]
    while True:
        vce_1, vce_2 = read_current_state(vce_1, vce_2)
        print ("vce_1 -> {0}\nvce_2 -> {1}".format(vce_1, vce_2))
        res_1, res_2 = calculate_resources(vce_1, vce_2)
        print ("res_1 -> {0}\nres_2 -> {1}".format(res_1, res_2))
        write_resource_alloc(res_1, res_2)
        sleep(4.0)

if __name__ == '__main__':
    main()
