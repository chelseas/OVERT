include("../../models/problems.jl")
include("../../OverApprox/src/overapprox_nd_relational.jl")
include("../../OverApprox/src/overt_parser.jl")
include("../../MIP/src/overt_to_mip.jl")
include("../../MIP/src/mip_utils.jl")
include("../../models/single_pendulum/single_pend.jl")

query = OvertQuery(
	SinglePendulum,                                      # problem
	"nnet_files/controller_single_pendulum.nnet",        # network file
	Id(),                                                # last layer activation layer Id()=linear, or ReLU()=relu
	"MIP",                                               # query solver, "MIP" or "ReluPlex"
	20,                                                  # ntime
	0.05,                                                # dt
	-1,                                                  # N_overt
	)

input_set = Hyperrectangle(low=[1., 0.], high=[1.2, 0.2])

# for symbolic probably need to break into
