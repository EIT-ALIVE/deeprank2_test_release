import tempfile
import shutil
import os
import unittest
import pytest
import logging
import warnings
import torch
from deeprankcore.trainer import Trainer
from deeprankcore.dataset import GraphDataset
from deeprankcore.neuralnets.ginet import GINet
from deeprankcore.neuralnets.foutnet import FoutNet
from deeprankcore.neuralnets.naive_gnn import NaiveNetwork
from deeprankcore.neuralnets.sgat import SGAT
from deeprankcore.utils.metrics import (
    OutputExporter,
    TensorboardBinaryClassificationExporter,
    ScatterPlotExporter
)
from deeprankcore.domain import (edgestorage as Efeat, nodestorage as Nfeat,
                                targetstorage as targets)


_log = logging.getLogger(__name__)

default_features = [Nfeat.RESTYPE, Nfeat.POLARITY, Nfeat.BSA, Nfeat.RESDEPTH, Nfeat.HSE, Nfeat.INFOCONTENT, Nfeat.PSSM]

def _model_base_test( # pylint: disable=too-many-arguments, too-many-locals
    model_class,
    train_hdf5_path,
    val_hdf5_path,
    test_hdf5_path,
    node_features,
    edge_features,
    task,
    target,
    transform_sigmoid,
    metrics_exporters,
    clustering_method,
    use_cuda = False
):

    dataset_train = GraphDataset(
        hdf5_path=train_hdf5_path,
        node_features=node_features,
        edge_features=edge_features,
        task = task,
        target=target,
        clustering_method=clustering_method)

    if val_hdf5_path is not None:
        dataset_val = GraphDataset(
            hdf5_path=val_hdf5_path,
            node_features=node_features,
            edge_features=edge_features,
            task = task,
            target=target,
            clustering_method=clustering_method)
    else:
        dataset_val = None

    if test_hdf5_path is not None:
        dataset_test = GraphDataset(
            hdf5_path=test_hdf5_path,
            node_features=node_features,
            edge_features=edge_features,
            target=target,
            task=task,
            clustering_method=clustering_method)
    else:
        dataset_test = None

    trainer = Trainer(
        model_class,
        dataset_train,
        dataset_val,
        dataset_test,
        batch_size=64,
        transform_sigmoid=transform_sigmoid,
        metrics_exporters=metrics_exporters,
    )

    if use_cuda:
        _log.debug("cuda is available, testing that the model is cuda")
        for parameter in trainer.model.parameters():
            assert parameter.is_cuda, f"{parameter} is not cuda"

        data = dataset_train.get(0)

        for name, data_tensor in (("x", data.x), ("y", data.y),
                                  (Efeat.INDEX, data.edge_index),
                                  ("edge_attr", data.edge_attr),
                                  (Nfeat.POSITION, data.pos),
                                  ("cluster0",data.cluster0),
                                  ("cluster1", data.cluster1)):

            if data_tensor is not None:
                assert data_tensor.is_cuda, f"data.{name} is not cuda"

    with warnings.catch_warnings(record=UserWarning):
        trainer.train(nepoch=3, validate=True)
        trainer.save_model("test.pth.tar")

        Trainer(
            model_class,
            dataset_train,
            dataset_val,
            dataset_test,
            pretrained_model="test.pth.tar")

class TestTrainer(unittest.TestCase):
    @classmethod
    def setUpClass(class_):
        class_.work_directory = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(class_):
        shutil.rmtree(class_.work_directory)

    def test_ginet_sigmoid(self):
        _model_base_test(
            GINet,
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            default_features,
            [Efeat.DISTANCE],
            targets.REGRESS,
            targets.IRMSD,
            True,
            [OutputExporter(self.work_directory)],
            "mcl",
        )

    def test_ginet(self):
        _model_base_test(           
            GINet,
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            default_features,
            [Efeat.DISTANCE],
            targets.REGRESS,
            targets.IRMSD,
            False,
            [OutputExporter(self.work_directory)],
            "mcl",
        )

        assert len(os.listdir(self.work_directory)) > 0

    def test_ginet_class(self):
        _model_base_test(
            GINet,
            "tests/data/hdf5/variants.hdf5",
            "tests/data/hdf5/variants.hdf5",
            "tests/data/hdf5/variants.hdf5",
            [Nfeat.POLARITY, Nfeat.INFOCONTENT, Nfeat.PSSM],
            [Efeat.DISTANCE],
            targets.CLASSIF,
            targets.BINARY,
            False,
            [TensorboardBinaryClassificationExporter(self.work_directory)],
            "mcl",
        )

        assert len(os.listdir(self.work_directory)) > 0

    def test_fout(self):
        _model_base_test(
            FoutNet,
            "tests/data/hdf5/test.hdf5",
            "tests/data/hdf5/test.hdf5",
            "tests/data/hdf5/test.hdf5",
            default_features,
            [Efeat.DISTANCE],
            targets.CLASSIF,
            targets.BINARY,
            False,
            None,
            "mcl",
        )

    def test_sgat(self):
        _model_base_test(
            SGAT,
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            "tests/data/hdf5/1ATN_ppi.hdf5",
            default_features,
            [Efeat.DISTANCE],
            targets.REGRESS,
            targets.IRMSD,
            False,
            None,
            "mcl",
        )

    def test_naive(self):
        _model_base_test(
            NaiveNetwork,
            "tests/data/hdf5/test.hdf5",
            "tests/data/hdf5/test.hdf5",
            "tests/data/hdf5/test.hdf5",
            default_features,
            [Efeat.DISTANCE],
            targets.REGRESS,
            "BA",
            False,
            [OutputExporter(self.work_directory)],
            "mcl",
        )

    def test_incompatible_regression(self):
        with pytest.raises(ValueError):
            _model_base_test(
                SGAT,
                "tests/data/hdf5/1ATN_ppi.hdf5",
                "tests/data/hdf5/1ATN_ppi.hdf5",
                "tests/data/hdf5/1ATN_ppi.hdf5",
                default_features,
                [Efeat.DISTANCE],
                targets.REGRESS,
                targets.IRMSD,
                False,
                [TensorboardBinaryClassificationExporter(self.work_directory)],
                "mcl",
            )

    def test_incompatible_classification(self):
        with pytest.raises(ValueError):
            _model_base_test(
                GINet,
                "tests/data/hdf5/variants.hdf5",
                "tests/data/hdf5/variants.hdf5",
                "tests/data/hdf5/variants.hdf5",
                [Nfeat.RESSIZE, Nfeat.POLARITY, Nfeat.SASA, Nfeat.INFOCONTENT, Nfeat.PSSM],
                [Efeat.DISTANCE],
                targets.CLASSIF,
                targets.BINARY,
                False,
                [ScatterPlotExporter(self.work_directory)],
                "mcl",
            )

    def test_incompatible_no_pretrained_no_train(self):
        with pytest.raises(ValueError):

            dataset = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
            )

            Trainer(
                neuralnet = NaiveNetwork,
                dataset_test = dataset,
            )

    def test_incompatible_no_pretrained_no_Net(self):
        with pytest.raises(ValueError):
            dataset = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
            )

            Trainer(
                neuralnet = NaiveNetwork,
                dataset_train = dataset,
            )

    def test_incompatible_no_pretrained_no_target(self):
        with pytest.raises(ValueError):
            dataset = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
            )

            Trainer(
                dataset_train = dataset,
            )

    def test_incompatible_pretrained_no_test(self):
        with pytest.raises(ValueError):
            dataset = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
            )

            trainer = Trainer(
                neuralnet = GINet,
                dataset_train = dataset,
            )

            with warnings.catch_warnings(record=UserWarning):
                trainer.train(nepoch=3, validate=True)
                trainer.save_model("test.pth.tar")

                Trainer(
                    neuralnet = GINet,
                    dataset_train = dataset,
                    pretrained_model="test.pth.tar")

    def test_incompatible_pretrained_no_Net(self):
        with pytest.raises(ValueError):
            dataset = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
            )

            trainer = Trainer(
                neuralnet = GINet,
                dataset_train = dataset,
            )

            with warnings.catch_warnings(record=UserWarning):
                trainer.train(nepoch=3, validate=True)
                trainer.save_model("test.pth.tar")

                Trainer(
                    dataset_test = dataset,
                    pretrained_model="test.pth.tar")

    def test_no_valid_provided(self):

        dataset = GraphDataset(
            hdf5_path="tests/data/hdf5/test.hdf5",
            target=targets.BINARY,
        )

        trainer = Trainer(
            neuralnet = GINet,
            dataset_train = dataset,
            batch_size = 1
        )

        assert len(trainer.train_loader) == int(0.75 * len(dataset))
        assert len(trainer.valid_loader) == int(0.25 * len(dataset))

    def test_no_valid_full_train(self):

        dataset = GraphDataset(
            hdf5_path="tests/data/hdf5/test.hdf5",
            target=targets.BINARY,
        )

        trainer = Trainer(
            neuralnet = GINet,
            dataset_train = dataset,
            val_size = 0,
            batch_size = 1
        )

        assert len(trainer.train_loader) == len(dataset)
        assert trainer.valid_loader is None

    def test_optim(self):

        dataset = GraphDataset(
            hdf5_path="tests/data/hdf5/test.hdf5",
            target=targets.BINARY,
        )

        trainer = Trainer(
            neuralnet = NaiveNetwork,
            dataset_train = dataset,
        )

        optimizer = torch.optim.Adamax
        lr = 0.1
        weight_decay = 1e-04

        trainer.configure_optimizers(optimizer, lr, weight_decay)

        assert isinstance(trainer.optimizer, optimizer)
        assert trainer.lr == lr
        assert trainer.weight_decay == weight_decay

        with warnings.catch_warnings(record=UserWarning):
            trainer.train(nepoch=3, validate=True)
            trainer.save_model("test.pth.tar")

            trainer_pretrained = Trainer(
                neuralnet = NaiveNetwork,
                dataset_test=dataset,
                pretrained_model="test.pth.tar")

        assert isinstance(trainer_pretrained.optimizer, optimizer)
        assert trainer_pretrained.lr == lr
        assert trainer_pretrained.weight_decay == weight_decay

    def test_default_optim(self):

        dataset = GraphDataset(
            hdf5_path="tests/data/hdf5/test.hdf5",
            target=targets.BINARY,
        )

        trainer = Trainer(
            neuralnet = NaiveNetwork,
            dataset_train = dataset,
        )

        assert isinstance(trainer.optimizer, torch.optim.Adam)
        assert trainer.lr == 0.001
        assert trainer.weight_decay == 1e-05

    def test_cuda(self):    # test_ginet, but with cuda
        if torch.cuda.is_available():

            _model_base_test(           
                GINet,
                "tests/data/hdf5/1ATN_ppi.hdf5",
                "tests/data/hdf5/1ATN_ppi.hdf5",
                "tests/data/hdf5/1ATN_ppi.hdf5",
                default_features,
                [Efeat.DISTANCE],
                targets.REGRESS,
                targets.IRMSD,
                False,
                [OutputExporter(self.work_directory)],
                "mcl",
                True
            )

            assert len(os.listdir(self.work_directory)) > 0

        else:
            warnings.warn("CUDA NOT AVAILABLE. test_cuda skipped")
            _log.debug("cuda is not available, test_cuda skipped")

    def test_dataset_equivalence_no_pretrained(self):
        with pytest.raises(ValueError):
            dataset_train = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
                edge_features=[Efeat.DISTANCE, Efeat.COVALENT]
            )
            
            dataset_val = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
                edge_features=[Efeat.DISTANCE]
            )

            Trainer(
                neuralnet = GINet,
                dataset_train = dataset_train,
                dataset_val = dataset_val,
            )

    def test_dataset_equivalence_pretrained(self):
        with pytest.raises(ValueError):
            dataset_train = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
                edge_features=[Efeat.DISTANCE, Efeat.COVALENT]
            )
            
            dataset_test = GraphDataset(
                hdf5_path="tests/data/hdf5/test.hdf5",
                target=targets.BINARY,
                edge_features=[Efeat.DISTANCE]
            )

            trainer = Trainer(
                neuralnet = GINet,
                dataset_train = dataset_train,
            )

            with warnings.catch_warnings(record=UserWarning):
                trainer.train(nepoch=3, validate=True)
                trainer.save_model("test.pth.tar")

                Trainer(
                    neuralnet = GINet,
                    dataset_train = dataset_train,
                    dataset_test = dataset_test,
                    pretrained_model="test.pth.tar")


if __name__ == "__main__":
    unittest.main()
