# Installation of CNO for UC2

1. Install git and gnuplot

```
brew install git gnuplot (Mac users)
sudo apt install -y git gnuplot (Linux users)
```

2. Install a version of python if you do not have one. CNO should work
   with all python versions (I’ve tested it with v3.5, v3.6, v2.7)
   
```
[Mac users only]
brew install python3 [Python 3.7.4] OR brew install python@2 [Python 2.7]

[Linux users only]
sudo apt-get install zlib1g-dev
wget https://www.python.org/ftp/python/3.6.7/Python-3.6.7.tar.xz [Choose a release for Linux from https://www.python.org/downloads/source/]
tar -xvf Python-3.6.7.tar
cd Python-3.6.3
./configure
make
make install
python3.6 -V -> Python3.67rc1 [/usr/bin/local/python3.6]
```

3. Installs the following python packages afterwards via pip

``` 
pip install virtualenv virtualenvwrapper
```

4. Create a new virtualenv (e.g. for python3.5). Note that if do not
   want to use virtualenv, continue from item #6

``` 
which python3.5 -> e.g. /usr/bin/python3.5 that is related to the default python that comes with Ubuntu16.4
virtualenv --python=/usr/bin/python3.5 ~/virtualenv/py3.5 [Linux/Mac users only]
conda create -n py3.5 python=3.5 anaconda [Windows users only]
``` 

5. Activate your new python environment

``` 
source ~/virtualenv/py3.5 [Mac/Linux users only]
conda activate py3.5 [Windows users only]
``` 

6. Finally install essential packages for CNO

``` 
pip install tflearn tensorflow matplotlib [Mac/Linux/Windows]
```

7. Finally, clone the CNO source code from my GitHub. Make sure you
   are using "deployed" branch.

```
git clone -b deployed https://github.com/mkheirkhah/5gmedia.git
git branch [* deployed]
```


# Execution of CNO for UC2 at your laptop

* Executing code with default settings

``` 
python multi_agent_cno_mks.py
```

* To explore available parameters to change

``` 
python multi_agent_cno_mks.py --help
```

* To monitor parameters (e.g. loss, reward, entropy) during a training
session

```
tensorboard --logdir ./results
```

* For plotting mean loss-rate and mean video-bit-rate after a training
session is completed

```
python plot.py
```

# Execution of CNO for UC2 via terminal (to UMP servers)

1. First connect to the dedicated technical WiFi at UPM

``` 
WiFi SSID: 5GMEDIA_CD
WiFI Pass: 5G_MediaCD
```

2. Connect to one of the provided VM according to your group via SSH
   connection

``` 
ssh media5g@192.168.0.74 [Group 1]
ssh media5g@192.168.0.35 [Group 2]
ssh media5g@192.168.0.60 [Group 3]
ssh media5g@192.168.0.67 [Group 4]
ssh media5g@192.168.0.52 [Group 5]
ssh media5g@192.168.0.78 [Group 6]
ssh media5g@192.168.0.75 [Group 7]
ssh media5g@192.168.0.55 [Group 8]
ssh media5g@192.168.0.57 [Group 9]
```

3. Once you are connected to the VM

```
cd 5gmedia/cno
```

4. Executing code with default settings

``` 
python multi_agent_cno_mks.py
```

5. To explore available parameters to change

``` 
python multi_agent_cno_mks.py --help
```

6. To monitor parameters (e.g. loss, reward, entropy) during a
training session, ssh to your remote host through another terminal and
then run tensorboard

```
tensorboard --logdir ~/5gmedia/cno/results
```

7. After previous step return back to you local machine and open your
   browser and enter the following

``` 
REMOTE_HOST_IP:6006 [e.g. 192.168.0.75:6006 for group 7]
```

8. For plotting mean loss-rate and mean video-bit-rate after a
training session

```
mkdir ~/5g_results  [at your local machine, do it only once]
scp media5g@REMOTE_HOST_IP:~/5gmedia/cno/plot.py ~/5g_results [password: 5gmedia1, do it only once]
scp media5g@REMOTE_HOST_IP:~/5gmedia/cno/results/cno_log_alt_agent_0_alt ~/5g_results [do it anytime you wish]
python plot.py [at your local host, from ~/5g_results]
```

# Exercises

### Run CNO with default parameters

``` 1c-enterprise
python multi_agent_cno_mks.py 
```

### Increase the number of parallel agents from 1 to 4 (if possible, mainly depends on available CPUs)

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4
```

### Modifying alpha from 500 (default) to [50, 1000]

##### --alpha 50
``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --alpha 50
```

##### --alpha 1000

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --alpha 1000
```

### Analyzing learning rates for both actor and critic networks

##### --alr 0.01 --clr 0.1

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --alr 0.01 --clr 0.1
```

##### --alr 0.00001 --clr 0.0001

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --alr 0.00001 --clr 0.0001
```

### Reward function construction [bls, bl, b]

##### With bitrate and loss-rate only

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --r_func bl 
```

##### With bitrate only

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --r_func b
```

### Increase link capacity, dimension, background traffic model/shape

##### 
``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --br_auto 1 --bg_auto 1 --lc 50 --dim 20 --bg_shape sawtooth
```

##### 

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --br_auto 1 --bg_auto 1 --lc 50 --dim 20 --bg_shape random
```

### Manual configuration of bitrates, and then generate background traffic set automatically with the sawtooth shape

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --br 2000 4000 6000 8000 10000 --dim 5 --lc 15 --bg_auto 1 --bg_shape sawtooth
```

### Support bitrate of 1Mbps and automatically generate new bitrate set

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --br_low 1 --br_auto 1
```

### Increase link capacity from 20Mbps to 35Mbps

``` 1c-enterprise
python multi_agent_cno_mks.py --pa 4 --lc 35
```


# Live demo of CNO at Telefónica network

<iframe width="560" height="315" src="https://www.youtube.com/embed/2BToKr4jVAI" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>





<!-- Make sure actual video files are stored in
`video_server/video[1-6]`, then run --> <!-- ``` --> <!-- python
get_video_sizes --> <!-- ``` -->

<!-- Put training data in `sim/cooked_traces` and testing data in `sim/cooked_test_traces` (need to create folders). The trace format for simulation is `[time_stamp (sec), throughput (Mbit/sec)]`. Sample training/testing data we used can be downloaded separately from `train_sim_traces` and `test_sim_traces` in https://www.dropbox.com/sh/ss0zs1lc4cklu3u/AAB-8WC3cHD4PTtYT0E4M19Ja?dl=0. More details of data preparation can be found in `traces/`. -->

<!-- To train a model, run  -->
<!-- ``` -->
<!-- python multi_agent.py -->
<!-- ``` -->

<!-- As reported by the A3C paper (http://proceedings.mlr.press/v48/mniha16.pdf) and a faithful implementation (https://openreview.net/pdf?id=Hk3mPK5gg), we also found the exploration factor in the actor network quite crucial for achieving good performance. A general strategy to train our system is to first set `ENTROPY_WEIGHT` in `a3c.py` to be a large value (in the scale of 1 to 5) in the beginning, then gradually reduce the value to `0.1` (after at least 100,000 iterations).  -->


<!-- The training process can be monitored in `sim/results/log_test` (validation) and `sim/results/log_central` (training). Tensorboard (https://www.tensorflow.org/get_started/summaries_and_tensorboard) is also used to visualize the training process, which can be invoked by running -->
<!-- ``` -->
<!-- python -m tensorflow.tensorboard --logdir=./results/ -->
<!-- ``` -->
<!-- where the plot can be viewed at `localhost:6006` from a browser.  -->

<!-- Trained model will be saved in `sim/results/`. We provided a sample pretrained model with linear QoE as the reward signal. It can be loaded by setting `NN_MODEL = './results/pretrain_linear_reward.ckpt'` in `multi_agent.py`. -->

