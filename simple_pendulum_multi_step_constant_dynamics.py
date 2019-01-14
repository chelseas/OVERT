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
import sandbox.rocky.tf.core.layers as L
from tensorflow.python.framework import graph_util
import parsing

# inputs: state and action yields next state
def create_dynamics_block(num, var_dict):
	with tf.name_scope("Dynamics_"+str(num)):
		torque_UB = var_dict["action_UB"]
		state_UB = var_dict["state_UB"]
		torque_LB = var_dict["action_LB"]
		state_LB = var_dict["state_LB"]
		#
		m = 0.25 # kg
		l = 0.1 # m
		oomls = tf.constant([[(1/ (m*(l**2)) )]], name="torque_scaling")
        #
		# constant accel bounds
		# constant from dynamics plus scaled torque
		const_UB = tf.constant([[50.]])
		const_LB = tf.constant([[-50.]])
        #
		# Euler integration
		deltat = tf.constant(0.05*np.eye(2), dtype='float32', name="delta_t")
		# outputs: state (theta and thetadot) at t+1
		with tf.name_scope("time_"+str(num+1)):
			theta_d_UB = tf.constant([[0.,1.],[0.,0.]])@state_UB
			theta_dd_UB = tf.constant([[0.],[1.]])@(oomls@torque_UB + const_UB)
			change_UB = deltat@theta_d_UB + deltat@theta_dd_UB
			state_tp1_UB = state_UB + change_UB
			# identical for lower bound
			theta_d_LB = tf.constant([[0.,1.],[0.,0.]])@state_LB
			theta_dd_LB = tf.constant([[0.],[1.]])@(oomls@torque_LB + const_LB)
			change_LB = deltat@theta_d_LB + deltat@theta_dd_LB
			state_tp1_LB = state_LB + change_LB
			# identical for lower bound
    #
	#
	print("built dynamics graph")
	return [state_tp1_UB, state_tp1_LB]

sess = tf.Session()
print("initialized session")
# Initialize theta and theta-dot
with tf.variable_scope("initial_values"):
	state_UB_0 = tf.placeholder(tf.float32, shape=(2,1), name="state_UB")
	# theta, theta dot, UB
	state_LB_0 = tf.placeholder(tf.float32, shape=(2,1), name="state_LB")

# sess.run(tf.global_variables_initializer())

###########################################################
# load controller! :)
###########################################################
# policy_file = "/Users/Chelsea/" # mac
# policy_file = policy_file + "Dropbox/AAHAA/src/rllab/data/local/experiment/relu_small_network_vpg_capped_action_trying_simpler_dense_layer/params.pkl"

# # load policy object:
# with sess.as_default():
# 	#with tf.name_scope("Controller"):
# 	data = joblib.load(policy_file)
# 	policy = data["policy"]
# 	print("loaded controller")
# 	g = sess.graph.as_graph_def()
# 	#[print(n.name) for n in g.node]
# 	output_node_name = "policy/mean_network/output"
# 	output_graph_def = graph_util.convert_variables_to_constants(
# 	    sess, # sess used to retrieve weights
# 	    g, # graph def used to retrieve nodes
# 	    output_node_name.split(",") # output node names used to select useful nodes
# 	    )
# 	print("op set: ", {(x.op,) for x in output_graph_def.node})

#####################################
# dummy controller
#####################################
class Controller():

	def __init__(self):
		with tf.name_scope('Controller'):
			self.W0 = tf.Variable(np.random.rand(4,2)*2-1, dtype='float32')
			self.b0 = tf.Variable(np.random.rand(4,1)*2-1, dtype='float32')
			self.W1 = tf.constant(np.random.rand(4,4)*2-1, dtype='float32')
			self.b1 = tf.constant(np.random.rand(4,1)*2-1, dtype='float32')
			self.Wf = tf.constant(np.random.rand(1,4)*2-1, dtype='float32')
			self.bf = tf.constant(np.random.rand(1,1)*2-1, dtype='float32')

	def run(self, state0):
		state = tf.nn.relu(self.W0@state0 + self.b0)
		state = tf.nn.relu(self.W1@state + self.b1)
		statef = self.Wf@state + self.bf
		return statef

# Controller -> Dynamics

# input of controller is theta and theta-dot
# output of controller is action....
relu_protector_1 = tf.constant(np.vstack([np.eye(2), -np.eye(2)]), dtype='float32')
relu_protector_2 = tf.constant(np.hstack([np.eye(2), -np.eye(2)]), dtype='float32')
state_UB = state_UB_0
state_LB = state_LB_0
controller = Controller()
for i in range(1):
	with tf.name_scope("get_actions"):
		#action_UB, = L.get_output([policy._l_mean], tf.transpose(state_UB))
		#action_LB, = L.get_output([policy._l_mean], tf.transpose(state_LB))
		action_UB = controller.run(state_UB)
		action_LB = controller.run(state_LB)
	#
	# apply relu protection
	with tf.name_scope("relu_protection"):
		for i in range(2):
			state_UB = relu_protector_2@tf.nn.relu(relu_protector_1@state_UB)
			state_LB = relu_protector_2@tf.nn.relu(relu_protector_1@state_LB)

	# input of dynamics is torque(action), output is theta theta-dot at the next timestep
	with tf.name_scope("run_dynamics"):
		var_dict = {"action_UB": action_UB, 
					"state_UB": state_UB, 
					"action_LB": action_LB, 
					"state_LB": state_LB, 
					}
		[state_UB, state_LB] = create_dynamics_block(num=i, var_dict=var_dict)

state_UB_final = state_UB
state_LB_final = state_LB

feed_dict_UB = {
	state_UB_0: np.array([[1.0], [0.0]]),
}
feed_dict_LB = {
	state_LB_0: np.array([[1.0], [0.0]]),
}
sess.run(tf.global_variables_initializer())
print("[theta, theta_dot]_UB: ", sess.run([state_UB_final], feed_dict=feed_dict_UB))
print("[theta, theta_dot]_LB", sess.run([state_LB_final], feed_dict=feed_dict_LB))
	
# see how many unique ops in the graph
# get current graph
# TODO: how to print all ops in a graph? below code only works for serialized graphs
g = sess.graph.as_graph_def()
# print n for all n in graph_def.node
[print(n.name) for n in g.node]
# make a set of the ops:
op_set = {(x.op,) for x in g.node}
# print this set of ops
[print(o[0]) for o in op_set]

# filter stuff out
# also add_2 is the other output. concat them together with a multiply and an add?
output_node_name = "run_dynamics/Dynamics_1/time_2/add_5"
output_graph_def = graph_util.convert_variables_to_constants(
    sess, # sess used to retrieve weights
    g, # graph def used to retrieve nodes
    output_node_name.split(",") # output node names used to select useful nodes
    )
#print("all nodes: ", [(x.op, x.name) for x in output_graph_def.node])
print("op set: ", {(x.op,) for x in output_graph_def.node})

sess.close()
tf.reset_default_graph()
s2 = tf.Session()
with s2.as_default():
	tf.import_graph_def(output_graph_def)
	g = tf.get_default_graph()

# okay, I want to "connect" the graphs and then export to tensorbooard the graph file
LOGDIR = "/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/tensorboard_logs/constant_dynamics_handcrafted_policy_2"
train_writer = tf.summary.FileWriter(LOGDIR) #, sess.graph)
train_writer.add_graph(g) # TODO: add the filtered graph only! # sess.graph
train_writer.close()
print("wrote to tensorboard log")

# next run at command line, e.g.:  tensorboard --logdir=/Users/Chelsea/Dropbox/AAHAA/src/OverApprox/tensorboard_logs/UGH_multi_2

# parse!!!! to .nnet!!!!
output_op = g.get_operation_by_name("import/run_dynamics/Dynamics_1/time_2/add_5")
print("got operation")
W,b = parsing.parse_network([output_op], [], [], [], [], 'Relu', s2)
print("parsed!")
W.reverse()
b.reverse()
net = parsing.create_tf_network(W,b,inputs=p, activation=activation)
feed_dict_UB = {
	p: np.array([[1.0], [0.0]]),
}
feed_dict_LB = {
	p: np.array([[1.0], [0.0]]),
}
print("[theta, theta_dot]_UB after parsing: ", s2.run([net], feed_dict=feed_dict_UB))
print("[theta, theta_dot]_LB  after parsing", s2.run([net], feed_dict=feed_dict_LB))







