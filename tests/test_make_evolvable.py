import pytest
import torch
import torch.nn as nn

from agilerl.wrappers.make_evolvable import MakeEvolvable
from tests.helper_functions import unpack_network


class TwoArgCNN(nn.Module):
    def __init__(self):
        super().__init__()

        # Define the convolutional layers
        self.conv1 = nn.Conv3d(
            in_channels=4, out_channels=16, kernel_size=(1, 3, 3), stride=4
        )  # W: 160, H: 210
        self.conv2 = nn.Conv3d(
            in_channels=16, out_channels=32, kernel_size=(1, 3, 3), stride=2
        )  # W:

        # Define the max-pooling layers
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Define fully connected layers
        self.fc1 = nn.Linear(304002, 256)
        self.fc2 = nn.Linear(256, 2)

        # Define activation function
        self.relu = nn.ReLU()

        # Define softmax for classification
        self.softmax = nn.Softmax(dim=1)
        self.tanh = nn.Tanh()

    def forward(self, x, xc):
        # Forward pass through convolutional layers
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))

        # Flatten the output for the fully connected layers
        x = x.view(x.size(0), -1)
        x = torch.cat([x, xc], dim=1)
        # Forward pass through fully connected layers
        x = self.tanh(self.fc1(x))
        x = self.fc2(x)

        # Apply softmax for classification
        x = self.softmax(x)

        return x


@pytest.fixture
def simple_mlp():
    network = nn.Sequential(
        nn.Linear(10, 20),
        nn.ReLU(),
        nn.Linear(20, 10),
        nn.ReLU(),
        nn.Linear(10, 1),
        nn.Tanh(),
    )
    return network


@pytest.fixture
def simple_mlp_2():
    network = nn.Sequential(
        nn.Linear(10, 128), nn.ReLU(), nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, 1)
    )
    return network


@pytest.fixture
def simple_cnn():
    network = nn.Sequential(
        nn.Conv2d(
            3, 16, kernel_size=3, stride=1, padding=1
        ),  # Input channels: 3 (for RGB images), Output channels: 16
        nn.ReLU(),
        nn.MaxPool2d(kernel_size=2, stride=2),
        nn.Conv2d(
            16, 32, kernel_size=3, stride=1, padding=1
        ),  # Input channels: 16, Output channels: 32
        nn.ReLU(),
        nn.MaxPool2d(kernel_size=2, stride=2),
        nn.Flatten(),  # Flatten the 2D feature map to a 1D vector
        nn.Linear(32 * 16 * 16, 128),  # Fully connected layer with 128 output features
        nn.ReLU(),
        nn.Linear(128, 1),  # Output layer with num_classes output features
    )
    return network


@pytest.fixture
def two_arg_cnn():
    return TwoArgCNN()


@pytest.fixture
def device():
    return "cuda" if torch.cuda.is_available() else "cpu"


######### Test instantiation #########
# The class can be instantiated with all the required parameters and no errors occur.
@pytest.mark.parametrize(
    "network, input_tensor",
    [("simple_mlp", torch.randn(1, 10)), ("simple_cnn", torch.randn(1, 3, 64, 64))],
)
def test_instantiation_with_required_parameters(network, input_tensor, request):
    network = request.getfixturevalue(network)
    evolvable_network = MakeEvolvable(network, input_tensor)
    assert isinstance(evolvable_network, MakeEvolvable)
    assert str(unpack_network(evolvable_network)) == str(unpack_network(network))


# The class can be instantiated with minimal parameters and default values are assigned correctly.
def test_instantiation_with_minimal_parameters():
    network = nn.Sequential(
        nn.Linear(10, 20), nn.Linear(20, 20), nn.ReLU(), nn.Linear(20, 1), nn.ReLU()
    )
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(network, input_tensor)
    assert isinstance(evolvable_network, MakeEvolvable)
    assert str(unpack_network(evolvable_network)) == str(unpack_network(network)), str(
        unpack_network(evolvable_network)
    )


######### Test forward #########
@pytest.mark.parametrize(
    "network, input_tensor, secondary_input_tensor, expected_result",
    [
        ("simple_mlp", torch.randn(1, 10), None, (1, 1)),
        ("simple_cnn", torch.randn(1, 3, 64, 64), None, (1, 1)),
        ("two_arg_cnn", torch.randn(1, 4, 160, 210, 160), torch.randn(1, 2), (1, 2)),
    ],
)
def test_forward_method(
    network, input_tensor, secondary_input_tensor, expected_result, request, device
):
    network = request.getfixturevalue(network)
    if secondary_input_tensor is None:
        evolvable_network = MakeEvolvable(network, input_tensor, device=device)
        actual_output = evolvable_network.forward(input_tensor)
    else:
        evolvable_network = MakeEvolvable(
            network, input_tensor, secondary_input_tensor, device, extra_critic_dims=2
        )
        actual_output = network.forward(input_tensor, secondary_input_tensor)
    output_shape = actual_output.shape
    if secondary_input_tensor is not None:
        print(str(unpack_network(network)))
        print(str(unpack_network(evolvable_network)))
    assert output_shape == expected_result


# The forward() method can handle different types of input tensors (e.g., numpy array, torch tensor).
def test_forward_method_with_different_input_types(simple_mlp):
    input_tensor = torch.randn(1, 10)
    numpy_array = input_tensor.numpy()
    evolvable_network = MakeEvolvable(simple_mlp, input_tensor)
    output1 = evolvable_network.forward(input_tensor)
    output2 = evolvable_network.forward(numpy_array)
    assert isinstance(output1, torch.Tensor)
    assert isinstance(output2, torch.Tensor)


# The forward() method can handle different types of normalization layers (e.g., BatchNorm2d, InstanceNorm3d).
def test_forward_with_different_normalization_layers():
    network = nn.Sequential(
        nn.Linear(10, 20),
        nn.LayerNorm(20),
        nn.ReLU(),
        nn.Linear(20, 10),
        nn.ReLU(),
        nn.Linear(10, 1),
    )
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(network, input_tensor)
    output = evolvable_network.forward(input_tensor)

    print(str(unpack_network(evolvable_network)))
    print(str(unpack_network(network)))

    assert isinstance(output, torch.Tensor)
    assert str(unpack_network(evolvable_network)) == str(unpack_network(network))


######### Test detect architecture function #########


# Detects architecture of a neural network with convolutional layers and without normalization layers
def test_detect_architecture_mlp_simple(device):
    net = nn.Sequential(
        nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1)
    )
    evolvable_net = MakeEvolvable(net, torch.randn(1, 4), device=device)
    assert evolvable_net.mlp_layer_info == {"activation_layers": {0: "ReLU", 1: "ReLU"}}
    assert str(unpack_network(net)) == str(unpack_network(evolvable_net))


def test_detect_architecture_medium(device):
    net = nn.Sequential(
        nn.Linear(4, 16), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1), nn.Tanh()
    )
    evolvable_net = MakeEvolvable(net, torch.randn(1, 4), device=device)
    assert evolvable_net.mlp_layer_info == {"activation_layers": {1: "ReLU", 2: "Tanh"}}
    assert str(unpack_network(net)) == str(unpack_network(evolvable_net))


def test_detect_architecture_complex(device):
    net = nn.Sequential(
        nn.Linear(4, 16),
        nn.LayerNorm(16),
        nn.Linear(16, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
        nn.Tanh(),
    )
    evolvable_net = MakeEvolvable(net, torch.randn(1, 4), device=device)
    assert evolvable_net.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "Tanh"},
        "norm_layers": {0: "LayerNorm"},
    }, evolvable_net.mlp_layer_info
    assert str(unpack_network(net)) == str(unpack_network(evolvable_net))


# Test if network after detect arch has the same arch as original network
@pytest.mark.parametrize(
    "network, input_tensor",
    [
        ("simple_mlp", torch.randn(1, 10)),
        ("simple_cnn", torch.randn(1, 3, 64, 64)),
    ],
)
def test_detect_architecture_networks_the_same(network, input_tensor, device, request):
    network = request.getfixturevalue(network)
    evolvable_network = MakeEvolvable(network, input_tensor, device=device)
    assert str(unpack_network(network)) == str(unpack_network(evolvable_network))


def test_add_mlp_layer_simple(simple_mlp, device):
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(simple_mlp, input_tensor, device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {0: "ReLU", 1: "ReLU", 2: "Tanh"}
    }, evolvable_network.mlp_layer_info
    evolvable_network.add_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers + 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {0: "ReLU", 1: "ReLU", 2: "ReLU", 3: "Tanh"}
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


def test_add_mlp_layer_medium(device):
    network = nn.Sequential(
        nn.Linear(4, 16), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1), nn.Tanh()
    )
    evolvable_network = MakeEvolvable(network, torch.randn(1, 4), device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "Tanh"}
    }, evolvable_network.mlp_layer_info
    evolvable_network.add_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers + 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "ReLU", 3: "Tanh"}
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


def test_add_mlp_layer_complex(device):
    net = nn.Sequential(
        nn.Linear(4, 16),
        nn.LayerNorm(16),
        nn.Linear(16, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
        nn.Tanh(),
    )
    evolvable_network = MakeEvolvable(net, torch.randn(1, 4), device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "Tanh"},
        "norm_layers": {0: "LayerNorm"},
    }, evolvable_network.mlp_layer_info
    evolvable_network.add_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers + 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "ReLU", 3: "Tanh"},
        "norm_layers": {0: "LayerNorm"},
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


######### Test remove_mlp_layer #########
def test_remove_mlp_layer_simple(simple_mlp_2, device):
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(simple_mlp_2, input_tensor, device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {0: "ReLU", 1: "ReLU"}
    }
    evolvable_network.remove_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers - 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {0: "ReLU"}
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            torch.testing.assert_close(param, value_net_dict[key])


def test_remove_mlp_layer_medium(device):
    network = nn.Sequential(
        nn.Linear(4, 16), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1), nn.Tanh()
    )
    evolvable_network = MakeEvolvable(network, torch.randn(1, 4), device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "Tanh"}
    }, evolvable_network.mlp_layer_info
    evolvable_network.remove_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers - 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "Tanh"}
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


def test_remove_mlp_layer_complex(device):
    net = nn.Sequential(
        nn.Linear(4, 16),
        nn.LayerNorm(16),
        nn.Linear(16, 16),
        nn.ReLU(),
        nn.Linear(16, 1),
        nn.Tanh(),
    )
    evolvable_network = MakeEvolvable(net, torch.randn(1, 4), device=device)
    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())
    initial_num_layers = len(evolvable_network.hidden_size)
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "ReLU", 2: "Tanh"},
        "norm_layers": {0: "LayerNorm"},
    }, evolvable_network.mlp_layer_info
    evolvable_network.remove_mlp_layer()
    new_value_net = evolvable_network.value_net
    assert len(evolvable_network.hidden_size) == initial_num_layers - 1
    assert evolvable_network.mlp_layer_info == {
        "activation_layers": {1: "Tanh"},
        "norm_layers": {0: "LayerNorm"},
    }, evolvable_network.mlp_layer_info
    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


######### Test add_mlp_node #########
def test_add_mlp_node_fixed(simple_mlp, device):
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(simple_mlp, input_tensor, device=device)

    # Test adding a new node to a specific layer
    hidden_layer = 1
    numb_new_nodes = 8
    result = evolvable_network.add_mlp_node(hidden_layer, numb_new_nodes)

    # Check if the hidden layer and number of new nodes are updated correctly
    assert evolvable_network.hidden_size[hidden_layer] == 18
    assert result["hidden_layer"] == hidden_layer
    assert result["numb_new_nodes"] == numb_new_nodes


######### Test remove_mlp_node #########
def test_remove_mlp_node(simple_mlp_2, device):
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(simple_mlp_2, input_tensor, device=device)

    # Check the initial number of nodes in the hidden layers
    assert len(evolvable_network.hidden_size) == 2

    # Remove a node from the second hidden layer
    evolvable_network.remove_mlp_node(hidden_layer=1, numb_new_nodes=10)

    # Check that the number of nodes in the second hidden layer has decreased by 10
    assert evolvable_network.hidden_size[1] == 118

    # Remove a node from the first hidden layer
    evolvable_network.remove_mlp_node(hidden_layer=0, numb_new_nodes=5)

    # Check that the number of nodes in the first hidden layer has decreased by 5
    assert evolvable_network.hidden_size[0] == 123


######### Test add_cnn_layer #########
def test_add_cnn_layer(simple_cnn, device):
    input_tensor = torch.randn(1, 3, 64, 64)
    evolvable_network = MakeEvolvable(simple_cnn, input_tensor, device=device)

    # Check the initial number of layers
    assert len(evolvable_network.channel_size) == 2

    # Add a new CNN layer
    evolvable_network.add_cnn_layer()

    # Check if a new layer has been added
    assert len(evolvable_network.channel_size) == 3
    print(evolvable_network.cnn_layer_info)
    assert evolvable_network.cnn_layer_info == {
        "activation_layers": {0: "ReLU", 1: "ReLU", 2: "ReLU"},
        "conv_layer_type": "Conv2d",
        "pooling_layers": {
            0: {"name": "MaxPool2d", "kernel": 2, "stride": 2, "padding": 0},
            1: {"name": "MaxPool2d", "kernel": 2, "stride": 2, "padding": 0},
        },
    }, evolvable_network.cnn_layer_info


######### Test change_cnn_kernel #########
def test_change_cnn_kernel(simple_cnn, device):
    input_tensor = torch.randn(1, 3, 64, 64)
    evolvable_network = MakeEvolvable(simple_cnn, input_tensor, device=device)

    # Check initial kernel sizes
    assert evolvable_network.kernel_size == [(3, 3), (3, 3)]

    # Change kernel size
    evolvable_network.change_cnn_kernel()

    while evolvable_network.kernel_size == [(3, 3), (3, 3)]:
        evolvable_network.change_cnn_kernel()

    # Check if kernel size has changed
    assert evolvable_network.kernel_size != [
        (3, 3),
        (3, 3),
    ], evolvable_network.kernel_size


######### Test recreate_nets #########
def test_recreate_nets_parameters_preserved(simple_mlp, device):
    input_tensor = torch.randn(1, 10)
    evolvable_network = MakeEvolvable(simple_mlp, input_tensor, device=device)

    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())

    # Modify the architecture
    evolvable_network.hidden_size += [evolvable_network.hidden_size[-1]]

    evolvable_network.recreate_nets()
    new_value_net = evolvable_network.value_net

    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            assert torch.equal(param, value_net_dict[key])


def test_recreate_nets_parameters_shrink_preserved(device):
    network = nn.Sequential(
        nn.Linear(4, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU(), nn.Linear(32, 2)
    )

    input_tensor = torch.randn(1, 4)
    evolvable_network = MakeEvolvable(network, input_tensor, device=device)

    value_net = evolvable_network.value_net
    value_net_dict = dict(value_net.named_parameters())

    print(evolvable_network.hidden_size)

    print(evolvable_network)

    # Modify the architecture
    evolvable_network.hidden_size = evolvable_network.hidden_size[:-1]
    print(evolvable_network.hidden_size)

    print(evolvable_network)
    evolvable_network.recreate_nets(shrink_params=True)
    new_value_net = evolvable_network.value_net

    for key, param in new_value_net.named_parameters():
        if key in value_net_dict.keys():
            print(param, value_net_dict[key])
            torch.testing.assert_close(param, value_net_dict[key])


######### Test clone #########


# The clone() method successfully creates a deep copy of the model.
@pytest.mark.parametrize(
    "network, input_tensor, secondary_input_tensor",
    [
        ("simple_mlp", torch.randn(1, 10), None),
        (
            "simple_cnn",
            torch.randn(1, 3, 64, 64),
            None,
        ),
        ("two_arg_cnn", torch.randn(1, 4, 160, 210, 160), torch.randn(1, 2)),
    ],
)
def test_clone_method_with_equal_state_dicts(
    network, input_tensor, secondary_input_tensor, request, device
):
    network = request.getfixturevalue(network)
    if secondary_input_tensor is None:
        evolvable_network = MakeEvolvable(network, input_tensor, device=device)
    else:
        evolvable_network = MakeEvolvable(
            network,
            input_tensor,
            secondary_input_tensor,
            device=device,
            extra_critic_dims=2,
        )
    clone_network = evolvable_network.clone()
    print(evolvable_network.state_dict().keys())
    print(clone_network.state_dict().keys())
    assert isinstance(clone_network, MakeEvolvable)
    assert str(evolvable_network.state_dict()) == str(clone_network.state_dict())