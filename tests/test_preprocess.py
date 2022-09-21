from tempfile import mkdtemp
from shutil import rmtree
import h5py
from deeprankcore.preprocess import preprocess
from deeprankcore.models.query import SingleResidueVariantResidueQuery
from deeprankcore.domain.amino_acid import alanine, phenylalanine
from tests.utils import PATH_TEST
from os.path import basename, isfile, join
import glob
import importlib


def preprocess_tester(feature_modules):
    """
    Generic function to test preprocess for either single or all feature types.
    """

    output_directory = mkdtemp()

    prefix = join(output_directory, "test-preprocess")


    try:
        count_queries = 10
        queries = []
        for number in range(1, count_queries + 1):
            query = SingleResidueVariantResidueQuery(
                str(PATH_TEST / "data/pdb/101M/101M.pdb"),
                "A",
                number,
                None,
                alanine,
                phenylalanine,
                pssm_paths={"A": str(PATH_TEST / "data/pssm/101M/101M.A.pdb.pssm")},
            )
            queries.append(query)

        output_paths = preprocess(feature_modules, queries, prefix, 10)
        assert len(output_paths) > 0

        graph_names = []
        for path in output_paths:
            with h5py.File(path, "r") as f5:
                graph_names += list(f5.keys())

        for query in queries:
            query_id = query.get_query_id()
            assert query_id in graph_names, f"missing in output: {query_id}"

    finally:
        rmtree(output_directory)


def test_preprocess_single_feature():
    """
    Tests preprocessing several PDB files into their feature representation HDF5 file.
    """

    feature_modules = [sasa]
    preprocess_tester(feature_modules)


def test_preprocess_all_features():
    """
    Tests preprocessing several PDB files into their features representation HDF5 file.
    """

    # copying this from feature.__init__.py
    modules = glob.glob(join('./deeprankcore/feature/', "*.py"))
    modules = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]

    feature_modules = []
    for m in modules:
        imp = importlib.import_module('deeprankcore.feature.' + m)
        feature_modules.append(imp)

    preprocess_tester(feature_modules)
