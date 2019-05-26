import os
import sys
os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
import tensorflow as tf
import load_trace
import a3c_cno_alt
import fixed_env_cno_alt as env


S_INFO = 3  # bit_rate, buffer_size, next_chunk_size, bandwidth_measurement(throughput and time), chunk_til_video_end
S_LEN = 8  # take how many frames in the past
A_DIM = 6
ACTOR_LR_RATE =  0.0001
CRITIC_LR_RATE = 0.001
VIDEO_BIT_RATE = [300,750,1200,1850,2850,4300]  # Kbps
BUFFER_NORM_FACTOR = 10.0
CHUNK_TIL_VIDEO_END_CAP = 48.0
M_IN_K = 1000.0
REBUF_PENALTY = 4.3  # 1 sec rebuffering -> 3 Mbps
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1  # default video quality without agent
RANDOM_SEED = 42
RAND_RANGE = 1000
LOG_FILE = './test_results/log_sim_rl'
TEST_TRACES = './cooked_test_traces/'
# log in format of time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward
NN_MODEL = sys.argv[1]

CNO_PARA_LOSS_RATE = 25 # weight used in reward function

def main():

    np.random.seed(RANDOM_SEED)

    assert len(VIDEO_BIT_RATE) == A_DIM

    all_cooked_time, all_cooked_bw, all_file_names = load_trace.load_trace(TEST_TRACES)

    net_env = env.Environment(all_cooked_time=all_cooked_time,
                              all_cooked_bw=all_cooked_bw)

    log_path = LOG_FILE + '_' + all_file_names[net_env.trace_idx]
    log_file = open(log_path, 'wb')
    #lf = open (LOG_FILE + "_plot", 'ab') #MKS
    
    with tf.Session() as sess:

        actor = a3c_cno_alt.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)

        critic = a3c_cno_alt.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN],
                                   learning_rate=CRITIC_LR_RATE)

        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()  # save neural net parameters

        # restore neural net parameters
        if NN_MODEL is not None:  # NN_MODEL is the path to file
            saver.restore(sess, NN_MODEL)
            print("***************************** Testing model restored.", NN_MODEL)

        mean_loss_rate_list = [] # MKS
        video_bit_rate_list = [] # MKS
        mean_throughput_trace_list = [] # MKS
        
        time_stamp = 0

        last_bit_rate = DEFAULT_QUALITY
        bit_rate = DEFAULT_QUALITY

        action_vec = np.zeros(A_DIM)
        action_vec[bit_rate] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]
        a_batch = [action_vec]
        r_batch = []
        entropy_record = []

        video_count = 0

        while True:  # serve video forever
            # the action is from the last decision
            # this is to make the framework similar to the real
            delay, sleep_time, buffer_size, rebuf, \
            video_chunk_size, next_video_chunk_sizes, \
            end_of_video, video_chunk_remain, \
            loss_rate, mean_loss_rate, mean_throughput_trace = \
                net_env.get_video_chunk(bit_rate)

            time_stamp += delay  # in ms
            time_stamp += sleep_time  # in ms

            video_bit_rate_list.append(VIDEO_BIT_RATE[bit_rate]) #MKS
            mean_loss_rate_list.append(mean_loss_rate) # MKS
            mean_throughput_trace_list.append(mean_throughput_trace) # MKS
            
            # reward is video quality - rebuffer penalty - smoothness
            #reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
            #         - REBUF_PENALTY * rebuf \
            #         - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #                                   VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K

            #******************** reward function for 5G-MEDIA *****************
            reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
                - CNO_PARA_LOSS_RATE * (loss_rate) \
                - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
                                          VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            #*******************************************************************

            r_batch.append(reward)

            last_bit_rate = bit_rate

            # log time_stamp, bit_rate, buffer_size, reward
            log_file.write(str(time_stamp / M_IN_K) + '\t' +
                           str(VIDEO_BIT_RATE[bit_rate]) + '\t' +
                           str(buffer_size) + '\t' +
                           str(rebuf) + '\t' +
                           str(video_chunk_size) + '\t' +
                           str(delay) + '\t' +
                           str(reward) + '\t' +
                           str(loss_rate) + '\t' +
                           str(mean_loss_rate * 8.0 / M_IN_K) + '\t' +  
                           str(video_count) + '\n')# B/s -> b/s -> Kb/s
            log_file.flush()

            # retrieve previous state
            if len(s_batch) == 0:
                state = [np.zeros((S_INFO, S_LEN))]
            else:
                state = np.array(s_batch[-1], copy=True)

            # dequeue history record
            state = np.roll(state, -1, axis=1)

            # this should be S_INFO number of terms
            # state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            # state[1, -1] = buffer_size / BUFFER_NORM_FACTOR  # 10 sec
            # state[2, -1] = float(video_chunk_size) / float(delay) / M_IN_K  # kilo byte / ms
            # state[3, -1] = float(delay) / M_IN_K / BUFFER_NORM_FACTOR  # 10 sec
            # state[4, :A_DIM] = np.array(next_video_chunk_sizes) / M_IN_K / M_IN_K  # mega byte
            # state[5, -1] = np.minimum(video_chunk_remain, CHUNK_TIL_VIDEO_END_CAP) / float(CHUNK_TIL_VIDEO_END_CAP)

            # this should be S_INFO number of terms
            state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            state[1, -1] = float(video_chunk_size) / float(delay) / M_IN_K  # kilo byte / ms
            state[2, -1] = loss_rate 

            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()

            # CNO - bitrate is the index of the max value in the action_prob vector
            #bit_rate = np.argmax(action_prob)

            # Note: we need to discretize the probability into 1/RAND_RANGE steps,
            # because there is an intrinsic discrepancy in passing single state and batch states

            s_batch.append(state)

            entropy_record.append(a3c_cno_alt.compute_entropy(action_prob[0]))

            if end_of_video:
                log_file.write('\n')
                log_file.close()

                # flush video bit rate and mean_loss_rate
                # lf.write(str(video_count) + '\t'+
                #          str(np.mean(video_bit_rate_list)) + '\t' + # kbps
                #          str(np.mean(mean_loss_rate_list) * 8.0 / M_IN_K) + '\t' +
                #          str(np.mean(mean_throughput_trace_list) * 8.0 / M_IN_K) + '\t' +
                #          '\n') 
                # lf.flush()
                # lf.close()
                #video_count += 1 # MKS - look down a few lines
                mean_loss_rate_list = [] #MKS
                video_bit_rate_list = [] #MKS
                mean_throughput_trace_list = [] # MKs
                assert(len(mean_loss_rate_list) == 0) # MKS

                last_bit_rate = DEFAULT_QUALITY
                bit_rate = DEFAULT_QUALITY  # use the default action here

                del s_batch[:]
                del a_batch[:]
                del r_batch[:]

                action_vec = np.zeros(A_DIM)
                action_vec[bit_rate] = 1

                s_batch.append(np.zeros((S_INFO, S_LEN)))
                a_batch.append(action_vec)
                entropy_record = []

                video_count += 1

                if video_count >= len(all_file_names):
                    break

                log_path = LOG_FILE + '_' + all_file_names[net_env.trace_idx]
                log_file = open(log_path, 'wb')
                #lf = open (LOG_FILE + "_plot", 'ab')  #MKS


if __name__ == '__main__':
    main()
