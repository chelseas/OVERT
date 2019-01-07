# simple pendulum problem

# theta_dd = F/ml  - gsin(theta)/l
# theta_dd = Tau/(ml^2) - (g/l)*sin(theta)
import colored_traceback.always
import tensorflow as tf 
import numpy as np
from simple_overapprox_simple_pendulum import line, bound, build_sin_approx
import os
import joblib
from rllab.sampler.utils import rollout
import tensorflow as tf
from sandbox.rocky.tf.envs.base import TfEnv
from rllab.envs.gym_env import GymEnv

# inputs: state and action yields next state
def create_dynamics_block(num, var_dict):
	with tf.name_scope("Dynamics_"+str(num)):
		torque_UB = var_dict["action_UB"]
		theta_t_UB = var_dict["theta_t_UB"]
		theta_d_t_UB = var_dict["theta_d_t_UB"]
		torque_LB = var_dict["action_LB"]
		theta_t_LB = var_dict["theta_t_LB"]
		theta_d_t_LB = var_dict["theta_d_t_LB"]
		
		m = 0.25 # kg
		l = 0.1 # m
		oomls = tf.constant([[(1/ (m*(l**2)) )]], name="torque_scaling")

		c2_UB = torque_UB@oomls
		c2_LB = torque_LB@oomls

		# constant accel bounds
		# constant from dynamics plus scaled torque
		theta_dd_UB = 50. + c2_UB
		theta_dd_LB = -50. + c2_LB

		# Euler integration
		deltat = tf.constant([[0.05]], name="delta_t")
		# outputs: theta at t+1 and theta_dot at t+1
		with tf.name_scope("time_"+str(num+1)):
			theta_tp1_UB = theta_t_UB + theta_d_t_UB@deltat
			theta_tp1_LB = theta_t_LB + theta_d_t_LB@deltat
			theta_d_tp1_UB = theta_d_t_UB + theta_dd_UB@deltat
			theta_d_tp1_LB = theta_d_t_LB + theta_dd_LB@deltat

	#
	import pdb; pdb.set_trace()
	print("built dynamics graph")
	return [theta_tp1_UB, theta_tp1_LB, theta_d_tp1_UB, theta_d_tp1_LB]

sess = tf.Session()
print("initialized session")
# Initialize theta and theta-dot
with tf.variable_scope("initial_values"):
	theta_init_UB = tf.Variable([[1.0]], name="theta_init_UB")
	theta_init_LB = tf.Variable([[1.0]], name="theta_init_LB")
	theta_d_init_UB = tf.Variable([[0.0]], name="theta_d_init_UB")
	theta_d_init_LB = tf.Variable([[0.0]], name="theta_d_init_LB")
sess.run(tf.global_variables_initializer())

###########################################################
# load controller! :)
###########################################################
policy_file = "/Users/Chelsea/" # mac
policy_file = policy_file + "Dropbox/AAHAA/src/rllab/data/local/experiment/relu_small_network_ppo_capped_action/params.pkl"

# load policy object:
with sess.as_default():
	#with tf.name_scope("Controller"):
	data = joblib.load(policy_file)
	policy = data["policy"]
	print("loaded controller")

# Controller -> Dynamics

# input of controller is theta and theta-dot
# output of controller is action....
theta_UB = theta_init_UB
theta_d_UB = theta_d_init_UB
theta_LB = theta_init_LB
theta_d_LB = theta_d_init_LB
for i in range(5):
	with tf.name_scope("get_actions"):
		action_UB = policy.dist_info_sym(tf.stack([theta_UB, theta_d_UB], axis=1), [])["mean"]
		print("action_UB: ", sess.run([action_UB]))
		#
		action_LB = policy.dist_info_sym(tf.stack([theta_LB, theta_d_LB], axis=1), [])["mean"]
		print("action_LB: ", sess.run([action_LB]))

	# input of dynamics is torque(action), output is theta theta-dot at the next timestep
	with tf.name_scope("run_dynamics"):
		var_dict = {"action_UB": action_UB, 
					"theta_t_UB": theta_UB, 
					"theta_d_t_UB": theta_d_UB,
					"action_LB": action_LB, 
					"theta_t_LB": theta_LB, 
					"theta_d_t_LB": theta_d_LB, 
					}
		[theta_UB, theta_LB, theta_d_UB, theta_d_LB] = create_dynamics_block(num=0, var_dict=var_dict)
		print("theta_tp1_UB: ", sess.run([theta_UB]))
		print("theta_tp1_LB", sess.run([theta_LB]))
		print("theta_d_tp1_UB: ", sess.run([theta_d_UB]))
		print("theta_d_tp1_LB", sess.run([theta_d_LB]))

# okay, I want to "connect" the graphs and then export to tensorbooard the graph file
LOGDIR = "/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/tensorboard_logs/constant_dynamics_relu_policy_debug"
train_writer = tf.summary.FileWriter(LOGDIR) #, sess.graph)
train_writer.add_graph(sess.graph)
train_writer.close()

# next run at command line, e.g.:  tensorboard --logdir=/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/tensorboard_logs/UGH_multi_2


# see how many unique ops in the graph
# get current graph
# TODO: how to print all ops in a graph? below code only works for serialized graphs
g = sess.graph.as_graph_def()
# print n for all n in graph_def.node
[print(n) for n in g.node]
# make a set of the ops:
op_set = {(x.op,) for x in g.node}
# print this set of ops
[print(o[0]) for o in op_set]








