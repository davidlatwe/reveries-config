
from maya.api import OpenMaya as om
from ..utils import _C4Hasher


def _hash_MPoint(x, y, z, w):
    x = (x + 1) * 233
    y = (y + x) * 239
    z = (z + y) * 241
    return (x + y + z) * w


def _hash_MFloatVectors(x, y, z):
    x = (x + 1) * 383
    y = (y + x) * 389
    z = (z + y) * 397
    return x + y + z


def _hash_UV(u, v):
    u = (u + 1) * 547
    v = (v + u) * 557
    return u * v


class MeshHasher(object):
    """A mesh geometry hasher for Maya

    For quickly identifying if any change on vertices, normals and UVs.
    Hash value will be encoded as Avalanche-io C4 Asset ID.

    Order matters, transform does not.

    Example Usage:
        >> hasher = MeshHasher()
        >> hasher.set_mesh("path|to|mesh")
        >> hasher.update_points()
        >> hasher.update_normals()
        >> hasher.update_uvmap()
        >> hasher.digest()
        {'normals': 'c41MSCnAGqWS9dBDDpydbpcMwzzFkGH66jNpuTqctfY...',
         'points': 'c44fV5wa6bNiekUadZ4HsRPDL2HZ11RFKcXhf3pntsUJ...',
         'uvmap': 'c45JRQTPxgMNYfcijAbm31vkJRt6CUUSn7ew2X1Mnyjwi...'}

        Hash meshes in loop
        >> for mesh in cmds.ls(type="mesh", ni=Ture, long=True)
        ...    hasher.set_mesh(mesh)
        ...    hasher.update_points()
        ...    hasher.update_normals()
        ...
        >> hasher.digest()
        {'normals': 'c456rBNH5pzobqjHzFnHApanrTdJo64r2R8o4GJxqU9G...',
         'points': 'c449wXhjNSSKfnUjPp2ub3fd1DeNowW2x5gBJDYrSvxrT...'}

        You can still adding more meshes until you call `clear`
        >> hasher.clear()

    """

    def __init__(self):
        self.clear()

    def clear(self):
        self._mesh = None
        self._points = 0
        self._normals = 0
        self._uvmap = 0

    def set_mesh(self, dag_path):
        """Set one mesh geometry node to hasher

        Arguments:
            dag_path (str): Mesh node's DAG path

        """
        sel_list = om.MSelectionList()
        sel_list.add(dag_path)
        sel_obj = sel_list.getDagPath(0)
        self._mesh = om.MFnMesh(sel_obj)

    def update_points(self):
        for i, vt in enumerate(self._mesh.getPoints()):
            self._points += _hash_MPoint(*vt) + i

    def update_normals(self):
        for i, vt in enumerate(self._mesh.getNormals()):
            self._normals += _hash_MFloatVectors(*vt) + i

    def update_uvmap(self, uv_set=""):
        for i, uv in enumerate(zip(*self._mesh.getUVs(uv_set))):
            self._uvmap += _hash_UV(*uv) + i

    def digest(self):
        result = dict()
        hasher = _C4Hasher()

        if self._points:
            hasher.hash_obj.update(str(self._points))
            result["points"] = hasher.digest()
            hasher.clear()

        if self._normals:
            hasher.hash_obj.update(str(self._normals))
            result["normals"] = hasher.digest()
            hasher.clear()

        if self._uvmap:
            hasher.hash_obj.update(str(self._uvmap))
            result["uvmap"] = hasher.digest()
            hasher.clear()

        return result
