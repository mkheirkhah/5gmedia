# Written by Morteza Kheirkhah [m.kheirkhah@ucl.ac.uk]
# Model-4 (lr-ca)(bg5)(sm0)(v+20)(bg+10)(bt10)(l450)

import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from time import sleep
import numpy as np
import tensorflow as tf
import a3c_cno_mks
from uc2_daemon import get_kafka_producer, write_kafka_uc2_exec
import argparse
from datetime import datetime

S_INFO = 3  # bit_rate, bytes_sent, loss_rate
S_LEN = 8  # take how many frames in the past
A_DIM = 10
ACTOR_LR_RATE = 0.0001
#CRITIC_LR_RATE = 0.001
#VIDEO_BIT_RATE = [4000, 8000, 12000, 20000, 40000, 45000]  # Kbps
#VIDEO_BIT_RATE  = [3000, 5000, 8000, 12000, 15000, 20000, 25000, 30000, 40000, 50000]
VIDEO_BIT_RATE = [5000, 6000, 7000, 8000, 9000, 10000, 11000, 15000, 19000, 20000]

M_IN_K = 1000.0
DEFAULT_QUALITY = 1
RANDOM_SEED = 42
RAND_RANGE = 1000
VCE = {1 : "06:00:cc:74:72:95", 2 : "06:00:cc:74:72:99"}

#rtmp://192.168.83.30/live/qoe
#NN_MODEL = './trained_models/mks_loss_1000.ckpt'
#NN_MODEL = './trained_models/mks_loss_45.ckpt'
#NN_MODEL = './trained_models/mks_loss_450_nosmth.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_1.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_loss_1000.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_l500.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_normal_l500.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_norm_l1000.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_bg_rand.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_3400.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_interval_1.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_l45.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_13000.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_l150_bg_in.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_652900.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_14900.ckpt'  # works
#NN_MODEL = './trained_models/nn_model_ep_29200.ckpt'  # works
#NN_MODEL = './trained_models/nn_model_ep_99200.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_9400.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_28000.ckpt' #model-4 (lr-ca)(bg4)(sm0)(v+20)(bg+10)(at10)/l225 [20-30]{laggy}
#NN_MODEL = './trained_models/nn_model_ep_27900.ckpt' #model-4 (lr-ca)(bg5)(sm0)(v+20)(bg+10)(bt10)/l225 [20-30]
#NN_MODEL = './trained_models/nn_model_ep_28100.ckpt' #works very well man! 20 < br < 30  
#NN_MODEL = './trained_models/nn_model_ep_22200.ckpt' #model-4 (lr-ca)(bg5)(sm0)(v+20)(bg+10)(bt10)/l350 [works!][20-30]
#NN_MODEL = './trained_models/nn_model_ep_22000.ckpt'
#NN_MODEL = './trained_models/nn_model_ep_20400.ckpt'  # [l250] 
#NN_MODEL = './trained_models/nn_model_ep_406500.ckpt' # [l450] 12<br<30 GOOD!

#NN_MODEL = './trained_models/nn_model_ep_48900_m4_bg5_v20_bg10_l150.ckpt' #[08<30][r3]
#NN_MODEL = './trained_models/nn_model_ep_28100_m4_bg5_v20_bg10_l225.ckpt' #[20<30][r4]
#NN_MODEL = './trained_models/nn_model_ep_22200_m4_bg5_v20_bg10_l350.ckpt' #[08<25][r5]
#NN_MODEL = './trained_models/nn_model_ep_24300_m4_bg5_v20_bg10_l450.ckpt' #[05<25][r5][some small loss]
#NN_MODEL = './trained_models/nn_model_ep_32500_m4_bg5_v20_bg10_l500.ckpt' #[05<25][r6][READY_1!]
#NN_MODEL = './trained_models/nn_model_ep_113800_m4_bg5_v20_bg10_l500.ckpt' #[05<25][r6][READY_2! more trained!]

#NN_MODEL = './trained_models/nn_model_ep_12800_m4_bg51_v20_bg10_l500_sm1.ckpt' #[<][rg][]
NN_MODEL = './trained_models/nn_model_ep_10800_m4_bg51_v20_bg10_l500_sm1.ckpt' #[5<11][rg6][Run during dry-run]
#NN_MODEL = './trained_models/nn_model_ep_40600_m4_bg51_v20_bg10_l500_sm1.ckpt' #[5<11][rg6][re-run dry-run more training]
#NN_MODEL = './trained_models/nn_model_ep_26800_m4_bg51_v20_bg10_l500_sm1.ckpt' #[<][rg][]

# After dry-run
#NN_MODEL = './trained_models/nn_model_ep_79000_m4_bg51_v20_bg10_l500_sm1.ckpt'  #[5<11][r5][ready f demo]
#NN_MODEL = './trained_models/nn_model_ep_48700_m4_bg51_v20_bg10_l500_sm1.ckpt'  #[5<11][r4][more training]
#NN_MODEL = './trained_models/nn_model_ep_639900_m4_bg51_v20_bg10_l500_sm1.ckpt' #[5<15][r1][more more training]


#NN_MODEL = './trained_models/nn_model_ep_22600_m4_bg5_v20_bg10_l500_ch100.ckpt' #[8<25][r4]
#NN_MODEL = './trained_models/nn_model_ep_130900_m4_bg5_v20_bg10_l500_ch20.ckpt' #[3<25][r5][very little varying]
#NN_MODEL = './trained_models/nn_model_ep_39600_m4_bg5_v20_bg10_l500_ch35.ckpt'  #[8<25][r4][]

#NN_MODEL = './trained_models/nn_model_ep_17700_m4_bg5_v10_bg00_l450.ckpt' #[5<20][r5][some small loss] Almost Perfect!
#NN_MODEL = './trained_models/nn_model_ep_22200_m4_bg5_v10_bg10_l450.ckpt' #[5<25][r6] Almost Perfect!
#NN_MODEL = './trained_models/nn_model_ep_22800_m4_bg5_v10_bg20_l450.ckpt' #[8<25][r4]


INTERVAL = 1.0
MBPS = 1000000.0
CAPACITY = 20000000.0

def extract_ts(line):
    extract = line[line.find("T") + 1:line.find("Z")]
    ts_list = extract.split(":")
    return ts_list


def compare_ts(ts_new, ts_cur):
    if ts_new[0] > ts_cur[0]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] > ts_cur[1]:
        return True
    elif ts_new[0] == ts_cur[0] and ts_new[1] == ts_cur[1] and ts_new[2] > ts_cur[2]:
        return True
    else:
        return False

def get_ts_dur(ts_new, ts_cur):
    hour   = float(ts_new[0]) - float(ts_cur[0])
    minite = float(ts_new[1]) - float(ts_cur[1])
    second = float(ts_new[2]) - float(ts_cur[2])
    total_seconds = hour*60*60 + minite*60 + second
    #print ("get_ts_dur() -> new_ts_dur[{0}]".format(total_seconds))
    return total_seconds

def cal_lr(ca_tx, ca_rx, ca_free):
    # when there is capacity, loss_rate is 0.0
    if (ca_free > 0.0 or ca_rx == 0.0):
        return 0.0
    
    lr = ca_rx - CAPACITY
    lr = 0.0 if lr < 0.0 else lr
    lr_frac = lr / float(ca_rx)
    
    # lr_diff = ca_rx - ca_tx
    # try:
    #     lr_frac = lr_diff / ca_rx
    # except Exception as ex:
    #     print(ex, "OK, let's set lr = 0.0")
    #     return 0.0

    # if lr_frac < 0:
    #     print("OK, lr_frac < 0: let's set it to lr_frac = 0.0")
    #     lr_frac = 0.0

    # print("cal_lr() -> ca_tx[{0}]Mbps  ca_rx[{1}]Mbps  (rx > tx)[{2}] lr_frac[{3}]"
    #       .format(ca_tx/MBPS, ca_rx/MBPS, (ca_rx > ca_tx), lr_frac))

    return lr_frac


def cal_ca(new_bytes_sent, last_bytes_sent, ts_dur):
    #ts_dur = get_ts_dur(ext_new_ts, ext_last_ts)
    diff_bs = float(new_bytes_sent) - float(last_bytes_sent)
    ca = float(diff_bs * 8) / ts_dur  # bps
    # print("cal_ca() -> new_bytes_sent [{0}] last_bytes_sent [{1}] diff_bs [{2}] ts_dur [{3}] ca [{4}]Mbps"
    #       .format(new_bytes_sent,
    #               last_bytes_sent,
    #               diff_bs,
    #               ts_dur,
    #               ca/MBPS))
    return ca

def get_last_kafka_msg():
    bs = 0.0
    ts = "T00:00:00.000000Z"
    br = 0.0
    lr = 0.0
    try:
        with open("uc2_read_from_kafka.log", "r") as ff:
            for line in ff:
                col = line.split()
                bs = col[0]
                ts = col[1]
                br = col[2]
                lr = 0.0
                print("get_last_kafka_msg() -> bs [{0}] br [{1}] ts [{2}] lr [{3}]"
                      .format(bs,
                              br,
                              ts,
                              lr))
    except Exception as ex:
        print(ex)
        print("The reader script that creates this file is not yet activated...!")
        f = open('uc2_read_from_kafka.log', 'w')
        f.close()
    return float(bs), ts, float(br), float(lr)


def read_kafka(last_bytes_sent, last_bytes_rcvd, last_lr, last_ts, last_ca):
    with open("uc2_read_from_kafka.log", "r") as ff:
        for line in ff:
            col = line.split()
            bs = col[0]
            ts = col[1]
            br = col[2]
            lr = 0.0

            if last_bytes_sent == 0.0 and last_bytes_rcvd == 0.0 \
               and last_lr == 0.0 and last_ts == "T00:00:00.000000Z":
                last_bytes_sent = bs
                last_ts = ts
                last_bytes_rcvd = br
                last_lr = lr
                print("read_kafka() -> 1st msg from Kafka: bs[{0}] br[{1}] ts[{2}] lr[{3}] last_ca[{4}]Mbps"
                      .format(last_bytes_sent, last_bytes_rcvd, last_ts, last_lr, last_ca / MBPS))

            ext_new_ts = extract_ts(line)
            ext_last_ts = extract_ts(last_ts)
            result = compare_ts(ext_new_ts, ext_last_ts)
            # print(result, ext_new_ts, ext_last_ts)
            
            if (result):
                ts_dur = get_ts_dur(ext_new_ts, ext_last_ts)
                #print("read_kafka() -> ts_dur [{0}]".format(ts_dur))
                
                ca_tx = cal_ca(bs, last_bytes_sent, ts_dur) #bps
                ca_rx = cal_ca(br, last_bytes_rcvd, ts_dur) #bps

                ca_free = CAPACITY - max(ca_rx, ca_tx)
                ca_free = 0.0 if ca_free < 0.0 else ca_free

                lr = cal_lr(ca_tx, ca_rx, ca_free) # 0 < lr < 1

                print("-> ca_free[{0}]Mbps | loss_rate[{1}]% | rx[{2}]Mbps | tx[{3}]Mbps | dur[{4}]s"
                      .format(round(ca_free/MBPS,3),
                              round(lr,6),
                              round(ca_rx/MBPS, 3),
                              round(ca_tx/MBPS, 3),
                              ts_dur))
                return bs, br, lr, ts, ca_free, 1

        # return last metrics
        #print("read_kafka() -> there is no messages in the Kafka to read...")
        return last_bytes_sent, last_bytes_rcvd, last_lr, last_ts, last_ca, 0

def bitrate_checker(vce, bit_rate, br_min, br_max, profile, priority):
    
    if (bit_rate < br_min):
        return br_min
    elif (bit_rate > br_max):
        return br_max
    return bit_rate

def init_cmd_params():
    parser = argparse.ArgumentParser(description='Parameters setting for use case 2 (UC2) of the 5G-MEDIA project.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     prog='rl_uc2',
                                     epilog="If you have any questions please contact "
                                     "Morteza Kheirkhah <m.kheirkhah@ucl.ac.uk>")
    parser.add_argument("--vce",      type=int,   default=1,     choices=[1, 2])
    parser.add_argument("--br_min",   type=int,   default=1,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--br_max",   type=int,   default=9,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--profile",  type=str,   default='sta', choices=['low', 'sta', 'pre'])
    parser.add_argument("--priority", type=int,   default=0,     choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    parser.add_argument("--ava_ca",   type=float, default=0.0)
    parser.add_argument("--capacity", type=float, default=20000000.0)
    args = parser.parse_args()

    # init parameters
    vce      = VCE[args.vce]
    br_min   = args.br_min
    br_max   = args.br_max
    profile  = args.profile
    priority = args.priority
    ava_ca   = args.ava_ca
    capacity = args.capacity
    return vce, br_min, br_max, profile, priority, ava_ca, capacity

def generate_timestamp():
    # now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    now = datetime.now().timestamp()
    return now

def advertise_current_state(vce, br, br_min, br_max, profile, priority, ava_ca, capacity):
    ts = generate_timestamp()
    message = str(list(VCE.keys())[list(VCE.values()).index(vce)]) + \
        "\t" + str(ts) + "\t" + str(br) + "\t" + str(br_min) + \
        "\t" + str(br_max) + "\t" + profile + "\t" + \
        str(ava_ca) + "\t" + str(capacity) + "\n"

    try:
        with open("uc2_current_state.log", "a") as ff:
            ff.write(message)
    except Exception as ex:
        print(ex)

def main():

    vce, br_min, br_max, profile, priority, ava_ca, capacity = init_cmd_params()
    print ("\n******************************************************************************"
           "\nvce [{0}]"
           "\nbr_min [{1}]"
           "\nbr_max [{2}]"
           "\nprofile [{3}]"
           "\npriority [{4}]"
           "\nava_ca [{5}]"
           "\ncapacity [{6}]"
           "\n******************************************************************************"
           .format(vce, br_min, br_max, profile, priority, ava_ca, capacity))

    # As session start up we need to inform the arbitator about this session's details
    advertise_current_state (vce, 0.0, br_min, br_max, profile, priority, ava_ca, capacity)

    np.random.seed(RANDOM_SEED)

    assert len(VIDEO_BIT_RATE) == A_DIM

    with tf.Session() as sess:

        actor = a3c_cno_mks.ActorNetwork(
            sess,
            state_dim=[S_INFO, S_LEN],
            action_dim=A_DIM,
            learning_rate=ACTOR_LR_RATE)

        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()  # save neural net parameters

        # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None:  # nn_model is the path to file
            saver.restore(sess, nn_model)
            print("\nThe offline trained model [{0}] is restored...".format(nn_model))

        bit_rate = DEFAULT_QUALITY
        last_bit_rate = bit_rate

        action_vec = np.zeros(A_DIM)
        action_vec[bit_rate] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]

        producer = get_kafka_producer()

        bytes_sent = 0.0
        bytes_rcvd = 0.0
        loss_rate = 0.0
        ts = "T00:00:00.000000Z"
        # ava_ca = 0.0
        # br_min = 0
        # br_max = 5
        # profile = "standard"
        # priority = 1
        # vce = 0

        bytes_sent, ts, bytes_rcvd, loss_rate, = get_last_kafka_msg()

        counter = 0
        while True:  # serve video forever
            counter += 1
            print("\n**** [{0}] ****".format(counter))

            while True:
                bytes_sent, bytes_rcvd, loss_rate, ts, ava_ca, result = \
                    read_kafka(bytes_sent, bytes_rcvd, loss_rate, ts, ava_ca)
                if (result):
                    break
                else:
                    sleep(INTERVAL)

            print("-> last_bit_rate[{0}]Mbps".format(VIDEO_BIT_RATE[last_bit_rate] / 1000.0))
            # print("new_bytes_sent[{0}] new_lr[{1}] new_ts[{2}] new_ava_ca[{3}]Mbps, last_bit_rate[{4}]"
            #       .format(bytes_sent,
            #               loss_rate,
            #               ts,
            #               ava_ca/MBPS,
            #               VIDEO_BIT_RATE[last_bit_rate]))

            # retrieve previous state
            if len(s_batch) == 0:
                state = [np.zeros((S_INFO, S_LEN))]
            else:
                state = np.array(s_batch[-1], copy=True)

            # dequeue history record
            state = np.roll(state, -1, axis=1)

            # last chunk bit rate (number)
            state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            # past chunk throughput (array) # video_chunk_size is measured in byte
            state[1, -1] = float(ava_ca / CAPACITY)  # bits/s -> megabytes/s
            # loss rate (array)
            state[2, -1] = float(loss_rate)  # loss_rate

            # print("states: bit_rate [{0}] ava_ca [{1}] loss_rate [{2}]"
            #       .format(state[0, -1], state[1, -1], state[2, -1]))

            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (
                action_cumsum >
                np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

            s_batch.append(state)
 
            # write new bit-rate to Kafka to be delivered to vCompression
            #if (last_bit_rate != bit_rate):
            print("-> new_bit_rate [{0}]Mbps"#" - last_bit_rate [{1}]Mbps"
                  .format(VIDEO_BIT_RATE[bit_rate]/1000.0,))
            #VIDEO_BIT_RATE[last_bit_rate]/1000.0))

            # Now time to check whether the decided bitrate is within our video quality profile
            new_bit_rate = bitrate_checker(vce, bit_rate, br_min, br_max, profile, priority)
            
            if (new_bit_rate != bit_rate):
                print ("old br [{0}] -> new br [{1}]".format(VIDEO_BIT_RATE[bit_rate], VIDEO_BIT_RATE[new_bit_rate]))
                bit_rate = new_bit_rate

            last_bit_rate = bit_rate
            write_kafka_uc2_exec(producer, VIDEO_BIT_RATE[bit_rate])

            advertise_current_state (vce, bit_rate, br_min, br_max, profile, priority, ava_ca, capacity)
    
            # sleep for an INTERVAL before begin reading from Kafka again
            sleep(INTERVAL)


if __name__ == '__main__':
    main()
