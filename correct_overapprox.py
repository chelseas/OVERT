# adapt simple_pendulum_multi_step_constant_dynamics.py
# make it simpler
# make it a true overapproximation, so that output set is large enough to be correct

# Features: __________________________
# multiple steps
# constant dynamics (accel) bound


import colored_traceback.always
import tensorflow as tf 
import numpy as np
import os
import joblib

# parsing support libs
from tensorflow.python.framework import graph_util
import parsing
from NNet.scripts.writeNNet import writeNNet

# implement new dynamics block

# Q: once parsed, how to keep track of which inputs are which? need to name them maybe, and then name them when parsing too? or at the very least somehow collect the order of the output names when parsing, and the order of the input names 

# plan: treat theta and thetadot seperately until i need to feed them into controller, where you can multiply by tall matrices and add together to concat

class Dynamics():
    def __init__(self): 
        with tf.name_scope("dynamics_constants"):
            self.m = 0.25 # kg
            self.l = 0.1 # m
            self.oomls = tf.constant([[(1/ (self.m*(self.l**2)) )]], name="torque_scaling")
            # currently accel bounds are constant but will be funcs of theta
            self.accel_UB = lambda theta: tf.constant([[50.]])
            self.accel_LB = lambda theta: tf.constant([[-50.]])
            self.deltat = tf.constant(0.05*np.eye(1), dtype='float32', name="deltat")

    def run(self, num, action, theta, theta_dot): 
        with tf.name_scope("Dynamics_"+str(num)):
            theta_hat = tf.add(theta, self.deltat@theta_dot, name="theta_"+str(num))
            theta_dot_UB = tf.add(
                            theta_dot,
                            self.deltat@(self.oomls@action + self.accel_UB(theta)),
                            name="theta_dot_UB_"+str(num)
                        )
            theta_dot_LB = tf.add(
                            theta_dot,
                            self.deltat@(self.oomls@action + self.accel_LB(theta)),
                            name="theta_dot_LB_"+str(num)
                        )
        return theta_hat, theta_dot_LB, theta_dot_UB

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

class ReluProtector():
    def __init__(self, state_dim):
        self.before = tf.constant(np.vstack([np.eye(state_dim), -np.eye(state_dim)]), dtype='float32')
        self.after = tf.constant(np.hstack([np.eye(state_dim), -np.eye(state_dim)]), dtype='float32')
    def apply(self, state, name=""):
        return tf.matmul(self.after, tf.nn.relu(self.before@state), name=name)

def build_multi_step_network(theta_0, theta_dot_0, controller, dynamics, nsteps, ncontroller_act):
    with tf.name_scope("assign_init_vals"):
        relu_protector = ReluProtector(1)
        theta = theta_0
        theta_dot = theta_dot_0
        theta_dot_hats = []
        for i in range(nsteps):
            theta_dot_hats.append(tf.placeholder(
                    tf.float32,
                    shape=(1,1),
                    name="theta_dot_hat_"+str(i+1)
                ))
        theta_dot_LBs = []
        theta_dot_UBs = []
        thetas = []
    #
    for i in range(nsteps):
        with tf.name_scope("get_action"):
            state = tf.constant([[1.],[0.]])@theta + tf.constant([[0.],[1.]])@theta_dot 
            action = controller.run(state)
        #
        # apply relu protection
        with tf.name_scope("relu_protection"):
            for j in range(ncontroller_act):
                theta = relu_protector.apply(theta, name="theta")
                thetas = [relu_protector.apply(t, name="theta_o") for t in thetas]
                theta_dot = relu_protector.apply(theta_dot, name="theta_dot")
                theta_dot_LBs = [relu_protector.apply(tdlb, name="tdlb") for tdlb in theta_dot_LBs]
                theta_dot_UBs = [relu_protector.apply(tdub, name="tdub") for tdub in theta_dot_UBs]
                theta_dot_hats = [relu_protector.apply(tdh, name="tdh") for tdh in theta_dot_hats]
            
        # input of dynamics is torque(action), output is theta theta-dot at the next timestep
        with tf.name_scope("run_dynamics"):
            theta, theta_dot_LB, theta_dot_UB = dynamics.run(num=i+1, action=action, theta=theta, theta_dot=theta_dot)
            theta_dot_LBs.append(theta_dot_LB)
            theta_dot_UBs.append(theta_dot_UB)
            thetas.append(theta) # collect all thetas from theta_1 onwards
            theta_dot = theta_dot_hats[i]
            
    #
    return (thetas, theta_dot, theta_dot_hats, theta_dot_LBs, theta_dot_UBs)

def display_ops(sess):
    g = sess.graph.as_graph_def()
    # print n for all n in graph_def.node
    print("before freezing:")
    [print(n.name) for n in g.node]
    # make a set of the ops:
    op_set = {(x.op,) for x in g.node}
    # print this set of ops
    [print(o[0]) for o in op_set]

def write_to_tensorboard(logdir, sess):
    train_writer = tf.summary.FileWriter(logdir)
    train_writer.add_graph(sess.graph) 
    train_writer.close()
    print("wrote to tensorboard log")

def write_metadata(input_list, output_list, directory, fid):
    filename = os.path.join(directory, "meta_data_" + fid + ".txt")
    with open(filename,'w') as file:
        file.write("inputs: \n")
        file.write("%s\n" % str(input_list))
        file.write("outputs: \n")
        file.write("%s\n" % str(output_list))

def collect_output_ops(cat_list):
    master_list = []
    for cat in cat_list:
        op_names = [t.op.name for t in cat]
        master_list.extend(op_names)
    return master_list