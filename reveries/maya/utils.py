
import os
import uuid
import hashlib

try:
    import bson
except ImportError:
    pass

from datetime import datetime

import maya.cmds as cmds
from maya.api import OpenMaya as om
from ..utils import _C4Hasher
from .lib import AVALON_ID_ATTR_LONG, hasAttr


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


def remove_unused_plugins():
    """Remove unused plugin from scene

    This will prevent Maya from saving redundant requires into scene file.

    (Copied from Maya support page)
    Maya is not cleaning up requires statements for unused plugins:

    Issue:
        When a plugin is used in Maya 2016, it puts a 'requires' statement
        into the header of the Maya File, akin to: requires "XZY" "1.30"
        When the plugin is subsequently deleted out of the Maya file and
        the Maya file is saved, the requires statement is left in the file.

    Causes:
        It creates extra lines of garbage code which makes the file larger
        and more clutter when files are being diagnosed

    Solution:
        Autodesk introduced one new command unknownPlugin which could be used
        to remove the "requires" line from the file if the plug-in is unknown
        to Maya 2016.

    """
    for plugin in cmds.unknownPlugin(query=True, list=True):
        cmds.unknownPlugin(plugin, remove=True)


def kill_turtle():
    """Ensure the Turtle plugin is not loaded"""

    turtle_nodes = (
        "TurtleDefaultBakeLayer",
        "TurtleBakeLayerManager",
        "TurtleUIOptions",
        "TurtleRenderOptions",
    )

    for node in turtle_nodes:
        if not cmds.objExists(node):
            continue
        cmds.lockNode(node, lock=False)
        cmds.delete(node)

    cmds.unloadPlugin("Turtle", force=True)


def _get_attr(node, attr):
    """Internal function for attribute getting
    """
    try:
        return cmds.getAttr(node + "." + attr)
    except ValueError:
        return None


def _add_attr(node, attr):
    """Internal function for attribute adding
    """
    if not hasAttr(node, attr):
        cmds.addAttr(node, longName=attr, dataType="string")


def _set_attr(node, attr, value):
    """Internal function for attribute setting
    """
    try:
        cmds.setAttr(node + "." + attr, value, type="string")
    except RuntimeError:
        # Attribute not existed
        pass


class Identifier(object):

    Clean = 0
    Duplicated = 1
    Untracked = 2

    ATTR_ADDRESS = AVALON_ID_ATTR_LONG
    ATTR_VERIFIER = "verifier"

    def read_address(self, node):
        """Read address value from node

        Arguments:
            node (str): Maya node name

        """
        return _get_attr(node, self.ATTR_ADDRESS)

    def read_verifier(self, node):
        """Read verifier value from node

        Arguments:
            node (str): Maya node name

        """
        return _get_attr(node, self.ATTR_VERIFIER)

    def read_uuid(self, node):
        """Read uuid value from node

        Arguments:
            node (str): Maya node name

        """
        muuid = cmds.ls(node, uuid=True)
        if not len(muuid):
            raise RuntimeError("Node not found.")
        elif len(muuid) > 1:
            raise RuntimeError("Found more then one node, use long name.")

        return muuid[0]

    def _generate_address(self):
        """Internal function for generating time-embedded ID address

        Note:
            `bson.ObjectId` is about 1 time faster then `uuid.uuid1`.

        """
        try:
            return str(bson.ObjectId())  # bson is faster
        except NameError:
            return str(uuid.uuid1())[:-18]  # remove mac-addr

    def _generate_verifier(self, muuid, address):
        """Internal function for generating hash value from Maya UUID and address

        Arguments:
            muuid (str): Maya UUID string
            address (str): Previous generated address id from node

        Note:
            Faster then uuid5.

        """
        hasher = hashlib.sha1()
        hasher.update(muuid + ":" + address)
        return hasher.hexdigest()

    def status(self, node):
        """Report `node` current state

        Return node state flag (int), in range 0 - 3:
            0 == Identifier.Clean
            1 == Identifier.Duplicated
            2 == Identifier.Untracked

        Arguments:
            node (str): Maya node name

        Returns:
            (int): Node state flag

        """
        address = self.read_address(node)
        verifier = self.read_verifier(node)

        if not all((address, verifier)):
            # Node did not have the attributes for verification,
            # this is new node.
            return self.Untracked
        else:
            if verifier == self._generate_verifier(self.read_uuid(node),
                                                   address):
                return self.Clean
            else:
                return self.Duplicated

    def on_track(self, node):
        """Update node's address

        MUST do this if `status` return flag `api.Untracked`.

        Arguments:
            node (str): Maya node name

        """
        address = self._generate_address()
        _add_attr(node, self.ATTR_ADDRESS)
        _set_attr(node, self.ATTR_ADDRESS, address)
        self.on_duplicate(node)

    def on_duplicate(self, node):
        """Update node's verifier

        MUST do this if `status` return flag `api.Duplicated`.

        Arguments:
            node (str): Maya node name
            fingerprint (str): Maya node's hash value

        """
        address = self.read_address(node)
        if address is None:
            return

        verifier = self._generate_verifier(self.read_uuid(node), address)
        _add_attr(node, self.ATTR_VERIFIER)
        _set_attr(node, self.ATTR_VERIFIER, verifier)

    __action_map = {
        Clean: (lambda n: None),
        Duplicated: on_track,
        Untracked: on_track,
    }

    def manage(self, node, state):
        """Auto update node's identity attributes by input state

        Arguments:
            node (str): Maya node name
            state (int): State flag returned from `status`

        """
        action = self.__action_map[state]
        action(self, node)

    def update_verifiers(self, nodes):
        """Update input nodes' verifier

        MUST do this on file-import.

        Arguments:
            nodes (list): A list of Maya node name

        """
        for node in nodes:
            self.on_duplicate(node)

    def get_time(self, node):
        """Retrive datetime object from Maya node

        A little bonus gained from datetime embedded id.

        Arguments:
            node (str): Maya node name

        """
        address = self.read_address(node)
        if address is None:
            return None

        if "-" in address:
            _ut = uuid.UUID(address + "-0000-000000000000").time
            stm = (_ut - 0x01b21dd213814000) * 100 / 1e9
            time = datetime.fromtimestamp(stm)
        else:
            time = bson.ObjectId(address).generation_time

        return time


_identifier = Identifier()


def set_avalon_uuid(node):
    """Add or renew avID ( Avalon ID ) to `node`
    """
    status = _identifier.status(node)
    _identifier.manage(node, status)


def get_id(node):
    """
    Get the `AvalonID` attribute of the given node
    Args:
        node (str): the name of the node to retrieve the attribute from

    Returns:
        str

    """
    return _identifier.read_address(node)


def get_id_status(node):
    return _identifier.status(node)


def set_transform_id():
    nodes = (set(cmds.ls(type="transform", long=True)) -
             set(cmds.ls(long=True, readOnly=True)) -
             set(cmds.ls(long=True, lockedNodes=True)))

    for node in nodes:
        status = _identifier.status(node)
        _identifier.manage(node, status)


def update_id_on_import(nodes):
    _identifier.update_verifiers(nodes)


def generate_container_id():
    hasher = hashlib.sha1()
    hasher.update(os.urandom(40))
    return "CON" + hasher.hexdigest()
