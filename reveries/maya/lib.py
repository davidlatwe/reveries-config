
import logging
import uuid

from maya import cmds
from maya.api import OpenMaya as om

from .. import utils


log = logging.getLogger(__name__)


AVALON_ID_ATTR_LONG = "AvalonID"
AVALON_ID_ATTR_SHORT = "avid"

DEFAULT_MATRIX = [1.0, 0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 0.0, 0.0, 1.0]

TRANSFORM_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
]

CAMERA_SHAPE_KEYABLES = [
    "focalLength",
]


def is_visible(node,
               displayLayer=True,
               intermediateObject=True,
               parentHidden=True,
               visibility=True):
    """Is `node` visible?

    Returns whether a node is hidden by one of the following methods:
    - The node exists (always checked)
    - The node must be a dagNode (always checked)
    - The node's visibility is off.
    - The node is set as intermediate Object.
    - The node is in a disabled displayLayer.
    - Whether any of its parent nodes is hidden.

    Roughly based on: http://ewertb.soundlinker.com/mel/mel.098.php

    Returns:
        bool: Whether the node is visible in the scene

    """

    # Only existing objects can be visible
    if not cmds.objExists(node):
        return False

    # Only dagNodes can be visible
    if not cmds.objectType(node, isAType='dagNode'):
        return False

    if visibility:
        if not cmds.getAttr('{0}.visibility'.format(node)):
            return False

    if intermediateObject and cmds.objectType(node, isAType='shape'):
        if cmds.getAttr('{0}.intermediateObject'.format(node)):
            return False

    if displayLayer:
        # Display layers set overrideEnabled and overrideVisibility on members
        if cmds.attributeQuery('overrideEnabled', node=node, exists=True):
            override_enabled = cmds.getAttr('{}.overrideEnabled'.format(node))
            override_visibility = cmds.getAttr(
                '{}.overrideVisibility'.format(node))
            if override_enabled and not override_visibility:
                return False

    if parentHidden:
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if parents:
            parent = parents[0]
            if not is_visible(parent,
                              displayLayer=displayLayer,
                              intermediateObject=False,
                              parentHidden=parentHidden,
                              visibility=visibility):
                return False

    return True


def bake_hierarchy_visibility(nodes, start_frame, end_frame, step=1):
    curve_map = {node: cmds.createNode("animCurveTU",
                                       name=node + "_visibility")
                 for node in cmds.ls(nodes)
                 if cmds.attributeQuery('visibility', node=node, exists=True)}

    # Bake to animCurve
    frame = start_frame
    while frame <= end_frame:
        cmds.currentTime(frame)
        for node, curve in curve_map.items():
            cmds.setKeyframe(curve, time=(frame,), value=is_visible(node))
        frame += step

    # Connect baked result curve
    for node, curve in curve_map.items():
        cmds.connectAttr(curve + ".output", node + ".visibility", force=True)


def set_avalon_uuid(node, renew=False):
    """Add or renew avID ( Avalon ID ) to `node`
    """
    write = False
    attr = "{0}.{1}".format(node, AVALON_ID_ATTR_SHORT)

    if not cmds.objExists(attr):
        write = True
        cmds.addAttr(node, shortName=AVALON_ID_ATTR_SHORT,
                     longName=AVALON_ID_ATTR_LONG, dataType="string")

    if write or renew:
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        cmds.setAttr(attr, uid, type="string")


def get_id(node):
    """
    Get the `AvalonID` attribute of the given node
    Args:
        node (str): the name of the node to retrieve the attribute from

    Returns:
        str

    """

    if node is None:
        return

    if not cmds.attributeQuery(AVALON_ID_ATTR_LONG, node=node, exists=True):
        return

    return cmds.getAttr("{0}.{1}".format(node, AVALON_ID_ATTR_LONG))


FPS_MAP = {
    15: "game",
    23.976: "film",
    24: "film",
    29.97: "ntsc",
    30: "ntsc",
    48: "show",
    50: "palf",
    60: "ntscf",
}


def set_scene_timeline():
    log.info("Timeline setting...")

    start_frame, end_frame, fps = utils.compose_timeline_data()
    fps = FPS_MAP.get(fps)

    if fps is None:
        raise ValueError("Unsupported FPS value: {}".format(fps))

    cmds.currentUnit(time=fps)
    cmds.playbackOptions(animationStartTime=start_frame)
    cmds.playbackOptions(minTime=start_frame)
    cmds.playbackOptions(animationEndTime=end_frame)
    cmds.playbackOptions(maxTime=end_frame)
    cmds.currentTime(start_frame)


def node_type_check(node, node_type):
    shape = node
    if cmds.objectType(node) == "transform":
        if node_type == "transform":
            return True
        shape = cmds.listRelatives(node, shape=True)
    if shape is not None and cmds.objectType(shape) == node_type:
        return True
    return False


def bake_to_worldspace(node, startFrame, endFrame, bake_shape=True):
    """Bake transform to worldspace
    """
    if not cmds.objectType(node) == "transform":
        raise TypeError("{} is not a transform node.".format(node))

    has_parent = False
    if cmds.listRelatives(node, parent=True):
        name = node + "_bakeHelper"
        new_node = cmds.duplicate(node,
                                  name=name,
                                  returnRootsOnly=True,
                                  inputConnections=True)

        # delete doublicated children
        children = cmds.listRelatives(new_node, children=True, path=True)
        cmds.delete(children)

        # unparent object, add constraints and append it to bake List
        cmds.parent(node, world=True)
        cmds.parentConstraint(new_node, node, maintainOffset=False)
        cmds.scaleConstraint(new_node, node, maintainOffset=False)
        has_parent = True

    # bake Animation and delete Constraints
    cmds.bakeResults(node, time=(startFrame, endFrame),
                     simulation=True,
                     shape=bake_shape)
    if has_parent:
        constraints = cmds.listRelatives(node, type="constraint")
        cmds.delete(constraints)


def bake_camera(camera, startFrame, endFrame):
    """Bake camera to worldspace
    """
    shape = None
    if cmds.objectType(camera) == "transform":
        transform = camera
        shape = (cmds.listRelatives(camera, shapes=True) or [None])[0]
    elif cmds.objectType(camera) == "camera":
        transform = cmds.listRelatives(camera, parent=True)[0]
        shape = camera

    if shape is None:
        raise TypeError("{} is not a camera.".format(camera))

    # make sure attrs all keyable
    cmds.setAttr(transform + ".visibility", keyable=True, lock=False)
    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(transform + "." + attr, keyable=True, lock=False)
    for attr in CAMERA_SHAPE_KEYABLES:
        cmds.setAttr(shape + "." + attr, keyable=True, lock=False)

    bake_to_worldspace(transform, startFrame, endFrame)


def lock_transform(node):
    if not cmds.objectType(node) == "transform":
        raise TypeError("{} is not a transform node.".format(node))

    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(node + "." + attr, lock=True)


def serialise_shaders(nodes):
    """Generate a shader set dictionary

    Arguments:
        nodes (list): Absolute paths to nodes

    Returns:
        dictionary of (shader: id) pairs

    Schema:
        {
            "shader1": ["id1", "id2"],
            "shader2": ["id3", "id1"]
        }

    Example:
        {
            "Bazooka_Brothers01_:blinn4SG": [
                "f9520572-ac1d-11e6-b39e-3085a99791c9.f[4922:5001]",
                "f9520572-ac1d-11e6-b39e-3085a99791c9.f[4587:4634]",
                "f9520572-ac1d-11e6-b39e-3085a99791c9.f[1120:1567]",
                "f9520572-ac1d-11e6-b39e-3085a99791c9.f[4251:4362]"
            ],
            "lambert2SG": [
                "f9520571-ac1d-11e6-9dbb-3085a99791c9"
            ]
        }

    """

    valid_nodes = cmds.ls(
        nodes,
        long=True,
        recursive=True,
        showType=True,
        objectsOnly=True,
        type="transform"
    )

    meshes_by_id = {}
    for mesh in valid_nodes:
        shapes = cmds.listRelatives(valid_nodes[0],
                                    shapes=True,
                                    fullPath=True) or list()

        if shapes:
            shape = shapes[0]
            if not cmds.nodeType(shape):
                continue

            try:
                id_ = cmds.getAttr(mesh + "." + AVALON_ID_ATTR_SHORT)

                if id_ not in meshes_by_id:
                    meshes_by_id[id_] = list()

                meshes_by_id[id_].append(mesh)

            except ValueError:
                continue

    meshes_by_shader = dict()
    for id_, mesh in meshes_by_id.items():
        shape = cmds.listRelatives(mesh,
                                   shapes=True,
                                   fullPath=True) or list()

        for shader in cmds.listConnections(shape,
                                           type="shadingEngine") or list():

            # Objects in this group are those that haven't got
            # any shaders. These are expected to be managed
            # elsewhere, such as by the default model loader.
            if shader == "initialShadingGroup":
                continue

            if shader not in meshes_by_shader:
                meshes_by_shader[shader] = list()

            shaded = cmds.sets(shader, query=True) or list()
            meshes_by_shader[shader].extend(shaded)

    shader_by_id = {}
    for shader, shaded in meshes_by_shader.items():

        if shader not in shader_by_id:
            shader_by_id[shader] = list()

        for mesh in shaded:

            # Enable shader assignment to faces.
            name = mesh.split(".f[")[0]

            transform = name
            if cmds.objectType(transform) == "mesh":
                transform = cmds.listRelatives(name, parent=True)[0]

            try:
                id_ = cmds.getAttr(transform + "." + AVALON_ID_ATTR_SHORT)
                shader_by_id[shader].append(mesh.replace(name, id_))
            except KeyError:
                continue

        # Remove duplicates
        shader_by_id[shader] = list(set(shader_by_id[shader]))

    return shader_by_id


def apply_shaders(relationships, namespace=None):
    """Given a dictionary of `relationships`, apply shaders to meshes

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to meshes.

    """

    if namespace is not None:
        # Append namespace to shader group identifier.
        # E.g. `blinn1SG` -> `Bruce_:blinn1SG`
        relationships = {
            "%s:%s" % (namespace, shader): relationships[shader]
            for shader in relationships
        }

    for shader, ids in relationships.items():
        print("Looking for '%s'.." % shader)
        shader = next(iter(cmds.ls(shader)), None)
        assert shader, "Associated shader not part of asset, this is a bug"

        for id_ in ids:
            mesh, faces = (id_.rsplit(".", 1) + [""])[:2]

            # Find all meshes matching this particular ID
            # Convert IDs to mesh + id, e.g. "nameOfNode.f[1:100]"
            meshes = list(".".join([mesh, faces])
                          for mesh in lsattr(AVALON_ID_ATTR_SHORT, value=mesh))

            if not meshes:
                continue

            print("Assigning '%s' to '%s'" % (shader, ", ".join(meshes)))
            cmds.sets(meshes, forceElement=shader)


def lsattr(attr, value=None):
    """Return nodes matching `key` and `value`

    Arguments:
        attr (str): Name of Maya attribute
        value (object, optional): Value of attribute. If none
            is provided, return all nodes with this attribute.

    Example:
        >> lsattr("id", "myId")
        ["myNode"]
        >> lsattr("id")
        ["myNode", "myOtherNode"]

    """

    if value is None:
        return cmds.ls("*.%s" % attr)
    return lsattrs({attr: value})


def lsattrs(attrs):
    """Return nodes with the given attribute(s).

    Arguments:
        attrs (dict): Name and value pairs of expected matches

    Example:
        >> lsattr("age")  # Return nodes with attribute `age`
        >> lsattr({"age": 5})  # Return nodes with an `age` of 5
        >> # Return nodes with both `age` and `color` of 5 and blue
        >> lsattr({"age": 5, "color": "blue"})

    Returns a list.

    """

    dep_fn = om.MFnDependencyNode()
    dag_fn = om.MFnDagNode()
    selection_list = om.MSelectionList()

    first_attr = attrs.iterkeys().next()

    try:
        selection_list.add("*.{0}".format(first_attr),
                           searchChildNamespaces=True)
    except RuntimeError, e:
        if str(e).endswith("Object does not exist"):
            return []

    matches = set()
    for i in range(selection_list.length()):
        node = selection_list.getDependNode(i)
        if node.hasFn(om.MFn.kDagNode):
            fn_node = dag_fn.setObject(node)
            full_path_names = [path.fullPathName()
                               for path in fn_node.getAllPaths()]
        else:
            fn_node = dep_fn.setObject(node)
            full_path_names = [fn_node.name()]

        for attr in attrs:
            try:
                plug = fn_node.findPlug(attr, True)
                if plug.asString() != attrs[attr]:
                    break
            except RuntimeError:
                break
        else:
            matches.update(full_path_names)

    return list(matches)
