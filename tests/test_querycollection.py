from tempfile import mkdtemp
from shutil import rmtree
from os.path import join
import h5py
from deeprankcore.features import surfacearea
from deeprankcore.query import SingleResidueVariantResidueQuery, QueryCollection, Query
from deeprankcore.domain.aminoacidlist import alanine, phenylalanine
from . import PATH_TEST


def querycollection_tester(n_queries = 10, feature_modules = None, cpu_count = 1, combine_output = True):
    """
    Generic function to test QueryCollection class.

    Args:
        n_queries: number of queries to be generated.

        feature_modules: list of feature modules (from .deeprankcore.features) to be passed to process.
            If None, all available modules in deeprankcore.features are used to generate the features.
        
        cpu_count: number of cpus to be used during the queries processing.

        combine_output: boolean for combining the hdf5 files generated by the processes.
            By default, the hdf5 files generated are combined into one, and then deleted.
    """

    output_directory = mkdtemp()
    prefix = join(output_directory, "test-process-queries")
    collection = QueryCollection()

    try:
        for number in range(1, n_queries + 1):
            collection.add(SingleResidueVariantResidueQuery(
                str(PATH_TEST / "data/pdb/101M/101M.pdb"),
                "A",
                number,
                None,
                alanine,
                phenylalanine,
                pssm_paths={"A": str(PATH_TEST / "data/pssm/101M/101M.A.pdb.pssm")},
                ))

        output_paths = collection.process(prefix, feature_modules, cpu_count, combine_output)
        assert len(output_paths) > 0

        graph_names = []
        for path in output_paths:
            with h5py.File(path, "r") as f5:
                graph_names += list(f5.keys())

        for query in collection.queries:
            query_id = query.get_query_id()
            assert query_id in graph_names, f"missing in output: {query_id}"

    except Exception as e:
        print(e)

    return collection, output_directory, output_paths


def test_querycollection_process():
    """
    Tests processing method of QueryCollection class.
    """

    n_queries = 5

    collection, output_directory, _ = querycollection_tester(n_queries)
    
    assert isinstance(collection.queries, list)
    assert len(collection.queries) == n_queries
    for query in collection.queries:
        assert issubclass(type(query), Query)

    rmtree(output_directory)


def test_querycollection_process_single_feature_module():
    """
    Tests processing for generating a single feature.
    """

    # test with single feature in list
    feature_modules = [surfacearea]
    _, output_directory, _ = querycollection_tester(feature_modules = feature_modules)
    rmtree(output_directory)

    # test with single feature NOT in list
    feature_modules = surfacearea
    _, output_directory, _ = querycollection_tester(feature_modules = feature_modules)
    rmtree(output_directory)


def test_querycollection_process_all_features_modules():
    """
    Tests processing for generating all features.
    """

    _, output_directory, _ = querycollection_tester()

    rmtree(output_directory)


def test_querycollection_process_combine_output_true():
    """
    Tests processing for combining hdf5 files into one.
    """

    _, output_directory_t, output_paths_t = querycollection_tester()

    _, output_directory_f, output_paths_f = querycollection_tester(combine_output = False)

    assert len(output_paths_t) == 1

    keys_t = {}
    with h5py.File(output_paths_t[0],'r') as file_t:
        for key, value in file_t.items():
            keys_t[key] = value

    keys_f = {}
    for output_path in output_paths_f:
        with h5py.File(output_path,'r') as file_f:
            for key, value in file_f.items():
                keys_f[key] = value

    assert keys_t == keys_f

    rmtree(output_directory_t)
    rmtree(output_directory_f)


def test_querycollection_process_combine_output_false():
    """
    Tests processing for keeping all generated hdf5 files .
    """

    cpu_count = 2
    combine_output = False

    collection, output_directory, output_paths = querycollection_tester(cpu_count = cpu_count, combine_output = combine_output)

    assert len(output_paths) == collection.cpu_count

    rmtree(output_directory)
