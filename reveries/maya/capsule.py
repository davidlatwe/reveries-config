import contextlib
from maya import cmds, mel
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
    smoothed = dict()
    try:
        smooth_mesh = cmds.ls("*.displaySmoothMesh", recursive=True)
        for attr in set(smooth_mesh):
            value = cmds.getAttr(attr)
            if value:
                smoothed[attr] = value
                cmds.setAttr(attr, 0)
        yield

    finally:
        for attr, value in smoothed.items():
            if cmds.objExists(attr):
                cmds.setAttr(attr, value)


@contextlib.contextmanager
def assign_shader(meshes, shadingEngine):
    """
    assign model to shading group
    """
    meshes_by_shader = dict()

    for mesh in cmds.ls(meshes, long=True, noIntermediate=True):
        for shader in cmds.listConnections(mesh,
                                           type="shadingEngine",
                                           source=False,
                                           destination=True) or list():
            if shader == shadingEngine:
                continue

            if shader not in meshes_by_shader:
                meshes_by_shader[shader] = set()

            shaded = set()
            for assigned in cmds.sets(shader, query=True) or []:
                # possible facets member
                node = cmds.ls(assigned, objectsOnly=True, long=True)
                if not node:
                    # Ensure the facets' node exists
                    continue

                if mesh == node[0]:
                    shaded.add(assigned)

            meshes_by_shader[shader].update(shaded)

    try:
        for shaded in meshes_by_shader.values():
            cmds.sets(list(shaded), edit=True, forceElement=shadingEngine)

        yield

    finally:
        for shader, shaded in meshes_by_shader.items():
            cmds.sets(list(shaded), forceElement=shader)


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


__no_undo_type = {"_": None}


@contextlib.contextmanager
def no_undo(flush=False):
    """Disable the undo queue during the context

    Arguments:
        flush (bool): When True the undo queue will be emptied when returning
            from the context losing all undo history. Defaults to False.

    """
    original = cmds.undoInfo(query=True, state=True)
    keyword = "state" if flush else "stateWithoutFlush"
    __no_undo_type["_"] = keyword

    try:
        cmds.undoInfo(**{keyword: False})
        yield
    finally:
        cmds.undoInfo(**{keyword: original})
        __no_undo_type["_"] = None


@contextlib.contextmanager
def undo_chunk(undo_on_exit=True):
    """Open undo chunk and undo when exit

    Use with caution !

    """
    try:
        cmds.undoInfo(ock=True)
        yield
    finally:
        cmds.undoInfo(cck=True)

        if undo_on_exit:
            try:  # Undo without RuntimeError: no command to undo
                cmds.undo()
            except RuntimeError as e:
                cmds.warning(str(e))


@contextlib.contextmanager
def undo_chunk_when_no_undo():
    """Open undo chunk and undo when exit back to context with no undo

    This should only be used under the `no_undo` context.

    Use with caution !!!

    Example:
    The scene will have a polyTorus and a cube but no sphere,
    and only the polyTorus' creation can be undone.

    >>> cmds.polyTorus()
    >>> with no_undo(flush=False):
    ...    cmds.polyCube()
    ...    with undo_chunk_when_no_undo():
    ...        print(cmds.polySphere())
    ...
    ['pSphere1', 'polySphere1']

    """
    keyword = __no_undo_type["_"]
    if keyword is None:
        raise RuntimeError("The keyword of undo state is `None`, "
                           "this is a bug.")

    original = cmds.undoInfo(query=True, state=True)
    cmds.undoInfo(**{keyword: True})

    try:
        cmds.undoInfo(ock=True)
        yield
    finally:
        cmds.undoInfo(cck=True)

        try:  # Undo without RuntimeError: no command to undo
            cmds.undo()
        except RuntimeError as e:
            cmds.warning(str(e))

        cmds.undoInfo(**{keyword: original})


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
        new (bool): Create namespace before entering the context

    Yields:
        str: The namespace that is used during the context

    """
    original = cmds.namespaceInfo(currentNamespace=True)
    if new:
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
def without_extension():
    """Use cmds.file with defaultExtensions=False"""
    previous_setting = cmds.file(defaultExtensions=True, query=True)
    try:
        cmds.file(defaultExtensions=False)
        yield
    finally:
        cmds.file(defaultExtensions=previous_setting)


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
            exists = cmds.ls(previous_selection)
            cmds.select(exists,
                        replace=True,
                        noExpand=True)
        else:
            cmds.select(clear=True)


@contextlib.contextmanager
def maintained_modification():
    """Maintain the modified state of the entire scene
    """
    modified = cmds.file(query=True, modified=True)
    try:
        yield
    finally:
        cmds.file(modified=modified)


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


@contextlib.contextmanager
def ref_edit_unlock():
    ref_lock = cmds.optionVar(query="refLockEditable")
    try:
        cmds.optionVar(intValue=("refLockEditable", 1))
        yield

    finally:
        cmds.optionVar(intValue=("refLockEditable", ref_lock))


class delete_after(object):
    """Context Manager that will delete collected nodes after exit.

    This allows to ensure the nodes added to the context are deleted
    afterwards. This is useful if you want to ensure nodes are deleted
    even if an error is raised.

    Examples:
        with delete_after() as delete_bin:
            cube = maya.cmds.polyCube()
            delete_bin.extend(cube)
            # cube exists
        # cube deleted

    """

    def __init__(self, nodes=None):

        self._nodes = list()

        if nodes:
            self.extend(nodes)

    def append(self, node):
        self._nodes.append(node)

    def extend(self, nodes):
        self._nodes.extend(nodes)

    def __iter__(self):
        return iter(self._nodes)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._nodes:
            cmds.delete(self._nodes)


@contextlib.contextmanager
def keytangent_default(in_tangent_type='auto',
                       out_tangent_type='auto'):
    """Set the default keyTangent for new keys during this context"""

    original_itt = cmds.keyTangent(query=True, g=True, itt=True)[0]
    original_ott = cmds.keyTangent(query=True, g=True, ott=True)[0]
    cmds.keyTangent(g=True, itt=in_tangent_type)
    cmds.keyTangent(g=True, ott=out_tangent_type)
    try:
        yield
    finally:
        cmds.keyTangent(g=True, itt=original_itt)
        cmds.keyTangent(g=True, ott=original_ott)


@contextlib.contextmanager
def reset_polySelectConstraint(reset=True):
    """Context during which the given polyConstraint settings are disabled.

    The original settings are restored after the context.

    """

    original = cmds.polySelectConstraint(query=True, stateString=True)

    try:
        if reset:
            # Ensure command is available in mel
            # This can happen when running standalone
            if not mel.eval("exists resetPolySelectConstraint"):
                mel.eval("source polygonConstraint")

            # Reset all parameters
            mel.eval("resetPolySelectConstraint;")
        cmds.polySelectConstraint(disable=True)
        yield
    finally:
        mel.eval(original)


@contextlib.contextmanager
def wait_cursor():
    """Provide a waiting cursor"""
    try:
        cmds.waitCursor(state=True)
        yield
    finally:
        cmds.waitCursor(state=False)


@contextlib.contextmanager
def attr_unkeyable(attr_list):
    """Set attribute not keyable during this context

    Args:
        attr_list (list): A list of `nodeName.attrName` strings

    """
    keyables = list()

    for attr in attr_list:
        if cmds.objExists(attr) and cmds.getAttr(attr, keyable=True):
            keyables.append(attr)

    try:
        for attr in keyables:
            cmds.setAttr(attr, keyable=False)
        yield
    finally:
        for attr in keyables:
            if cmds.objExists(attr):
                cmds.setAttr(attr, keyable=True)
