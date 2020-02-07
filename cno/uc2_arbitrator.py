import argparse
from time import sleep
from datetime import datetime

    
def process_current_state(vce_1, vce_2):
    try:
        with open("uc2_current_state.log", "r") as ff:
            for line in ff:
                col = line.split()
                if (int(col[0]) == int (vce_1[0])):   # vce_1
                    if (float(col[1]) > float(vce_1[1])):
                        vce_1 = col
                elif (int(col[0]) == int(vce_2[0])): # vce_2
                    if (float(col[1]) > float(vce_2[1])):
                        vce_2 = col
        print (vce_1)
        print (vce_2)
        return vce_1, vce_2
    except Exception as ex:
        print(ex)

def main():
    vce_1 = [1, 0.0]
    vce_2 = [2, 0.0]
    while True:
        vce_1, vce_2 = process_current_state(vce_1, vce_2)
        sleep(4.0)


if __name__ == '__main__':
    main()
