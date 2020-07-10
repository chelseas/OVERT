using JuMP
using Gurobi
using LazySets

include("../OverApprox/src/overapprox_nd_relational.jl")
include("../OverApprox/src/overt_parser.jl")
include("../MIP/src/overt_to_mip.jl")

function encode_layer(inputs, w, input_size, output_size; activated=true)
	l = []
	for i in 1:output_size
		v =  Expr(:call, :+)
		for j = 1:input_size
			x = :($(w[i, j]) * $(inputs[j]))
			v.args = vcat(v.args, x)
		end
		if activated
			v = :(tanh($v))
		end
		push!(l, v)
	end
	l = hcat(l)
	return l
end

function get_min(sizes, input_set; N=3)

	input_size = sizes[1]
	n_layers = length(sizes) - 1
	inputs = [Meta.parse("x_$i") for i = 1:input_size]
	ranges = [[low(input_set)[i], high(input_set)[i]] for i = 1:input_size]
	inputs_range = Dict(:some => [-1., 1.])
	for i = 1:input_size
		inputs_range[inputs[i]] = ranges[i]
	end

	this_input = copy(inputs)
	for n in 1:n_layers - 1
		w = rand(sizes[n+1], sizes[n])
		w = round.(w, digits=3)
		this_input = encode_layer(this_input, w, sizes[n], sizes[n+1]; activated=true)
	end
	w = rand(sizes[n_layers+1], sizes[n_layers])
	output = encode_layer(this_input, w, sizes[n_layers], sizes[n_layers+1]; activated=false)
	oA = overapprox_nd(output[1], inputs_range; N=N)
	mip_model = OvertMIP(oA)
	mip_summary(mip_model.model)

	output_var = oA.output
	output_var_mip = mip_model.vars_dict[output_var]
	@objective(mip_model.model, Min, output_var_mip)
	JuMP.optimize!(mip_model.model)
	min_value = objective_value(mip_model.model)
	println("min = $min_value")
	return min_value
end


# input_size = 2
# l1_size = 15
# l2_size = 5
# l3_size = 5
# out_size = 1
#
# w1 = rand(l1_size, input_size); w1 = round.(w1, digits=3)
# w2 = rand(l2_size, l1_size); w2 = round.(w2, digits=3)
# w3 = rand(l3_size, l2_size); w3 = round.(w3, digits=3)
# w4 = rand(out_size, l3_size); w4 = round.(w4, digits=3)
#
# input = [:x1, :x2]
# l1 = encode_layer(input, w1, input_size, l1_size; activated=true)
# l2 = encode_layer(l1, w2, l1_size, l2_size, activated=true)
# l3 = encode_layer(l2, w3, l2_size, l3_size, activated=true)
# output = encode_layer(l3, w4, l3_size, out_size, activated=false)
#
# oA = overapprox_nd(output[1], Dict(:x1 => [1., 2.], :x2 => [1., 2.]); N=3)
# mip_model = OvertMIP(oA)
# mip_summary(mip_model.model)
#
# output_var = oA.output
# output_var_mip = mip_model.vars_dict[output_var]
# @objective(mip_model.model, Min, output_var_mip)
# JuMP.optimize!(mip_model.model)
# min_value = objective_value(mip_model.model)
# println("min = $min_value")
