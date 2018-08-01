import contextlib
import maya.cmds as cmds


def _safe_undo():
    """Undo without RuntimeError: no command to undo
    """
    try:
        cmds.undo()
    except RuntimeError as e:
        cmds.warning(str(e))


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
        _safe_undo()


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
        _safe_undo()


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
        _safe_undo()


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


@contextlib.contextmanager
def evaluation(mode="off"):
    """Set the evaluation manager during context.

    Arguments:
        mode (str): The mode to apply during context.
            "off": The standard DG evaluation (stable)
            "serial": A serial DG evaluation
            "parallel": The Maya 2016+ parallel evaluation

    """

    original = cmds.evaluationManager(query=True, mode=1)[0]
    try:
        cmds.evaluationManager(mode=mode)
        yield
    finally:
        cmds.evaluationManager(mode=original)


@contextlib.contextmanager
def no_refresh(with_undo=False):
    """Pause viewport
    """
    if with_undo:
        cmds.undoInfo(ock=True)

    try:
        cmds.refresh(suspend=True)
        yield
    finally:
        if with_undo:
            cmds.undoInfo(cck=True)
            _safe_undo()
        cmds.refresh(suspend=False)


@contextlib.contextmanager
def undo():
    """Pause viewport
    """
    cmds.undoInfo(ock=True)
    try:
        yield
    finally:
        cmds.undoInfo(cck=True)
        _safe_undo()


@contextlib.contextmanager
def solo_renderable(solo_cam):
    """
    Disable all cameras as renderable and store the original states
    """
    cams = cmds.ls(type="camera")
    states = {}
    for cam in cams:
        states[cam] = cmds.getAttr(cam + ".rnd")
        cmds.setAttr(cam + ".rnd", 0)

    # Change the solo cam to renderable
    cmds.setAttr(solo_cam + ".rnd", 1)

    try:
        yield
    finally:
        # Revert to original state
        for cam, state in states.items():
            cmds.setAttr(cam + ".rnd", state)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> scene = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="Test")
        >>> cmds.select("persp")
        >>> with maintained_selection():
        ...     cmds.select("Test", replace=True)
        >>> "Test" in cmds.ls(selection=True)
        False

    """

    previous_selection = cmds.ls(selection=True)
    try:
        yield
    finally:
        if previous_selection:
            cmds.select(previous_selection,
                        replace=True,
                        noExpand=True)
        else:
            cmds.select(clear=True)
