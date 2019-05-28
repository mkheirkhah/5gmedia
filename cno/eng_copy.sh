scp a3c_cno_mks.py /.ssh/5g-media-keypair-external.pem ubuntu@217.172.12.203:~/cno_rl_uc2/cno
scp uc2_* /.ssh/5g-media-keypair-external.pem ubuntu@217.172.12.203:~/cno_rl_uc2/cno
scp rl_uc2.py /.ssh/5g-media-keypair-external.pem ubuntu@217.172.12.203:~/cno_rl_uc2/cno
scp -rd trained_models/ /.ssh/5g-media-keypair-external.pem ubuntu@217.172.12.203:~/cno_rl_uc2/cno
