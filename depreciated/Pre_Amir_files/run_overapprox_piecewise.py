import colored_traceback.always
from correct_overapprox import *
import tensorflow as tf 
import numpy as np
import os
import joblib
# script to create concatted model

policy_file = "/Users/Chelsea/" # mac
policy_file = policy_file + "Dropbox/AAHAA/src/rllab/data/local/experiment/"
################################################################################

# good policy for 2dim observation (theta, thetadot)
policy_name = "curriculum_training_11142"
    #"EXCELLENT_POLICY_relu_small_network_ppo_capped_action_simpler_dense_layer_xW_learn_std_smaller_learning_rate/"

# bad policy for image observation
# policy_name = "convnet_1_ppo/"
################################################################################
policy_file = os.path.join(policy_file, policy_name,"params.pkl")

verbose = True
output_pb = True
output_nnet = False
f_id = str(int(np.round(np.random.rand()*50000)))
tensorboard_log_dir = "/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/tensorboard_logs/real_controller_piecewise_accel_bound_"+f_id
network_dir = "/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/nnet_files"
nsteps = 3
m = 0.25; # trained with 0.25 mass
l = 0.1;

network_construction_log = network_dir + "/extra_metadata_"+f_id+".txt"
with open(network_construction_log, 'w') as file:
        file.write("Steps: " + str(nsteps) + "\n")
        file.write("m = " + str(m) + "\n")
        file.write("l = " + str(l) + "\n")

build_model(nsteps, 
                output_pb, 
                output_nnet, 
                tensorboard_log_dir, 
                network_dir, 
                f_id,
                policy_file=policy_file, 
                activation_type="Relu",
                activation_fn=tf.nn.relu,
                dynamics_fun="piecewise",
                m=m,
                l=l,
                verbose=verbose)