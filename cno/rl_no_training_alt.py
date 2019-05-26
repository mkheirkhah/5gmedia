# Written by Morteza Kheirkhah [m.kheirkhah@ucl.ac.uk]

import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from time import sleep
import numpy as np
import tensorflow as tf
import a3c_cno_alt
from uc2_daemon import get_kafka_producer, write_kafka_uc2_exec

S_INFO = 3  # bit_rate, bytes_sent, loss_rate
S_LEN = 8  # take how many frames in the past
A_DIM = 10
ACTOR_LR_RATE = 0.0001
#CRITIC_LR_RATE = 0.001
#VIDEO_BIT_RATE = [4000, 8000, 12000, 20000, 40000, 45000]  # Kbps
VIDEO_BIT_RATE  = [3000, 5000, 8000, 12000, 15000, 20000, 25000, 30000, 40000, 50000]
M_IN_K = 1000.0
DEFAULT_QUALITY = 1
RANDOM_SEED = 42
RAND_RANGE = 1000

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
#NN_MODEL = './trained_models/nn_model_ep_28100.ckpt' # works very well man!
#NN_MODEL = './trained_models/nn_model_ep_22200.ckpt' # works well too
NN_MODEL  = './trained_models/nn_model_ep_22000.ckpt'

INTERVAL = 1.0
MBPS = 1000000.0
CAPACITY = 50000000.0

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

    print("cal_lr() -> ca_tx[{0}]Mbps  ca_rx[{1}]Mbps  (rx > tx)[{2}] lr_frac[{3}]"
          .format(ca_tx/MBPS, ca_rx/MBPS, (ca_rx > ca_tx), lr_frac))

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
                print("read_kafka() -> ts_dur [{0}]".format(ts_dur))
                
                ca_tx = cal_ca(bs, last_bytes_sent, ts_dur) #bps
                ca_rx = cal_ca(br, last_bytes_rcvd, ts_dur) #bps

                ca_free = CAPACITY - max(ca_rx, ca_tx)
                ca_free = 0.0 if ca_free < 0.0 else ca_free

                lr = cal_lr(ca_tx, ca_rx, ca_free) # 0 < lr < 1

                print("read_kafka() -> ca_free[{0}]Mbps  ca_rx[{1}]Mbps ca_tx[{2}]Mbps (rx > tx)[{3}] lr_frac[{4}]"
                      .format(ca_free/MBPS,
                              ca_rx/MBPS,
                              ca_tx/MBPS,
                              (ca_rx>ca_tx),
                              lr))
                return bs, br, lr, ts, ca_free, 1

        # return last metrics
        print ("read_kafka() -> there is no messages in the Kafka to read...")
        return last_bytes_sent, last_bytes_rcvd, last_lr, last_ts, last_ca, 0


def main():

    np.random.seed(RANDOM_SEED)

    assert len(VIDEO_BIT_RATE) == A_DIM

    with tf.Session() as sess:

        actor = a3c_cno_alt.ActorNetwork(
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
        ava_ca = 0.0

        bytes_sent, ts, bytes_rcvd, loss_rate,  = get_last_kafka_msg()
        
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
                
            print("new_bytes_sent[{0}] new_lr[{1}] new_ts[{2}] new_ava_ca[{3}]Mbps, last_bit_rate[{4}]"
                  .format(bytes_sent,
                          loss_rate,
                          ts,
                          ava_ca/MBPS,
                          VIDEO_BIT_RATE[last_bit_rate]))

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

            print("states: bit_rate [{0}] ava_ca [{1}] loss_rate [{2}]"
                  .format(state[0, -1], state[1, -1], state[2, -1]))

            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (
                action_cumsum >
                np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()
            
            s_batch.append(state)
 
            # write new bit-rate to Kafka to be delivered to vCompression
            if (last_bit_rate != bit_rate):
                print("new bit_rate: [{0}] last_bit_rate [{1}]"
                      .format(VIDEO_BIT_RATE[bit_rate],
                              VIDEO_BIT_RATE[last_bit_rate]))
                last_bit_rate = bit_rate
                write_kafka_uc2_exec(producer, VIDEO_BIT_RATE[bit_rate])

            # sleep for an INTERVAL before begin reading from Kafka again
            sleep(INTERVAL)


if __name__ == '__main__':
    main()
