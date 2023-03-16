from pdb2sql import pdb2sql
import numpy as np
from deeprankcore.domain.aminoacidlist import alanine
from deeprankcore.molstruct.structure import PDBStructure, Chain
from deeprankcore.molstruct.residue import Residue
from deeprankcore.molstruct.variant import SingleResidueVariant
from deeprankcore.features.secondary_structure import add_features
from deeprankcore.utils.graph import build_residue_graph, build_atomic_graph
from deeprankcore.utils.buildgraph import (
    get_structure,
    get_residue_contact_pairs,
    get_surrounding_residues)
from deeprankcore.domain import nodestorage as Nfeat

def _load_pdb_structure(pdb_path: str, id_: str) -> PDBStructure:
    """
    Load PDB structure from a PDB file.

    Args:
        pdb_path (str): The file path of the PDB file.
        id_ (str): The PDB structure ID.

    Returns:
        PDBStructure: The loaded PDB structure.
    """
    pdb = pdb2sql(pdb_path)
    try:
        return get_structure(pdb, id_)
    finally:
        pdb._close()  # pylint: disable=protected-access


def test_secondary_structure_residue():
    # Load test PDB file and create a residue graph
    pdb_path = "tests/data/pdb/1ak4/1ak4.pdb"
    structure = _load_pdb_structure(pdb_path, "1ak4")
    residues = structure.chains[0].residues + structure.chains[1].residues
    graph = build_residue_graph(residues, "1ak4", 8.5)

    # Add secondary structure features to the graph nodes
    add_features(pdb_path, graph)

    # Create a list of node information (residue number, chain ID, and secondary structure features)
    node_info_list = [[node.id.number, node.id.chain.id, node.features['ss']] for node in graph.nodes]
    node_info_list.sort()

    # Check if the sum of secondary structure features equals 1.0 for all nodes
    assert np.any(
        node.features['ss'].sum() == 1.0 for node in graph.nodes
    )

    # Check example 1
    assert node_info_list[0][0] == 1
    assert node_info_list[0][1] == 'D'
    assert np.array_equal(node_info_list[0][2], np.array([0., 0., 1.]))

    # Check example 2
    assert node_info_list[255][0] == 129
    assert node_info_list[255][1] == 'C'
    assert np.array_equal(node_info_list[255][2], np.array([0., 1., 0.]))

    # Check example 3
    assert node_info_list[226][0] == 114
    assert node_info_list[226][1] == 'D'
    assert np.array_equal(node_info_list[226][2], np.array([1., 0., 0.]))
