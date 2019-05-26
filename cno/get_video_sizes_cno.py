# MKS

BITRATE_LEVELS = 6
BITRATE_LEVELS_2 = 6
TOTAL_VIDEO_FRAME = 500
VIDEO_PATH_2 = './irt/'

# vstats_ducks_take_off_0
for bitrate in xrange(BITRATE_LEVELS_2): # [0:3]
	with open('video_size_' + str(bitrate), 'wb') as f:
                if (bitrate > 3):
                        bitrate_name = 3
                else:
                        bitrate_name = bitrate
                with open (VIDEO_PATH_2 + 'vstats_ducks_take_off_'+ str(bitrate_name) + '.log', 'r') as r:
                        for line in r:
                                ll = line.split()
                                frame_size = int(ll[5])
                                frame_bitrate =float((ll[11].replace('kbits/s', '')).rstrip())
                                if (bitrate == 4): # 40M
                                        frame_size*=2
                                        frame_bitrate*=2
                                        f.write(str(frame_size)+'\t'+ str(frame_bitrate) + "\n")
                                elif (bitrate == 5): # 60M
                                        frame_size*=3
                                        frame_bitrate*=3
                                        f.write(str(frame_size)+'\t'+ str(frame_bitrate) + "\n")
                                else:
                                        f.write(str(frame_size)+'\t'+ str(frame_bitrate) + "\n")
