import contextlib
import maya.cmds as cmds
import avalon.maya
from . import lib


@contextlib.contextmanager
def no_display_layers(nodes):
    """
    remove DAG nodes connection with displayLayer
    """
    # remove `displayLayerManager` type node
    invalid = set(cmds.ls(nodes, type="displayLayerManager"))
    nodes = [x for x in nodes if x not in invalid]

    # get connections with `displayLayer` type node
    conn_pair = cmds.listConnections(
        nodes,
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
        for i in range(0, len(conn_pair), 2):
            cmds.connectAttr(conn_pair[i + 1], conn_pair[i])


@contextlib.contextmanager
def no_smooth_preview():
    """
    disable mesh smooth preview
    """
    smoothed = list()
    try:
        smooth_mesh = cmds.ls("*.displaySmoothMesh", recursive=True)
        for attr in set(smooth_mesh):
            if cmds.getAttr(attr):
                smoothed.append(attr)
                cmds.setAttr(attr, False)
        yield

    finally:
        for attr in smoothed:
            cmds.setAttr(attr, True)


@contextlib.contextmanager
def assign_shader(meshes, shadingEngine):
    """
    assign model to shading group
    """
    meshes_by_shader = dict()

    for mesh in meshes:
        for shader in cmds.listConnections(mesh,
                                           type="shadingEngine",
                                           source=False,
                                           destination=True) or list():
            if shader not in meshes_by_shader:
                meshes_by_shader[shader] = []

            shaded = cmds.sets(shader, query=True) or []
            meshes_by_shader[shader] += shaded

    try:
        cmds.sets(meshes, edit=True, forceElement=shadingEngine)

        yield

    finally:
        for shader, shaded in meshes_by_shader.items():
            cmds.sets(shaded, forceElement=shader)


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
def no_refresh():
    """Pause viewport
    """
    try:
        cmds.refresh(suspend=True)
        yield
    finally:
        cmds.refresh(suspend=False)


@contextlib.contextmanager
def no_undo(flush=False):
    """Disable the undo queue during the context

    Arguments:
        flush (bool): When True the undo queue will be emptied when returning
            from the context losing all undo history. Defaults to False.

    """
    original = cmds.undoInfo(query=True, state=True)
    keyword = "state" if flush else "stateWithoutFlush"

    try:
        cmds.undoInfo(**{keyword: False})
        yield
    finally:
        cmds.undoInfo(**{keyword: original})


@contextlib.contextmanager
def undo_chunk():
    """Open undo chunk and undo when exit

    Use with caution !

    """
    cmds.undoInfo(ock=True)
    try:
        yield
    finally:
        cmds.undoInfo(cck=True)

        try:  # Undo without RuntimeError: no command to undo
            cmds.undo()
        except RuntimeError as e:
            cmds.warning(str(e))


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
def namespaced(namespace, new=True):
    """Work inside namespace during context

    Args:
        new (bool): When enabled this will rename the namespace to a unique
            namespace if the input namespace already exists.

    Yields:
        str: The namespace that is used during the context

    """
    original = cmds.namespaceInfo(currentNamespace=True)
    if new:
        namespace = avalon.maya.lib.unique_namespace(namespace)
        cmds.namespace(add=namespace)

    try:
        cmds.namespace(set=namespace)
        yield namespace
    finally:
        cmds.namespace(set=original)


@contextlib.contextmanager
def root_namespaced():
    """Back to root namespace during context
    """
    original = cmds.namespaceInfo(currentNamespace=True)

    try:
        cmds.namespace(set=":")
        yield
    finally:
        cmds.namespace(set=original)


@contextlib.contextmanager
def relative_namespaced():
    """Entering relative namespace mode
    """
    relative = cmds.namespace(query=True, relativeNames=True)

    try:
        cmds.namespace(relativeNames=True)
        yield
    finally:
        cmds.namespace(relativeNames=relative)


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


@contextlib.contextmanager
def nodes_locker(nodes, lock=True, lockName=True, lockUnpublished=True):
    """Lock or unlock nodes and restore lock state on exit

    For node publishing, suggest using:
        - lock=False
        - lockName=True
        - lockUnpublished=True

    This will lock nodes' all attributes and names, but not locking nodes
    entirely, so still able to add custom attributes and nodes will remain
    deletable.

    """
    nodes = cmds.ls(nodes, objectsOnly=True, long=True)
    lock_state = lib.acquire_lock_state(nodes)

    try:
        lib.lock_nodes(nodes, lock, lockName, lockUnpublished)
        yield

    finally:
        # Restore lock states
        lib.restore_lock_state(lock_state)
