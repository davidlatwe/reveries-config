
from maya.api import OpenMaya as om
from ..utils import _C4Hasher


class MeshHasher(_C4Hasher):
    """A mesh geometry hasher for Maya

    Based on Avalanche-io C4 Asset ID, hashing mesh geometry by ipnuting all
    vertices' position.

    Vertex and mesh input order matters, transform does not.

    Usage:
        >> hasher = MeshHasher()
        >> hasher.add_mesh("path|to|mesh")

        You can keep adding more meshes.
        And get the hash value by
        >> hasher.hash()
        'c463d2Wh5NyBMQRHyxbdBxCzZfaKXvBQaawgfgG18moxQU2jdmaSbCWL...'

        You can still adding more meshes at this point
        >> hasher.add_mesh("path|to|more|mesh")

        And get the hash value of all meshes added so far
        >> hasher.hash()
        'c43cysVyTd7kYurvAa5ooR6miJJgUZ9QnBCHZeNK3en9aQ96KHsoJyJX...'

        Until you call `clear`
        >> hasher.clear()

    """

    def add_mesh(self, dag_path):
        """Add one mesh geometry to hasher

        Arguments:
            dag_path (str): Mesh node's DAG path

        """
        sel_list = om.MSelectionList()
        sel_list.add(dag_path)

        sel_obj = sel_list.getDagPath(0)
        mesh = om.MFnMesh(sel_obj)

        for vt in mesh.getPoints():
            pos = "{},{},{}".format(*vt)
            self.hash_obj.update(pos)
