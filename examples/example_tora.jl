include("../models/problems.jl")
include("../OverApprox/src/overapprox_nd_relational.jl")
include("../OverApprox/src/overt_parser.jl")
include("../MIP/src/overt_to_mip.jl")
include("../MIP/src/mip_utils.jl")
include("../models/tora/tora.jl")

controller = "nnet_files/jair/tora_smallest_controller.nnet"

query = OvertQuery(
<<<<<<< HEAD
	Tora,                                          # problem
	controller,  # network file
	Id(),                                          # last layer activation layer Id()=linear, or ReLU()=relu
	"MIP",                                         # query solver, "MIP" or "ReluPlex"
	10,                                            # ntime
	0.1,                                           # dt
	-1,                                            # N_overt
=======
	Tora,       # problem
	controller, # network file
	Id(),       # last layer activation layer Id()=linear, or ReLU()=relu
	"MIP",      # query solver, "MIP" or "ReluPlex"
	10,         # ntime
	0.1,        # dt
	-1,         # N_overt
>>>>>>> 3aa8b2aa009643d7197ee6ff6ed72d3a198f100c
	)

input_set = Hyperrectangle(low=[0.6, -0.7, -0.4, 0.5], high=[0.7, -0.6, -0.3, 0.6])
t1 = Dates.time()
all_sets, all_sets_symbolic = symbolic_reachability(query, input_set)
t2 = Dates.time()
dt = (t2-t1)
print("elapsed time= $(dt) seconds")


fig = plot_output_sets(all_sets)
fig = plot_output_sets([all_sets_symbolic]; linecolor=:red, fig=fig)
fig = plot_output_hist(xvec, query.ntime; fig=fig, nbins=100)
