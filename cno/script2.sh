#!/bin/bash

cd ./5gmedia-cno/cno && source ~/virtualenv/pillow2/bin/activate && python multi_agent_cno_mks.py --pa $8 --alpha $1 --bg_shape $2 --alr $3 --clr $4 --lc $5 --nn $6 --r_func $7 --trn $9 --seed ${10}


