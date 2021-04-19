"""Unit tests for lv/zoo/core module."""
import collections
import pathlib
import tempfile

from lv.zoo import core

import pytest
import torch
from torch import nn
from torch.utils import data

LAYER = 'my-layer'


class Model(nn.Sequential):
    """A fake model that does not do very much."""

    def __init__(self, flag=False):
        """Initialize the model."""
        super().__init__(collections.OrderedDict([(LAYER, nn.Linear(10, 10))]))
        self.flag = flag


@pytest.fixture
def weights():
    """Return fake model weights."""
    return Model().state_dict()


@pytest.yield_fixture
def weights_file(weights):
    """Yield a fake weights file."""
    with tempfile.TemporaryDirectory() as tempdir:
        file = pathlib.Path(tempdir) / 'weights.pth'
        torch.save(weights, file)
        yield file


@pytest.fixture
def model_config():
    """Return a ModelConfig for testing."""
    return core.ModelConfig(factory=Model, flag=True)


def test_model_config_load(model_config, weights_file, weights):
    """Test ModelConfig.load in the basic case."""
    model, layers = model_config.load(path=weights_file)

    assert model.flag
    assert tuple(layers) == (LAYER,)

    state_dict = model.state_dict()
    assert state_dict.keys() == weights.keys()

    for key in state_dict:
        assert state_dict[key].allclose(weights[key], atol=1e-3)


OTHER_LAYER = 'other-layer'


def test_model_config_load_overwrite_defaults(model_config, weights_file,
                                              weights):
    """Test ModelConfig.load overwrites defaults."""
    model_config.layers = [OTHER_LAYER]
    model, layers = model_config.load(path=weights_file, flag=False)

    assert not model.flag
    assert tuple(layers) == (OTHER_LAYER,)

    state_dict = model.state_dict()
    assert state_dict.keys() == weights.keys()

    for key in state_dict:
        assert state_dict[key].allclose(weights[key], atol=1e-3)


def test_model_config_load_no_load_weights(model_config, weights_file,
                                           weights):
    """Test ModelConfig.load does not load weights when told not to."""
    model_config.load_weights = False
    model, layers = model_config.load(path=weights_file)

    assert model.flag

    state_dict = model.state_dict()
    assert state_dict.keys() == weights.keys()

    for key in state_dict:
        assert not state_dict[key].allclose(weights[key], atol=1e-3)


def test_model_config_load_bad_weights_path(model_config, weights_file):
    """Test ModelConfig.load dies when given bad weights file."""
    weights_file.unlink()
    with pytest.raises(FileNotFoundError, match='.*model path not found.*'):
        model_config.load(weights_file)


class Dataset(data.Dataset):
    """A fake dataset that reads tensors from disk."""

    def __init__(self, path, flag=False):
        """Initialize the dataset."""
        assert path.is_file()
        self.dataset = data.TensorDataset(torch.load(path))
        self.flag = flag

    def __getitem__(self, index):
        """Return the index'th tensor."""
        return self.dataset[index]

    def __len__(self):
        """Return the number of samples in the dataset."""
        return len(self.dataset)


N_SAMPLES = 10
N_FEATURES = 15


@pytest.fixture
def tensors():
    """Return fake tensor data for testing."""
    return torch.rand(N_SAMPLES, N_FEATURES)


@pytest.yield_fixture
def dataset_file(tensors):
    """Return a fake dataset file for testing."""
    with tempfile.TemporaryDirectory() as tempdir:
        file = pathlib.Path(tempdir) / 'data.pth'
        torch.save(tensors, file)
        yield file


@pytest.fixture
def dataset_config():
    """Return a DatasetConfig for testing."""
    return core.DatasetConfig(factory=Dataset, flag=True)


def test_dataset_config_load(dataset_config, dataset_file, tensors):
    """Test DatasetConfig.load correctly instantiates dataset."""
    actual = dataset_config.load(dataset_file)
    assert torch.cat(actual.dataset.tensors).allclose(tensors, atol=1e-3)
    assert actual.flag


def test_dataset_config_load_overwrite_defaults(dataset_config, dataset_file,
                                                tensors):
    """Test DatasetConfig.load correctly overwrites defaults."""
    actual = dataset_config.load(dataset_file, flag=False)
    assert torch.cat(actual.dataset.tensors).allclose(tensors, atol=1e-3)
    assert not actual.flag