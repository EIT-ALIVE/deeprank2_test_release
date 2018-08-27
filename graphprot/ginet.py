import torch
from torch.nn import Parameter
import torch.nn.functional as F
from torch_scatter import scatter_add
from torch_geometric.utils import remove_self_loops, add_self_loops, softmax

from torch_geometric.nn.inits import uniform
from torch_scatter import scatter_mean


def add_self_loops_wattr(edge_index, edge_attr, num_nodes=None):
    num_nodes = maybe_num_nodes(edge_index, num_nodes)

    dtype, device = edge_index.dtype, edge_index.device
    loop = torch.arange(0, num_nodes, dtype=dtype, device=device)
    loop = loop.unsqueeze(0).repeat(2, 1)
    edge_index = torch.cat([edge_index, loop], dim=1)

    dtype, device = edge_attr.dtype, edge_attr.device
    loop = torch.ones(num_nodes,dtype=dtype, device=device)
    edge_attr = torch.cat([edge_attr,loop])

    return edge_index, edge_attr


class GINet(torch.nn.Module):

    """
    This is a new layer that is similar to the graph attention network but simpler

    z_i =  1 / Ni \Sum_j a_ij * [x_i || x_j] * W + b_i

    || is the concatenation operator: [1,2,3] || [4,5,6] = [1,2,3,4,5,6]
    Ni is the number of neighbor of node i
    \Sum_j runs over the neighbors of node i
    a_ij is the edge attribute between node i and j

    Args:
        in_channels (int): Size of each input sample.
        out_channels (int): Size of each output sample.
        bias (bool, optional): If set to :obj:`False`, the layer will not learn
            an additive bias. (default: :obj:`True`)
    """

    def __init__(self,
                 in_channels,
                 out_channels,
                 bias=True):

        super(GINet, self).__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels

        self.weight = Parameter(
            torch.Tensor(2 * in_channels, out_channels))

        if bias:
            self.bias = Parameter(torch.Tensor(out_channels))
        else:
            self.register_parameter('bias', None)

        self.reset_parameters()

    def reset_parameters(self):
        size = 2 * self.in_channels
        uniform(size, self.weight)
        uniform(size, self.bias)

    def forward(self, x, edge_index, edge_attr):

        #print('weight : ', torch.sum(self.weight))

        row, col = edge_index
        num_node = len(x)
        edge_attr = edge_attr.unsqueeze(-1) if edge_attr.dim() == 1 else edge_attr

        # create edge feature by concatenating node feature
        alpha = torch.cat([x[row], x[col]], dim=-1)

        # multiply the edge features with the fliter
        alpha = torch.mm(alpha,self.weight)

        # multiply each edge features with the corresponding dist
        alpha = edge_attr*alpha

        # scatter the resulting edge feature to get node features
        out = torch.zeros(num_node,self.out_channels).to(alpha.device)
        out = scatter_mean(alpha,row,dim=0,out=out)

        # if the graph is undirected and (i,j) and (j,i) are both in
        # the edge_index then we do not need to have that second line
        # or we count everythong twice
        #out = scatter_mean(alpha,col,dim=0,out=out)

        # add the bias
        if self.bias is not None:
            out = out + self.bias

        return out

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__,
                                             self.in_channels,
                                             self.out_channels)