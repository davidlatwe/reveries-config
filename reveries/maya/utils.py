
import os
import uuid
import hashlib

try:
    import bson
except ImportError:
    pass

from datetime import datetime

from avalon import io

from maya import cmds, mel
from maya.api import OpenMaya as om
from ..utils import _C4Hasher, get_representation_path_
from .pipeline import get_interface_from_container, env_embedded_path
from . import lib, capsule


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
    if lib.hasAttrExact(node, attr):
        return cmds.getAttr(node + "." + attr)
    else:
        return None


def _add_attr(node, attr):
    """Internal function for attribute adding
    """
    if not lib.hasAttrExact(node, attr):
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

    ATTR_ADDRESS = lib.AVALON_ID_ATTR_LONG
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
        Clean: (lambda self, n: None),
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


def set_id(node, id):
    _add_attr(node, lib.AVALON_ID_ATTR_LONG)
    _set_attr(node, lib.AVALON_ID_ATTR_LONG, str(id))
    _identifier.on_duplicate(node)


def update_id_verifiers(nodes):
    _identifier.update_verifiers(nodes)


def generate_container_id():
    hasher = hashlib.sha1()
    hasher.update(os.urandom(40))
    return "CON" + hasher.hexdigest()


def get_renderer_by_layer(layer=None):
    layer = layer or get_current_renderlayer()
    return lib.query_by_renderlayer("defaultRenderGlobals",
                                    "currentRenderer",
                                    layer)


def get_current_renderlayer():
    return cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)


def get_render_filename_prefix(layer=None):
    renderer = get_renderer_by_layer(layer)

    if renderer == "vray":
        return lib.query_by_renderlayer("vraySettings",
                                        "fileNamePrefix",
                                        layer)
    else:
        prefix = lib.query_by_renderlayer("defaultRenderGlobals",
                                          "imageFilePrefix",
                                          layer)
        if prefix and renderer == "arnold" and "<RenderPass>" not in prefix:
            prefix = "/".join(["<RenderPass>", prefix])

        return prefix


def get_render_resolution(layer=None):
    renderer = get_renderer_by_layer(layer)

    if renderer == "vray":
        width = lib.query_by_renderlayer("vraySettings",
                                         "width",
                                         layer)
        height = lib.query_by_renderlayer("vraySettings",
                                          "height",
                                          layer)
    else:
        width = lib.query_by_renderlayer("defaultResolution",
                                         "width",
                                         layer)
        height = lib.query_by_renderlayer("defaultResolution",
                                          "height",
                                          layer)
    return width, height


def compose_render_filename(layer, renderpass="", camera="", on_frame=None):
    """
    """
    renderer = get_renderer_by_layer(layer)
    prefix = get_render_filename_prefix(layer) or ""
    multi_render_cams = len(lib.ls_renderable_cameras(layer)) > 1
    has_renderlayers = lib.ls_renderable_layers() != ["defaultRenderLayer"]
    is_animated = cmds.getAttr("defaultRenderGlobals.animation")
    padding_str = ""
    scene_name = cmds.file(query=True,
                           sceneName=True,
                           shortName=True).rsplit(".", 1)[0]

    # (NOTE) There's another *Deep EXR* in both VRay("exr (deep)") and
    #   Arnold("deepexr"), it's not being handled here since it's a rarely
    #   used format.

    if renderer == "vray":
        from . import vray

        if not cmds.objExists("vraySettings"):
            vray.utils.create_vray_settings()

        ext, is_multichannel_exr = vray.utils.get_vray_output_image_format()

        separate_folders = cmds.getAttr("vraySettings"
                                        ".relements_separateFolders")
        separate_rgba = cmds.getAttr("vraySettings"
                                     ".relements_separateRGBA")

        prefix = prefix or scene_name

        if renderpass and separate_folders:
            head, tail = os.path.split(prefix)
            prefix = "/".join([head, renderpass, tail])

        elif not renderpass and separate_folders and separate_rgba:
            head, tail = os.path.split(prefix)
            prefix = "/".join([head, "rgba", tail])

        # Put <Camera> tag if having multiple renderable cameras and
        # <Camera> tag not in prefix
        if (multi_render_cams and
                not any(t in prefix for t in ["<Camera>", "<camera>", "%c"])):
            prefix = "/".join(["<Camera>", prefix])

        # Put <Layer> tag if having multiple renderlayers and
        # <Layer> tag not in prefix
        if (has_renderlayers and
                not any(t in prefix for t in ["<Layer>", "<layer>", "%l"])):
            prefix = "/".join(["<Layer>", prefix])

        # Don't transform if the prefix is blank, so we can just default to
        # the scene file name.
        if prefix:
            for tag in ("<Layer>", "<layer>", "%l"):
                # We need to replace renderlayer tag by ourself if we don't
                # switch renderlayer.
                prefix = prefix.replace(tag, lib.pretty_layer_name(layer))
            prefix = mel.eval("vrayTransformFilename("
                              "\"{0}\", \"{1}\", \"{2}\", 0, 0, 0)"
                              "".format(prefix, camera, scene_name))

        pass_sep = cmds.getAttr("vraySettings"
                                ".fileNameRenderElementSeparator")
        if renderpass and not is_multichannel_exr:
            prefix = prefix + pass_sep + renderpass

        elif (not renderpass and separate_folders and
                separate_rgba and not is_multichannel_exr):
            prefix = prefix + pass_sep + "rgba"

        if is_animated:
            padding_str = "#" * cmds.getAttr("vraySettings.fileNamePadding")

            # When rendering to a non-raw format, vray places a period before
            # the padding, even though it doesn't show up in the render
            # globals filename.
            if ext == "vrimg":
                output_prefix = prefix + padding_str + "." + ext
            else:
                output_prefix = prefix + "." + padding_str + "." + ext
        else:
            output_prefix = prefix + "." + ext

    else:
        # Not VRay

        current_prefix = prefix
        prefix = prefix or scene_name

        if renderer == "arnold" and "<RenderPass>" not in prefix:
            from . import arnold
            aov_names = arnold.utils.get_arnold_aov_names(layer)
            if aov_names:
                prefix = "/".join(["<RenderPass>", prefix])

        # Put <Camera> tag if having multiple renderable cameras and
        # <Camera> tag not in prefix
        if (multi_render_cams and
                not any(t in prefix for t in ["<Camera>", "%c"])):
            prefix = "/".join(["<Camera>", prefix])

        # Put <RenderLayer> tag if having multiple renderlayers and
        # <RenderLayer> tag not in prefix
        if (has_renderlayers and
                not any(t in prefix
                        for t in ["<RenderLayer>", "<Layer>", "%l"])):
            prefix = "/".join(["<RenderLayer>", prefix])

        padding_str = "#" * cmds.getAttr("defaultRenderGlobals"
                                         ".extensionPadding")

        with capsule.maintained_modification():
            cmds.setAttr("defaultRenderGlobals.imageFilePrefix",
                         prefix,
                         type="string")

            output_prefix = cmds.renderSettings(
                genericFrameImageName=padding_str,
                layer=layer,
                camera=camera,
                customTokenString="RenderPass=" + renderpass)[0]

            cmds.setAttr("defaultRenderGlobals.imageFilePrefix",
                         current_prefix,
                         type="string")

    if is_animated and on_frame is not None:
        frame_str = "%%0%dd" % len(padding_str) % on_frame
        output_prefix = output_prefix.replace(padding_str, frame_str)

    return output_prefix


def update_dependency(container):
    """Update subset data and references

    This is for updating dependencies and relink them to assets in current
    project for the loaded subset that was originally moved from other project.

    You need to manually update the representation id value in container before
    using this function.

    """

    representation_id = cmds.getAttr(container + ".representation")
    representation_id = io.ObjectId(representation_id)

    representation = io.find_one({"_id": representation_id})

    if representation is None:
        raise Exception("Representation not found.")

    version, subset, asset, project = io.parenthood(representation)

    interface = get_interface_from_container(container)

    cmds.setAttr(interface + ".assetId", str(asset["_id"]), type="string")
    cmds.setAttr(interface + ".subsetId", str(subset["_id"]), type="string")
    cmds.setAttr(interface + ".versionId", str(version["_id"]), type="string")

    # Update Reference path
    reference_node = next(iter(cmds.ls(cmds.sets(container, query=True),
                                       type="reference")), None)

    if reference_node is None:
        # No reference to update
        return

    package_path = get_representation_path_(representation,
                                            (version, subset, asset, project))

    file_type = representation["name"]
    if file_type == "FBXCache":
        file_type = "FBX"
    elif file_type in ("GPUCache", "LookDev"):
        file_type = "MayaAscii"

    file_name = representation["data"]["entryFileName"]
    entry_path = os.path.join(package_path, file_name)

    if not os.path.isfile(entry_path):
        raise IOError("File Not Found: {!r}".format(entry_path))

    entry_path = env_embedded_path(entry_path)

    cmds.file(entry_path,
              loadReference=reference_node,
              type=file_type,
              defaultExtensions=False)
