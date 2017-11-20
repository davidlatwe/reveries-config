import logging
import contextlib
import tempfile

from maya import cmds, mel

from avalon import maya


log = logging.getLogger(__name__)


def temp_dir():
    """Provide a temporary directory
    This temporary directory is generated through `tempfile.mkdtemp()`
    """
    return tempfile.mkdtemp()


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
            if override_enabled and override_visibility:
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


@contextlib.contextmanager
def no_undo(flush=False):
    """Disable the undo queue during the context

    Arguments:
        flush (bool): When True the undo queue will be emptied when returning
            from the context losing all undo history. Defaults to False.

    """
    original = cmds.undoInfo(query=True, state=True)
    keyword = 'state' if flush else 'stateWithoutFlush'

    try:
        cmds.undoInfo(**{keyword: False})
        yield
    finally:
        cmds.undoInfo(**{keyword: original})


def polyConstraint(components, *args, **kwargs):
    """Return the list of *components* with the constraints applied.

    A wrapper around Maya's `polySelectConstraint` to retrieve its results as
    a list without altering selections. For a list of possible constraints
    see `maya.cmds.polySelectConstraint` documentation.

    Arguments:
        components (list): List of components of polygon meshes

    Returns:
        list: The list of components filtered by the given constraints.

    """

    kwargs.pop('mode', None)

    with no_undo(flush=False):
        with maya.maintained_selection():
            # Apply constraint using mode=2 (current and next) so
            # it applies to the selection made before it; because just
            # a `maya.cmds.select()` call will not trigger the constraint.
            with reset_polySelectConstraint():
                cmds.select(components, r=1)
                cmds.polySelectConstraint(*args, mode=2, **kwargs)
                result = cmds.ls(selection=True)

    return result


@contextlib.contextmanager
def reset_polySelectConstraint(reset=True):
    """Context during which the given polyConstraint settings are disabled.

    The original settings are restored after the context.

    """

    original = cmds.polySelectConstraint(query=True, stateString=True)

    try:
        if reset:
            # Reset all parameters
            mel.eval("resetPolySelectConstraint;")
        cmds.polySelectConstraint(disable=True)
        yield
    finally:
        mel.eval(original)


def get_id(node):
    """
    Get the `rvID` attribute of the given node
    Args:
        node (str): the name of the node to retrieve the attribute from

    Returns:
        str

    """

    if node is None:
        return

    if not cmds.attributeQuery("rvID", node=node, exists=True):
        return

    return cmds.getAttr("{}.rvID".format(node))
