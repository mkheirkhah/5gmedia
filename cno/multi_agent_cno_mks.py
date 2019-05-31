import os
import logging
import numpy as np
import multiprocessing as mp
os.environ['CUDA_VISIBLE_DEVICES']=''
import tensorflow as tf

import env_cno_mks
import a3c_cno_mks
import load_trace


S_INFO = 3  # bit_rate, buffer_size, next_chunk_size, bandwidth_measurement(throughput and time), chunk_til_video_end
S_LEN = 8  # take how many frames in the past
A_DIM = 10
ACTOR_LR_RATE =  0.0001
CRITIC_LR_RATE = 0.001
NUM_AGENTS = 2
#NUM_AGENTS = 1
TRAIN_SEQ_LEN = 100  # take as a train batch
MODEL_SAVE_INTERVAL = 100

#VIDEO_BIT_RATE  = [300,750,1200,1850,2850,4300]
#VIDEO_BIT_RATE  = [4000, 8000, 12000, 20000, 40000, 45000]
#VIDEO_BIT_RATE  = [3000, 5000, 8000, 12000, 15000, 20000, 25000, 30000, 40000, 50000]
VIDEO_BIT_RATE   = [5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 20000]
CNO_REWARD       = [1, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8] # dry-run
#CNO_REWARD       = [1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]

HD_REWARD = [1, 2, 3, 12, 15, 20]
BUFFER_NORM_FACTOR = 10.0
CHUNK_TIL_VIDEO_END_CAP = 48.0
M_IN_K = 1000.0
#REBUF_PENALTY = 4.3  # 1 sec rebuffering -> 3 Mbps
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1  # default video quality without agent
RANDOM_SEED = 42
RAND_RANGE = 1000
SUMMARY_DIR = './results'
LOG_FILE = './results/cno_log_alt'
TEST_LOG_FOLDER = './test_results/'
TRAIN_TRACES = './cooked_traces/'

#NN_MODEL = './results/pretrain_linear_reward.ckpt'
#NN_MODEL = './results/nn_model_ep_32500_m4_bg5_v20_bg10_l500.ckpt'
#NN_MODEL = './results/nn_model_ep_32500_m4_bg5_v20_bg10_l500.ckpt'
#NN_MODEL = './results/nn_model_ep_12800_m4_bg51_v20_bg10_l500_sm1.ckpt'
#NN_MODEL = './results/nn_model_ep_10800_m4_bg51_v20_bg10_l500_sm1.ckpt' #(Dry-run)

## [ready for actual demo... but let's train it a little bit more]
#NN_MODEL = './trained_models/nn_model_ep_79000_m4_bg51_v20_bg10_l500_sm1.ckpt' #[<][rg]
NN_MODEL = None

CNO_PARA_LOSS_RATE = 500 # weight used in reward function
#CNO_PARA_FREE_CA = 45

def testing(epoch, nn_model, log_file):
    # clean up the test results folder
    os.system('rm -r ' + TEST_LOG_FOLDER)
    os.system('mkdir ' + TEST_LOG_FOLDER)
    
    # run test script
    os.system('python rl_test_cno_alt.py ' + nn_model)
    
    # append test performance to the log
    rewards = []
    test_log_files = os.listdir(TEST_LOG_FOLDER)
    for test_log_file in test_log_files:
        reward = []
        with open(TEST_LOG_FOLDER + test_log_file, 'rb') as f:
            for line in f:
                parse = line.split()
                try:
                    reward.append(float(parse[-1]))
                except IndexError:
                    break
        rewards.append(np.sum(reward[1:]))

    rewards = np.array(rewards)

    rewards_min = np.min(rewards)
    rewards_5per = np.percentile(rewards, 5)
    rewards_mean = np.mean(rewards)
    rewards_median = np.percentile(rewards, 50)
    rewards_95per = np.percentile(rewards, 95)
    rewards_max = np.max(rewards)

    log_file.write(str(epoch) + '\t' +
                   str(rewards_min) + '\t' +
                   str(rewards_5per) + '\t' +
                   str(rewards_mean) + '\t' +
                   str(rewards_median) + '\t' +
                   str(rewards_95per) + '\t' +
                   str(rewards_max) + '\n')
    log_file.flush()


def central_agent(net_params_queues, exp_queues):

    assert len(net_params_queues) == NUM_AGENTS
    assert len(exp_queues) == NUM_AGENTS

    logging.basicConfig(filename=LOG_FILE + '_central',
                        filemode='w',
                        level=logging.INFO)

    with tf.Session() as sess, open(LOG_FILE + '_test', 'wb') as test_log_file:

        actor = a3c_cno_mks.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)
        critic = a3c_cno_mks.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN],
                                   learning_rate=CRITIC_LR_RATE)

        summary_ops, summary_vars = a3c_cno_mks.build_summaries()

        sess.run(tf.global_variables_initializer())
        writer = tf.summary.FileWriter(SUMMARY_DIR, sess.graph)  # training monitor
        saver = tf.train.Saver()  # save neural net parameters

        # restore neural net parameters
        nn_model = NN_MODEL
        if nn_model is not None:  # nn_model is the path to file
            saver.restore(sess, nn_model)
            print("Model restored.")

        epoch = 0

        # assemble experiences from agents, compute the gradients
        while True:
            # synchronize the network parameters of work agent
            actor_net_params = actor.get_network_params()
            critic_net_params = critic.get_network_params()
            for i in range(NUM_AGENTS):
                net_params_queues[i].put([actor_net_params, critic_net_params])
                # Note: this is synchronous version of the parallel training,
                # which is easier to understand and probe. The framework can be
                # fairly easily modified to support asynchronous training.
                # Some practices of asynchronous training (lock-free SGD at
                # its core) are nicely explained in the following two papers:
                # https://arxiv.org/abs/1602.01783
                # https://arxiv.org/abs/1106.5730

            # record average reward and td loss change
            # in the experiences from the agents
            total_batch_len = 0.0
            total_reward = 0.0
            total_td_loss = 0.0
            total_entropy = 0.0
            total_agents = 0.0 

            # assemble experiences from the agents
            actor_gradient_batch = []
            critic_gradient_batch = []

            for i in range(NUM_AGENTS):
                s_batch, a_batch, r_batch, terminal, info = exp_queues[i].get()

                actor_gradient, critic_gradient, td_batch = \
                    a3c_cno_mks.compute_gradients(
                        s_batch=np.stack(s_batch, axis=0),
                        a_batch=np.vstack(a_batch),
                        r_batch=np.vstack(r_batch),
                        terminal=terminal, actor=actor, critic=critic)

                actor_gradient_batch.append(actor_gradient)
                critic_gradient_batch.append(critic_gradient)

                total_reward += np.sum(r_batch)
                total_td_loss += np.sum(td_batch)
                total_batch_len += len(r_batch)
                total_agents += 1.0
                total_entropy += np.sum(info['entropy'])

            # compute aggregated gradient
            assert NUM_AGENTS == len(actor_gradient_batch)
            assert len(actor_gradient_batch) == len(critic_gradient_batch)
            # assembled_actor_gradient = actor_gradient_batch[0]
            # assembled_critic_gradient = critic_gradient_batch[0]
            # for i in range(len(actor_gradient_batch) - 1):
            #     for j in range(len(assembled_actor_gradient)):
            #             assembled_actor_gradient[j] += actor_gradient_batch[i][j]
            #             assembled_critic_gradient[j] += critic_gradient_batch[i][j]
            # actor.apply_gradients(assembled_actor_gradient)
            # critic.apply_gradients(assembled_critic_gradient)
            for i in range(len(actor_gradient_batch)):
                actor.apply_gradients(actor_gradient_batch[i])
                critic.apply_gradients(critic_gradient_batch[i])

            # log training information
            epoch += 1
            avg_reward = total_reward  / total_agents
            avg_td_loss = total_td_loss / total_batch_len
            avg_entropy = total_entropy / total_batch_len

            logging.info('Epoch: ' + str(epoch) +
                         ' TD_loss: ' + str(avg_td_loss) +
                         ' Avg_reward: ' + str(avg_reward) +
                         ' Avg_entropy: ' + str(avg_entropy))

            summary_str = sess.run(summary_ops, feed_dict={
                summary_vars[0]: avg_td_loss,
                summary_vars[1]: avg_reward,
                summary_vars[2]: avg_entropy
            })

            writer.add_summary(summary_str, epoch)
            writer.flush()

            if epoch % MODEL_SAVE_INTERVAL == 0:
                # Save the neural net parameters to disk.
                save_path = saver.save(sess, SUMMARY_DIR + "/nn_model_ep_" +
                                       str(epoch) + ".ckpt")
                logging.info("Model saved in file: " + save_path)
                # MKS - turn off testing
                # testing(epoch, 
                #     SUMMARY_DIR + "/nn_model_ep_" + str(epoch) + ".ckpt", 
                #     test_log_file)


def agent(agent_id, all_cooked_time, all_cooked_bw, net_params_queue, exp_queue):

    net_env = env_cno_mks.Environment(all_cooked_time=all_cooked_time,
                              all_cooked_bw=all_cooked_bw,
                              random_seed=agent_id)

    with tf.Session() as sess, open(LOG_FILE + '_agent_' + str(agent_id), 'w') as log_file, \
         open(LOG_FILE + '_agent_' + str(agent_id) + '_alt', 'w') as lf:
        
        actor = a3c_cno_mks.ActorNetwork(sess,
                                 state_dim=[S_INFO, S_LEN], action_dim=A_DIM,
                                 learning_rate=ACTOR_LR_RATE)
        critic = a3c_cno_mks.CriticNetwork(sess,
                                   state_dim=[S_INFO, S_LEN],
                                   learning_rate=CRITIC_LR_RATE)

        # initial synchronization of the network parameters from the coordinator
        actor_net_params, critic_net_params = net_params_queue.get()
        actor.set_network_params(actor_net_params)
        critic.set_network_params(critic_net_params)

        last_bit_rate = DEFAULT_QUALITY
        bit_rate = DEFAULT_QUALITY

        action_vec = np.zeros(A_DIM)
        action_vec[bit_rate] = 1

        s_batch = [np.zeros((S_INFO, S_LEN))]
        a_batch = [action_vec]
        r_batch = []
        entropy_record = []
        video_count = 1 # MKS
        mean_loss_rate_list = [] # MKS
        mean_lr_list = []
        video_bit_rate_list = [] # MKS
        #mean_throughput_trace_list = [] # MKS 
        #rebuf_max = 0
        time_stamp = 0

        BACKGROUND_TRAFFIC = [0,5,10,15,20,25,30,35,30,25,20,15,10,5,0]
        
        while True:  # experience video streaming forever
            index = video_count % len(BACKGROUND_TRAFFIC)
            background = BACKGROUND_TRAFFIC[index] * 1000000.0
            
            # the action is from the last decision
            # this is to make the framework similar to the real
            #delay, sleep_time, buffer_size, rebuf, \
            #video_chunk_size, mean_throughput_trace, \
            end_of_video, mean_loss_rate, mean_free_ca, mean_lr, mean_ca = \
                net_env.get_video_chunk(bit_rate, video_count, background)
            
            # time_stamp += delay  # in ms
            # time_stamp += sleep_time  # in ms

            video_bit_rate_list.append(VIDEO_BIT_RATE[bit_rate])
            mean_loss_rate_list.append(mean_loss_rate) # MKS
            mean_lr_list.append(mean_lr)
            #mean_throughput_trace_list.append(mean_throughput_trace) # MKS
            
            # if rebuf_max < (REBUF_PENALTY * rebuf):
            #     rebuf_max = (rebuf*REBUF_PENALTY)
            #     print (rebuf_max * REBUF_PENALTY)

            # #******************** reward function for 5G-MEDIA *****************
            reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
                - CNO_PARA_LOSS_RATE * mean_loss_rate \
                - SMOOTH_PENALTY * np.abs(CNO_REWARD[bit_rate] -
                                          CNO_REWARD[last_bit_rate])

            # -- linear reward --
            # #******************** reward function for 5G-MEDIA *****************
            # reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
            #     - CNO_PARA_LOSS_RATE * mean_loss_rate \
            #     # - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #     #                           VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            # #*******************************************************************
            # print("reward[{0}] br[{1}] lr[{2}] smooth[{3}]"
            #       .format(reward,
            #               VIDEO_BIT_RATE[bit_rate] / M_IN_K,
            #               CNO_PARA_LOSS_RATE * mean_loss_rate,
            #               SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #                                       VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K))

            
            # #******************** reward function for 5G-MEDIA *****************
            # reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
            #     - CNO_PARA_LOSS_RATE * mean_loss_rate \
            #     - CNO_PARA_FREE_CA * mean_free_ca  \
            #     - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #                               VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            # #*******************************************************************
            # print("reward[{0}] br[{1}] lr[{2}] smooth[{3}] free_ca[{4}]"
            #       .format(reward,
            #               VIDEO_BIT_RATE[bit_rate] / M_IN_K,
            #               CNO_PARA_LOSS_RATE * mean_loss_rate,
            #               SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #                                       VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K,
            #               CNO_PARA_FREE_CA * mean_free_ca))
            
            # reward is video quality - rebuffer penalty - smoothness
            #reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
            #         - REBUF_PENALTY * rebuf \
            #         - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
            #                                   VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K

            # -- log scale reward --
            # log_bit_rate = np.log(VIDEO_BIT_RATE[bit_rate] / float(VIDEO_BIT_RATE[-1]))
            # log_last_bit_rate = np.log(VIDEO_BIT_RATE[last_bit_rate] / float(VIDEO_BIT_RATE[-1]))

            # reward = log_bit_rate \
            #          - REBUF_PENALTY * rebuf \
            #          - SMOOTH_PENALTY * np.abs(log_bit_rate - log_last_bit_rate)

            # -- HD reward --
            # reward = HD_REWARD[bit_rate] \
            #          - REBUF_PENALTY * rebuf \
            #          - SMOOTH_PENALTY * np.abs(HD_REWARD[bit_rate] - HD_REWARD[last_bit_rate])
            r_batch.append(reward)

            last_bit_rate = bit_rate

            # retrieve previous state
            if len(s_batch) == 0:
                state = [np.zeros((S_INFO, S_LEN))]                                
            else:
                state = np.array(s_batch[-1], copy=True)

            # dequeue history record
            # shift the element to the left, move the first element to the end
            # this end value will be updated with the new one, make sure we always
            # keep the infirmation of the last 8 chunks.
            state = np.roll(state, -1, axis=1)
            
            # this should be S_INFO number of terms
            # last chunk bit rate (number)
            #state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            # current buffer size (number)
            #state[1, -1] = buffer_size / BUFFER_NORM_FACTOR  # 10 sec
            # past chunk throughput (array)
            #state[2, -1] = float(video_chunk_size) / float(delay) / M_IN_K  # kilo byte / ms
            # past chunk download time (array)
            #state[3, -1] = float(delay) / M_IN_K / BUFFER_NORM_FACTOR  # 10 sec
            # next chunk sizes (array)
            #state[4, :A_DIM] = np.array(next_video_chunk_sizes) / M_IN_K / M_IN_K  # mega byte
            # number of chunks left (number)
            #state[5, -1] = np.minimum(video_chunk_remain, CHUNK_TIL_VIDEO_END_CAP) / float(CHUNK_TIL_VIDEO_END_CAP)
            
            #***************************** states for CNO 5G-MEDIA *****************
            # last chunk bit rate (number)
            state[0, -1] = VIDEO_BIT_RATE[bit_rate] / float(np.max(VIDEO_BIT_RATE))  # last quality
            # past chunk throughput (array) # video_chunk_size is measured in byte
            #state[1, -1] = float(video_chunk_size) / float(delay) / M_IN_K  # kilo byte / ms
            #state[1, -1] = float(mean_throughput_trace) / 1000000 # Mega Bytes/s
            state[1, -1] = float(mean_free_ca)  #fraction
            # loss rate (array)
            state[2, -1] = float(mean_loss_rate)  #fraction

            ########
            # print("states: bit_rate [{0}] capacity [{1}] loss_rate [{2}]"
            #       .format(state[0, -1], state[1, -1], state[2, -1]))
            #***********************************************************************

            # compute action probability vector
            action_prob = actor.predict(np.reshape(state, (1, S_INFO, S_LEN)))
            action_cumsum = np.cumsum(action_prob)
            bit_rate = (action_cumsum > np.random.randint(1, RAND_RANGE) / float(RAND_RANGE)).argmax()
            #print("new bitrate [{0}] last_bit_rate [{1}]".format(bit_rate, last_bit_rate))

            # CNO - bitrate is the index of the max value in the action_prob vector
            #bit_rate = np.argmax(action_prob)

            # Note: we need to discretize the probability into 1/RAND_RANGE steps,
            # because there is an intrinsic discrepancy in passing single state and batch states

            entropy_record.append(a3c_cno_mks.compute_entropy(action_prob[0]))

            # log time_stamp, bit_rate, buffer_size, reward
            log_file.write(str(time_stamp) + '\t' +
                           str(VIDEO_BIT_RATE[bit_rate]) + '\t' +
                           # str(buffer_size) + '\t' +
                           # str(rebuf) + '\t' +
                           # str(video_chunk_size) + '\t' +
                           # str(delay) + '\t' +
                           str(reward) + '\t' +
                           # str(loss_rate) + '\t' +
                           str(mean_loss_rate * 8.0 / M_IN_K) + '\t' + # B/s -> b/s -> Kb/s
                           str(video_count) + '\n')
            log_file.flush()

            # report experience to the coordinator
            if len(r_batch) >= TRAIN_SEQ_LEN or end_of_video:
                exp_queue.put([s_batch[1:],  # ignore the first chuck
                               a_batch[1:],  # since we don't have the
                               r_batch[1:],  # control over it
                               end_of_video,
                               {'entropy': entropy_record}])

                # synchronize the network parameters from the coordinator
                actor_net_params, critic_net_params = net_params_queue.get()
                actor.set_network_params(actor_net_params)
                critic.set_network_params(critic_net_params)

                del s_batch[:]
                del a_batch[:]
                del r_batch[:]
                del entropy_record[:]

                log_file.write('\n')  # so that in the log we know where video ends

            # store the state and action into batches
            if end_of_video:
                # flush video bit rate and mean_loss_rate -----------------------------
                lf.write(str(video_count) + '\t'+
                         str(np.mean(video_bit_rate_list)) + '\t' + # kbps
                         str(np.mean(mean_loss_rate_list)) + '\t' + # fraction
                         str(np.mean(mean_lr_list) / M_IN_K) + '\t' + # actual loss #kbps
                         #str(np.mean(mean_throughput_trace_list) * 8.0 / M_IN_K) + '\t' +
                         '\n') 
                lf.flush()
                video_count += 1 # MKS
                mean_loss_rate_list = [] # MKS
                video_bit_rate_list = [] # MKS
                mean_lr_list = []
                #mean_throughput_trace_list = [] # MKS
                assert(len(mean_loss_rate_list) == 0) # MKS
                #---------------------------------------------------------------------
                last_bit_rate = DEFAULT_QUALITY
                bit_rate = DEFAULT_QUALITY  # use the default action here

                action_vec = np.zeros(A_DIM)
                action_vec[bit_rate] = 1

                s_batch.append(np.zeros((S_INFO, S_LEN)))
                a_batch.append(action_vec)

            else:
                s_batch.append(state)

                action_vec = np.zeros(A_DIM)
                action_vec[bit_rate] = 1
                a_batch.append(action_vec)


def main():

    np.random.seed(RANDOM_SEED)
    assert len(VIDEO_BIT_RATE) == A_DIM
    
    # create result directory
    if not os.path.exists(SUMMARY_DIR):
        os.makedirs(SUMMARY_DIR)

    # inter-process communication queues
    net_params_queues = []
    exp_queues = []
    for i in range(NUM_AGENTS):
        net_params_queues.append(mp.Queue(1))
        exp_queues.append(mp.Queue(1))

    # create a coordinator and multiple agent processes
    # (note: threading is not desirable due to python GIL)
    coordinator = mp.Process(target=central_agent,
                             args=(net_params_queues, exp_queues))
    
    coordinator.start()
    
    all_cooked_time, all_cooked_bw, _ = load_trace.load_trace(TRAIN_TRACES)
    agents = []
    
    for i in range(NUM_AGENTS):
        agents.append(mp.Process(target=agent,
                                 args=(i, all_cooked_time, all_cooked_bw,
                                       net_params_queues[i],
                                       exp_queues[i])))
    
    for i in range(NUM_AGENTS):
        agents[i].start()
    
    # wait unit training is done
    coordinator.join()

if __name__ == '__main__':
    main()
