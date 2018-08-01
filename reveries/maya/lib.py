
import logging
import uuid

from maya import cmds

from .. import pipeline


log = logging.getLogger(__name__)


AVALON_ID_ATTR_LONG = "AvalonID"
AVALON_ID_ATTR_SHORT = "avid"

DEFAULT_MATRIX = [1.0, 0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 0.0, 0.0, 1.0]


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


def set_avalon_uuid(node, renew=False):
    """Add or renew avID ( Avalon ID ) to `node`
    """
    write = False
    attr = "{0}.{1}".format(node, AVALON_ID_ATTR_SHORT)

    if not cmds.objExists(attr):
        write = True
        cmds.addAttr(node, shortName=AVALON_ID_ATTR_SHORT,
                     longName=AVALON_ID_ATTR_LONG, dataType="string")
        _, uid = str(uuid.uuid4()).rsplit("-", 1)

    if write or renew:
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

    start_frame, end_frame, fps = pipeline.compose_timeline_data()
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


TRANSFORM_ATTRS = [
    ".translateX", ".translateY", ".translateZ",
    ".rotateX", ".rotateY", ".rotateZ",
    ".scaleX", ".scaleY", ".scaleZ",
]


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
    shape_keyables = [
        ".focalLength",
    ]
    cmds.setAttr(transform + ".visibility", keyable=True, lock=False)
    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(transform + attr, keyable=True, lock=False)
    for attr in shape_keyables:
        cmds.setAttr(shape + attr, keyable=True, lock=False)

    bake_to_worldspace(transform, startFrame, endFrame)


def lock_transform(node):
    if not cmds.objectType(node) == "transform":
        raise TypeError("{} is not a transform node.".format(node))

    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(node + attr, lock=True)


def bake_hierarchy_visibility():
    pass
