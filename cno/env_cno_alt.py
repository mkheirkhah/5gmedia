import numpy as np

MILLISECONDS_IN_SECOND = 1000.0
B_IN_MB = 1000000.0
BITS_IN_BYTE = 8.0
RANDOM_SEED = 42
VIDEO_CHUNCK_LEN = 4000.0  # millisec, every time add this amount to buffer
BITRATE_LEVELS = 6
TOTAL_VIDEO_CHUNCK = 499
FRAME_INTERVAL = 50 #50  # frame
BUFFER_THRESH = 60.0 * MILLISECONDS_IN_SECOND  # millisec, max buffer limit
DRAIN_BUFFER_SLEEP_TIME = 500.0  # millisec
PACKET_PAYLOAD_PORTION = 0.95
LINK_RTT = 80  # millisec
PACKET_SIZE = 1500  # bytes
NOISE_LOW = 0.9
NOISE_HIGH = 1.1
VIDEO_SIZE_FILE = './video_size_'

VIDEO_BIT_RATE = [3855, 7551, 11244, 18740, 37480, 56220]  # Kbps
#VIDEO_BIT_RATE = [300,750,1200,1850,2850,4300]  # Kbps # MKS
CNO_RAND_MAX = 50000000 / 8.0  #Mbytes/s
CNO_RAND_MIN = 1000000 / 8.0  #Mbytes/s

ALGO = {0: "REAL", 1: "UNIFORM", 2: "NORMAL", 3: "SAWTHOOTH", 4: "NORM_BIT"}

TRAFFIC_MODEL = ALGO[0]

CNO_AC_MIN = 1 / 0.8
CNO_AC_MAX = 101000000 / 0.8
CNO_AC_STEP = 10


class Environment:
    def __init__(self, all_cooked_time, all_cooked_bw,
                 random_seed=RANDOM_SEED):
        assert len(all_cooked_time) == len(all_cooked_bw)

        np.random.seed(random_seed)

        self.all_cooked_time = all_cooked_time
        self.all_cooked_bw = all_cooked_bw

        self.video_chunk_counter = 0
        self.buffer_size = 0

        self.available_capacity = CNO_AC_MIN
        self.available_capacity_mode = 1

        # pick a random trace file
        self.trace_idx = np.random.randint(len(self.all_cooked_time))
        self.cooked_time = self.all_cooked_time[self.trace_idx]
        self.cooked_bw = self.all_cooked_bw[self.trace_idx]

        # randomize the start point of the trace
        # note: trace file starts with time 0
        self.mahimahi_ptr = np.random.randint(1, len(self.cooked_bw))
        self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

        self.video_size = {}  # in bytes
        for bitrate in range(BITRATE_LEVELS):
            self.video_size[bitrate] = []
            with open(VIDEO_SIZE_FILE + str(bitrate)) as f:
                for line in f:
                    self.video_size[bitrate].append(
                        (int(line.split()[0]), float(line.split()[1])))

    def get_video_size(self, quality):
        video_chunk_size = self.video_size[quality][self.video_chunk_counter][
            0]  # equal to frame's size
        video_chunk_br = self.video_size[quality][self.video_chunk_counter][
            1]  # equal to frame's bit_rate
        self.video_chunk_counter += 1  # to keep track of chunks/frames globally
        return video_chunk_size, \
            video_chunk_br

    def get_throughput(self):
        assert (CNO_AC_MAX > CNO_AC_MIN)
        slop = CNO_AC_MAX / CNO_AC_STEP

        if (self.available_capacity_mode == 1):
            self.available_capacity += slop
            if (self.available_capacity > CNO_AC_MAX):
                self.available_capacity -= slop
                self.available_capacity_mode = 0
            if (self.available_capacity == CNO_AC_MAX):
                self.available_capacity_mode = 0
        elif (self.available_capacity_mode == 0):
            self.available_capacity -= slop
            if (self.available_capacity < CNO_AC_MIN):
                self.available_capacity += slop
                self.available_capacity_mode = 1
            if (self.available_capacity == CNO_AC_MIN):
                self.available_capacity_mode = 1
        #print(self.available_capacity, self.available_capacity_mode)

    def get_video_chunk(self, quality):
        assert quality >= 0
        assert quality < BITRATE_LEVELS
        # ------------------------------------------------------------------
        # print("GET_VIDEO_CHUNK({}), "
        #       "last_quality[{}], "
        #       "video_chunk_counter[{}], "
        #       "TOTAL_VIDEO_CHUNCK[{}]").format(quality,
        #                                        self.last_quality,
        #                                        self.video_chunk_counter,
        #                                        TOTAL_VIDEO_CHUNCK)
        # ------------------------------------------------------------------
        video_chunk_size, video_chunk_br = self.get_video_size(quality)
        #print (quality, video_chunk_size, video_chunk_br)

        # use the delivery opportunity in mahimahi
        delay = 0.0  # in ms
        video_chunk_counter_sent = 0  # in bytes
        loss_rate = 0  # MKS
        loss_rate_list = []  # MKS
        loss_rate_frac_list = []  # MKS
        throughput_list = []  # MKS
        free_ca_list = []
        total_video_chunk_size = 0  # MKS
        frame_counter = 1  # MKS

        rand1 = np.random.randint(1, 15)
        rand2 = np.random.randint(1, len(VIDEO_BIT_RATE))

        while True:  # download video chunk over mahimahi
            throughput = self.cooked_bw[self.mahimahi_ptr] \
                         * B_IN_MB / BITS_IN_BYTE

            # if the following line is uncommented, it then overwrite the mahimahi throughput with a synthetic value
            if (TRAFFIC_MODEL) == "UNIFORM":
                throughput = np.random.randint(CNO_RAND_MIN, CNO_RAND_MAX)  # MKS - synthetic throughput
            elif (TRAFFIC_MODEL == "NORMAL"):
                throughput = np.random.normal(CNO_RAND_MAX, CNO_RAND_MAX / 10.0)
            elif (TRAFFIC_MODEL == "SAWTHOOTH"):
                self.get_throughput()
                throughput = self.available_capacity
            elif (TRAFFIC_MODEL == "REAL"):
                throughput *= rand1
            elif (TRAFFIC_MODEL == "NORM_BIT"):
                bitrate = (VIDEO_BIT_RATE[rand2] * 1000) / 8.0
                throughput = np.random.normal(bitrate, bitrate / 10.0)
                # if throughput < bitrate:
                #     print(bitrate, throughput)
            
            required_throughput = throughput  # Bytes/s
            #frame_throughput = video_chunk_br * 1000 / BITS_IN_BYTE  # Bytes/s
            
            frame_throughput = VIDEO_BIT_RATE[quality] * 1000 / BITS_IN_BYTE  # Bytes/s

            if (required_throughput > frame_throughput):
                required_throughput = frame_throughput

            duration = self.cooked_time[self.mahimahi_ptr] \
                - self.last_mahimahi_time

            #duration = 1 # MKS - overwrite mahimahi

            # we can't deliver more data than the frame_throughput alghough we may have more capacity
            if (required_throughput != throughput):
                packet_payload = required_throughput * duration * PACKET_PAYLOAD_PORTION
            else:
                packet_payload = throughput * duration * PACKET_PAYLOAD_PORTION

            # calculate mininum bit-rate needed for this chunk based on video quality
            # VIDEO_BIT_RATE is Kb/s # video_chunk_size is Bytes/s
            # minimum_video_chunk_rate = VIDEO_BIT_RATE[quality] * 1000 / BITS_IN_BYTE  # Bytes/s
            # minimum_video_chunk_rate = video_chunk_br *  1000 / BITS_IN_BYTE          # Bytes/s
            frame_loss_rate = frame_throughput - throughput  # Bytes/s
            frame_loss_rate = 0 if frame_loss_rate <= 0 else frame_loss_rate
            loss_rate_list.append(frame_loss_rate)  # add curr frame_loss_rate (bytes/s) to list
            assert (frame_loss_rate <= frame_throughput)
            loss_rate_frac_list.append(frame_loss_rate / float(frame_throughput))
            throughput_list.append(throughput)  # add curr available capacity (bytes/s) to list

            free_ca = throughput - frame_throughput
            free_ca = 0 if free_ca < 0 else free_ca
            free_ca_list.append(free_ca) # bytes/s
            
            assert (throughput >= 0)
            # ------------------------------------------------------------------
            # print (quality,\
            #        VIDEO_BIT_RATE[quality] / BITS_IN_BYTE, \
            #        "VBR", \
            #        minimum_video_chunk_rate / 1000, \
            #        "TH:", throughput / 1000, \
            #        " loss: ", frame_loss_rate / 1000,\
            #        "delay: ", delay)
            # ------------------------------------------------------------------
            if video_chunk_counter_sent + packet_payload > video_chunk_size:
                fractional_time = (video_chunk_size - video_chunk_counter_sent) / \
                                  required_throughput / PACKET_PAYLOAD_PORTION

                delay += fractional_time
                self.last_mahimahi_time += fractional_time
                assert (self.last_mahimahi_time <=
                        self.cooked_time[self.mahimahi_ptr])

                if (frame_counter < FRAME_INTERVAL):
                    frame_counter += 1  # a frame ends so start another one
                    video_chunk_counter_sent = 0  # prepare byte counter for the next frame
                    total_video_chunk_size += video_chunk_size  # keep total size of frames sent during a FRAME_INTERVAL
                    if (self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK):  # a chunk with several frames ends
                        break
                    video_chunk_size, video_chunk_br = self.get_video_size(quality)
                    continue
                else:
                    total_video_chunk_size += video_chunk_size  # keep total size of frame sent by end of FRAME_INTERVAL
                    break

            video_chunk_counter_sent += packet_payload
            delay += duration
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
            self.mahimahi_ptr += 1

            if self.mahimahi_ptr >= len(self.cooked_bw):
                # loop back in the beginning
                # note: trace file starts with time 0
                self.mahimahi_ptr = 1
                self.last_mahimahi_time = 0

        # exit while loop
        mean_loss_rate = np.mean(loss_rate_list)   # MKS - Bytes/s
        loss_rate = np.mean(loss_rate_frac_list)   # MKS - 0 <= loss_rate <= 1
        assert (loss_rate >= 0)                    # MKS
        mean_throughput = np.mean(throughput_list) # MKS - Bytes/s
        assert (mean_throughput >= 0)              # MKS
        mean_free_ca = np.mean(free_ca_list)       # MKS - Bytes/s
        # ------------------------------------------------------------------
        # print("quality[{}], "
        #       "frame_counter[{}], "
        #       "video_chunk_counter[{}], "
        #       "loss_list_size[{}], "
        #       "delay[{}], "
        #       "total_video_chunk_size[{}], "
        #       "mahimahi_ptr[{}]").format(quality,
        #                                  frame_counter,
        #                                  self.video_chunk_counter,
        #                                  len(loss_rate_list),
        #                                  delay,
        #                                  total_video_chunk_size,
        #                                  self.mahimahi_ptr)
        # ------------------------------------------------------------------
        delay *= MILLISECONDS_IN_SECOND
        delay += LINK_RTT

        # add a multiplicative noise to the delay
        delay *= np.random.uniform(NOISE_LOW, NOISE_HIGH)

        # rebuffer time
        rebuf = np.maximum(delay - self.buffer_size, 0.0)

        # update the buffer
        self.buffer_size = np.maximum(self.buffer_size - delay, 0.0)

        # add in the new chunk
        self.buffer_size += VIDEO_CHUNCK_LEN

        # sleep if buffer gets too large
        sleep_time = 0
        if self.buffer_size > BUFFER_THRESH:
            # exceed the buffer limit
            # we need to skip some network bandwidth here
            # but do not add up the delay
            drain_buffer_time = self.buffer_size - BUFFER_THRESH
            sleep_time = np.ceil(drain_buffer_time / DRAIN_BUFFER_SLEEP_TIME) * \
                         DRAIN_BUFFER_SLEEP_TIME
            self.buffer_size -= sleep_time

            while True:
                duration = self.cooked_time[self.mahimahi_ptr] \
                           - self.last_mahimahi_time
                if duration > sleep_time / MILLISECONDS_IN_SECOND:
                    self.last_mahimahi_time += sleep_time / MILLISECONDS_IN_SECOND
                    break
                sleep_time -= duration * MILLISECONDS_IN_SECOND
                self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
                self.mahimahi_ptr += 1

                if self.mahimahi_ptr >= len(self.cooked_bw):
                    # loop back in the beginning
                    # note: trace file starts with time 0
                    self.mahimahi_ptr = 1
                    self.last_mahimahi_time = 0

        # the "last buffer size" return to the controller
        # Note: in old version of dash the lowest buffer is 0.
        # In the new version the buffer always have at least
        # one chunk of video
        return_buffer_size = self.buffer_size

        #self.video_chunk_counter += 1
        video_chunk_remain = TOTAL_VIDEO_CHUNCK - self.video_chunk_counter
        end_of_video = False
        if self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK:
            end_of_video = True
            self.buffer_size = 0
            self.video_chunk_counter = 0
            # print("Video Ends with {} frame").format(self.video_chunk_counter)  #
            # pick a random trace file
            self.trace_idx = np.random.randint(len(self.all_cooked_time))
            self.cooked_time = self.all_cooked_time[self.trace_idx]
            self.cooked_bw = self.all_cooked_bw[self.trace_idx]

            # randomize the start point of the video
            # note: trace file starts with time 0
            self.mahimahi_ptr = np.random.randint(1, len(self.cooked_bw))
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

        next_video_chunk_sizes = []
        for i in range(BITRATE_LEVELS):
            next_video_chunk_sizes.append(
                self.video_size[i][self.video_chunk_counter])

        # video_chunk_size -> total_video_chunk_size
        return delay, \
            sleep_time, \
            return_buffer_size / MILLISECONDS_IN_SECOND, \
            rebuf / MILLISECONDS_IN_SECOND, \
            total_video_chunk_size, \
            next_video_chunk_sizes, \
            end_of_video, \
            video_chunk_remain, \
            loss_rate, \
            mean_loss_rate, \
            mean_throughput, \
            mean_free_ca
