import contextlib
import maya.cmds as cmds


@contextlib.contextmanager
def no_display_layers(node_list):
    """
    remove DAG nodes connection with displayLayer
    """
    cmds.undoInfo(ock=True)

    # remove `displayLayerManager` type node
    invalid = set(cmds.ls(node_list, type="displayLayerManager"))
    node_list = [x for x in node_list if x not in invalid]
    # get connections with `displayLayer` type node
    conn_pair = cmds.listConnections(
        node_list,
        connections=True,
        plugs=True,
        type="displayLayer"
    ) or []

    try:
        # connection list *conn_pair* must be pairable
        # [source, destination, src, dst, ...]
        assert len(conn_pair) % 2 == 0
        # remove connection
        for i in range(0, len(conn_pair), 2):
            cmds.disconnectAttr(conn_pair[i + 1], conn_pair[i])
        yield
    except AssertionError:
        cmds.warning("This is a bug. The connection list is not pairable.")
    finally:
        cmds.undoInfo(cck=True)
        cmds.undo()


@contextlib.contextmanager
def no_smooth_preview():
    """
    disable mesh smooth preview
    """
    cmds.undoInfo(ock=True)

    try:
        smooth_mesh = cmds.ls("*.displaySmoothMesh", recursive=True)
        for attr in set(smooth_mesh):
            cmds.setAttr(attr, False)
        yield
    finally:
        cmds.undoInfo(cck=True)
        cmds.undo()


@contextlib.contextmanager
def assign_shader(node_list, shadingEngine):
    """
    assign model to shading group
    """
    cmds.undoInfo(ock=True)

    try:
        cmds.sets(node_list, edit=True, forceElement=shadingEngine)
        yield
    finally:
        cmds.undoInfo(cck=True)
        cmds.undo()


@contextlib.contextmanager
def renderlayer(layer):
    """
    Set the renderlayer during the context
    """

    original = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)

    try:
        cmds.editRenderLayerGlobals(currentRenderLayer=layer)
        yield
    finally:
        cmds.editRenderLayerGlobals(currentRenderLayer=original)
