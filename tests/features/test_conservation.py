from pdb2sql import pdb2sql
import numpy as np
from deeprankcore.domain import nodestorage as Nfeat
from deeprankcore.domain.aminoacidlist import alanine
from deeprankcore.utils.parsing.pssm import parse_pssm
from deeprankcore.molstruct.variant import SingleResidueVariant
from deeprankcore.features.conservation import add_features
from deeprankcore.utils.graph import build_atomic_graph
from deeprankcore.utils.buildgraph import get_structure, get_surrounding_residues



def test_add_features():

    pdb_path = "tests/data/pdb/101M/101M.pdb"

    pdb = pdb2sql(pdb_path)
    try:
        structure = get_structure(pdb, "101m")
    finally:
        pdb._close() # pylint: disable=protected-access

    chain = structure.get_chain("A")
    with open("tests/data/pssm/101M/101M.A.pdb.pssm", "rt", encoding="utf-8") as f:
        chain.pssm = parse_pssm(f, chain)

    variant_residue = chain.residues[25]

    variant = SingleResidueVariant(variant_residue, alanine)

    residues = get_surrounding_residues(structure, variant_residue, 10.0)
    atoms = set([])
    for residue in residues:
        for atom in residue.atoms:
            atoms.add(atom)
    atoms = list(atoms)
    assert len(atoms) > 0

    graph = build_atomic_graph(atoms, "101M-25-atom", 4.5)
    add_features(pdb_path, graph, variant)

    for feature_name in (
        Nfeat.PSSM,
        Nfeat.DIFFCONSERVATION,
        Nfeat.CONSERVATION,
        Nfeat.INFOCONTENT,
    ):
        assert np.any([node.features[feature_name] != 0.0 for node in graph.nodes])