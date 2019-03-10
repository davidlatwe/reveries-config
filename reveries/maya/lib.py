
import re
import logging

from maya import cmds, mel
from maya.api import OpenMaya as om

from .. import lib
from ..vendor.six import string_types
from .vendor import capture


log = logging.getLogger(__name__)


AVALON_ID_ATTR_LONG = "AvalonID"

TRANSFORM_ATTRS = [
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
]

CAMERA_SHAPE_KEYABLES = [
    "focalLength",
]


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


def query_by_renderlayer(node, attr, layer):
    """Query attribute without switching renderLayer when layer overridden

    (NOTE) The value that has been overridden may return in different type,
           e.g. `int` value may return as `long`.

           The `time` type of value will be multiplied with frame rate if it
           has layeroverride.

    Arguments:
        node (str): node name
        attr (str): node attribute name
        layer (str): renderLayer name

    """
    if cmds.mayaHasRenderSetup():
        return query_by_setuplayer(node, attr, layer)

    node_attr = node + "." + attr

    current = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
    if layer == current:
        return cmds.getAttr(node_attr, asString=True)

    val_type = cmds.getAttr(node_attr, type=True)
    is_time = False
    try:
        # For type correct, because bool value may return as float
        # from renderlayer.adjustments
        type_ = eval(val_type)
    except NameError:
        type_ = (lambda _: _)

        if val_type == "time":
            is_time = True

    def get_value(conn):
        return type_(cmds.getAttr(conn.rsplit(".", 1)[0] + ".value",
                                  asString=True))

    origin_value = None
    for conn in cmds.listConnections(node_attr, type="renderLayer",
                                     source=False, plugs=True) or []:
        if conn.startswith("defaultRenderLayer.adjustments"):
            # Origin value
            origin_value = get_value(conn)
            continue

        if not conn.startswith("%s.adjustments" % layer):
            continue
        # layer.adjustments[*].plug -> layer.adjustments[*].value
        if is_time:
            return get_value(conn) * mel.eval('currentTimeUnitToFPS()')
        return get_value(conn)

    if origin_value is not None:
        # Override in other layer
        if is_time:
            return origin_value * mel.eval('currentTimeUnitToFPS()')
        return origin_value

    # No override
    return cmds.getAttr(node_attr, asString=True)


def query_by_setuplayer(node, attr, layer):
    """Query attribute without switching renderSetupLayer when layer overridden

    Arguments:
        node (str): node long name
        attr (str): node attribute name
        layer (str): renderLayer name

    """
    node_attr = node + "." + attr
    current_layer = cmds.editRenderLayerGlobals(query=True,
                                                currentRenderLayer=True)
    if layer == current_layer:
        return cmds.getAttr(node_attr)

    enabled_overrides = cmds.ls(lsAttrs({"attribute": attr,
                                         "enabled": True}),
                                type="override")

    if enabled_overrides and layer == "defaultRenderLayer":
        applyer = cmds.listConnections(node_attr,
                                       type="applyOverride",
                                       skipConversionNodes=True)
        if applyer:
            # Get original
            return cmds.getAttr(applyer[0] + ".original")
        else:
            # No override
            return cmds.getAttr(node_attr)

    for override in enabled_overrides:
        setup_layers = cmds.ls(cmds.listHistory(override),
                               type="renderSetupLayer")
        overrided_layer = cmds.ls(cmds.listHistory(setup_layers),
                                  type="renderLayer")

        if not overrided_layer[0] == layer:
            continue

        collections = cmds.ls(cmds.listHistory(override), type="collection")
        collection = collections[0]

        if not cmds.getAttr(collection + ".enabled"):
            continue

        # Does this node selected by this collection ?
        # (NOTE) We can not relay on `cmds.editRenderLayerMembers` since
        #        the member list will not get updated if artist toggling
        #        the collection while the layer was not activated.
        #        Also, renderSettings node isn't a member of a layer.
        selector = cmds.listConnections(collection + ".selector")[0]
        pattern = cmds.getAttr(selector + ".pattern")
        selection = cmds.getAttr(selector + ".staticSelection")
        if (node in selection.split() or
                node in cmds.ls(re.split(";| ", pattern), long=True)):
            # Has override
            return cmds.getAttr(override + ".attrValue")

    else:
        # No override
        return cmds.getAttr(node_attr)


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

    Args:
        ndoe (str): Node name string
        displayLayer (bool): Check displayLayer, Default True
        intermediateObject (bool): Check 'intermediateObject', Default True
        parentHidden (bool): Check parent node, Default True
        visibility (bool): Check atttribute 'visibility', Default True

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


def lock_transform(node, additional=None):
    attr_to_lock = TRANSFORM_ATTRS + (additional or [])

    for attr in attr_to_lock:
        try:
            cmds.setAttr(node + "." + attr, lock=True)
        except RuntimeError as e:
            if not cmds.objectType(node) == "transform":
                raise TypeError("{} is not a transform node.".format(node))
            else:
                raise e


def shaders_by_meshes(meshes):
    """Return shadingEngine nodes from a list of mesh or facet
    """

    def ls_engine(mesh):
        return list(set(
            cmds.listConnections(mesh, type="shadingEngine") or []))

    assigned = list()

    if isinstance(meshes, string_types):
        meshes = [meshes]
    elif not isinstance(meshes, list):
        raise TypeError("`meshes` should be str or list.")

    mesh_faces = list()

    for mesh in meshes:
        if ".f[" not in mesh:
            assigned += ls_engine(cmds.ls(mesh, long=True, type="mesh"))
        else:
            mesh_faces.append(mesh)

    mesh_shpaes = list(set(cmds.ls(mesh_faces,
                                   objectsOnly=True,
                                   type="mesh",
                                   )))

    for engine in ls_engine(mesh_shpaes):
        for face in cmds.ls(mesh_faces, flatten=True):
            if cmds.sets(face, isMember=engine):
                assigned.append(engine)

    return list(set(assigned))


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
        objectsOnly=True,
        type="transform"
    )

    surfaces_by_id = {}
    for transform in valid_nodes:
        shapes = cmds.listRelatives(transform,
                                    shapes=True,
                                    fullPath=True,
                                    type="surfaceShape") or list()
        shapes = cmds.ls(shapes, noIntermediate=True)

        try:
            surface = shapes[0]
        except IndexError:
            continue

        try:
            id_ = cmds.getAttr(transform + "." + AVALON_ID_ATTR_LONG)
        except ValueError:
            continue
        else:
            if id_ not in surfaces_by_id:
                surfaces_by_id[id_] = list()

            surfaces_by_id[id_].append(surface)

    surfaces_by_shader = {}
    for id_, surfaces in surfaces_by_id.items():

        for shader in cmds.listConnections(surfaces,
                                           type="shadingEngine",
                                           source=False,
                                           destination=True) or list():

            # Objects in this group are those that haven't got
            # any shaders. These are expected to be managed
            # elsewhere, such as by the default model loader.
            if shader == "initialShadingGroup":
                continue

            if shader not in surfaces_by_shader:
                surfaces_by_shader[shader] = list()

            shaded = cmds.ls(cmds.sets(shader, query=True), long=True)
            surfaces_by_shader[shader].extend(shaded)

    shader_by_id = {}
    for shader, shaded in surfaces_by_shader.items():

        for surface in shaded:

            # Enable shader assignment to mesh faces.
            name = surface.split(".f[")[0]

            transform = name
            if cmds.objectType(transform, isAType="surfaceShape"):
                transform = cmds.listRelatives(name,
                                               parent=True,
                                               fullPath=True)[0]

            if transform not in valid_nodes:
                # Ignore nodes which were not in the query list
                continue

            try:
                id_ = cmds.getAttr(transform + "." + AVALON_ID_ATTR_LONG)
            except ValueError:
                continue
            else:
                if shader not in shader_by_id:
                    shader_by_id[shader] = list()

                shader_by_id[shader].append(surface.replace(name, id_))

        # Remove duplicates
        shader_by_id[shader] = list(set(shader_by_id[shader]))

    return shader_by_id


def apply_shaders(relationships, namespace=None, target_namespaces=None):
    """Given a dictionary of `relationships`, apply shaders to surfaces

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to surfaces.
        namespace (str, optional): namespace that need to apply to shaders
        target_namespaces (list, optional): model namespaces

    """

    if namespace is not None:
        # Append namespace to shader group identifier.
        # E.g. `blinn1SG` -> `Bruce_:blinn1SG`
        relationships = {
            "%s:%s" % (namespace, shader): relationships[shader]
            for shader in relationships
        }

    target_namespaces = target_namespaces or [None]

    for shader_, ids in relationships.items():
        print("Looking for '%s'.." % shader_)
        shader = next(iter(cmds.ls(shader_)), None)
        if shader is None:
            log.warning("{!r} Not found. Skipping..".format(shader_))
            log.warning("Associated shader not part of asset, this is a bug.")
            continue

        for id_ in ids:
            surface, faces = (id_.rsplit(".", 1) + [""])[:2]

            for target_namespace in target_namespaces:
                # Find all surfaces matching this particular ID
                # Convert IDs to surface + id, e.g. "nameOfNode.f[1:100]"
                surfaces = list(".".join([m, faces])
                                for m in lsAttr(AVALON_ID_ATTR_LONG,
                                                value=surface,
                                                namespace=target_namespace))

                if not surfaces:
                    continue

                print("Assigning '%s' to '%s'" % (shader, ", ".join(surfaces)))
                cmds.sets(surfaces, forceElement=shader)


def apply_crease_edges(relationships, namespace=None, target_namespaces=None):
    """Given a dictionary of `relationships`, apply crease value to edges

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to surface edges.
        namespace (str, optional): namespace that need to apply to creaseSet
        target_namespaces (list, optional): model namespaces

    Returns:
        list: A list of created or used crease sets

    """
    namespace = namespace or ""
    crease_sets = list()

    for level, members in relationships.items():
        level = float(level)

        node = lsAttr("creaseLevel", level, namespace=namespace)
        if not node:
            crease_name = namespace + ":creaseSet1"
            crease_set = cmds.createNode("creaseSet", name=crease_name)
            cmds.setAttr(crease_set + ".creaseLevel", level)
        else:
            crease_set = node[0]

        crease_sets.append(crease_set)

        for member in members:
            id, edge_ids = member.split(".")

            for target_namespace in target_namespaces:
                # Find all surfaces matching this particular ID
                # Convert IDs to surface + id, e.g. "nameOfNode.f[1:100]"
                edges = list(".".join([m, edge_ids])
                             for m in lsAttr(AVALON_ID_ATTR_LONG,
                                             value=id,
                                             namespace=target_namespace))
                if not edges:
                    continue

                print("Applying '%s' to '%s'" % (crease_set, ", ".join(edges)))
                cmds.sets(edges, forceElement=crease_set)

    return crease_sets


def list_all_parents(nodes):
    """List all parents of dag nodes

    Args:
        nodes (list or str): A list of node or one node name

    Returns:
        (list): A list of all parent nodes

    """
    parents = cmds.listRelatives(nodes, parent=True, fullPath=True) or []
    if parents:
        parents += list_all_parents(parents)
    return list(set(parents))


def hasAttr(node, attr):
    """Convenience function for determining if an object has an attribute

    This function is simply using `cmds.objExists`, it's about 4 times faster
    then `cmds.attributeQuery(attr, node=node, exists=True)`, and about 9 times
    faster then pymel's `PyNode(node).hasAttr(attr)`.

    Arguments:
        node (str): Name of Maya node
        attr (str): Name of Maya attribute

    Example:
        >> hasAttr("pCube1", "translateX")
        True

    """
    return cmds.objExists(node + "." + attr)


def lsAttr(attr, value=None, namespace=None):
    """Return nodes matching `key` and `value`

    Arguments:
        attr (str): Name of Maya attribute
        value (object, optional): Value of attribute. If none
            is provided, return all nodes with this attribute.
        namespace (str): Search under this namespace, default all.

    Example:
        >> lsAttr("id", "myId")
        ["myNode"]
        >> lsAttr("id")
        ["myNode", "myOtherNode"]

    """
    namespace = namespace or ""

    if value is None:
        return cmds.ls("{0}*.{1}".format(namespace, attr),
                       long=True,
                       recursive=True)
    return lsAttrs({attr: value}, namespace=namespace)


def _mplug_type_map(value):
    _map = {
        float: "asDouble",
        int: "asInt",
        bool: "asBool",
    }
    try:
        return _map[type(value)]
    except KeyError:
        if isinstance(value, string_types):
            return "asString"
        return None


def lsAttrs(attrs, namespace=None):
    """Return nodes with the given attribute(s).

    Arguments:
        attrs (dict): Name and value pairs of expected matches

    Example:
        >> lsAttrs({"age": 5})  # Return nodes with an `age` of 5
        >> # Return nodes with both `age` and `color` of 5 and blue
        >> lsAttrs({"age": 5, "color": "blue"})

    Returns a list.

    Raise `TypeError` if value type not supported.
    Currently supported value types are:
        * `float`
        * `int`
        * `bool`
        * `str`

    If the attribute is connected with a source node, the value
    will be compared with the source node name.

    """
    namespace = namespace or ""

    # Type check
    for attr, value in attrs.items():
        if _mplug_type_map(value) is None:
            raise TypeError("Unsupported value type {0!r} on attribute {1!r}"
                            "".format(type(value), attr))

    dep_fn = om.MFnDependencyNode()
    dag_fn = om.MFnDagNode()
    selection_list = om.MSelectionList()

    first_attr = attrs.iterkeys().next()

    try:
        selection_list.add("{0}*.{1}".format(namespace, first_attr),
                           searchChildNamespaces=True)
    except RuntimeError as e:
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

        for attr, value in attrs.items():
            try:
                plug = fn_node.findPlug(attr, True)
                if plug.isDestination:
                    # The plug is being connected, retrive source node name
                    source_plug = plug.connectedTo(True, False)[0]
                    source_node = source_plug.name().split(".")[0]
                    if source_node != value:
                        break
                else:
                    value_getter = getattr(plug, _mplug_type_map(value))
                    if value_getter() != value:
                        break
            except RuntimeError:
                break
        else:
            matches.update(full_path_names)

    return list(matches)


def ls_duplicated_name(nodes, rename=False):
    """Genreate a node name duplication report dict

    Arguments:
        nodes (list): A list of DAG nodes.
        rename (bool, optional): Auto rename duplicated node if set to `True`,
            and if set to `True`, will not return the report.

    This will list out every node which share the same base name and thire
    full DAG path, for example:

    >> cmds.polyCube(n="Box")
    >> cmds.group(n="BigBox_A")
    >> cmds.polyCube(n="Box")
    >> cmds.group(n="BigBox_B")
    >> cmds.polyCube(n="Box")
    >> ls_duplicated_name(["Box"])
    # Result: {u'Box': [u'|Box', u'|BigBox_B|Box', u'|BigBox_A|Box']} #

    If `rename` is on, it will auto append a digit suffix to the base name.

    """

    result = dict()

    for node in cmds.ls(nodes, long=True):
        full_name = node
        base_name = full_name.rsplit("|")[-1]

        if base_name not in result:
            result[base_name] = list()

        result[base_name].append(full_name)

    # Remove those not duplicated
    for base_name in list(result.keys()):
        if len(result[base_name]) == 1:
            del result[base_name]

    if not rename:
        return result

    # Auto rename with digit suffix
    for base_name, nodes in result.items():
        for i, full_name in enumerate(nodes):
            cmds.rename(full_name, base_name + "_" + str(i))


def filter_mesh_parenting(transforms):
    """Filter out mesh parenting nodes from list

    Arguments:
        transforms (list): A list of transforms nodes.

    This will return a list that mesh parenting nodes are removed, possible
    use case is to clean up the selection before Alembic export to avoid
    mesh parenting error.

    Example:

    >> cmds.polyCube(n="A")
    >> cmds.polyCube(n="B")
    >> cmds.polyCube(n="C")
    >> cmds.parent("C", "B")
    >> cmds.parent("B", "A")
    >> cmds.group("A", name="ROOT", world=True)
    >> cmds.select("ROOT", hierarchy=True)
    >> filter_mesh_parenting(cmds.ls(sl=True))
    # Result: [u'|ROOT', u'|ROOT|A'] #

    """

    # Phase 1
    cleaned_1 = list()
    blacksheep = list()

    for node in cmds.ls(transforms, long=True, type="transform"):
        if node in blacksheep:
            continue

        children = cmds.listRelatives(node,
                                      children=True,
                                      fullPath=True)

        sub_transforms = cmds.ls(children, long=True, type="transform")

        if cmds.ls(children, type="mesh") and sub_transforms:
            blacksheep += sub_transforms

        cleaned_1 += cmds.ls(node, long=True)

    # Phase 2
    cleaned_2 = list()

    for node in cleaned_1:
        if any(node.startswith(_) for _ in blacksheep):
            continue

        cleaned_2.append(node)

    return cleaned_2


def get_highest_in_hierarchy(nodes):
    """Return highest nodes in the hierarchy that are in the `nodes` list.

    The "highest in hierarchy" are the nodes closest to world: top-most level.

    Args:
        nodes (list): The nodes in which find the highest in hierarchies.

    Returns:
        list: The highest nodes from the input nodes.

    """

    # Ensure we use long names
    nodes = cmds.ls(nodes, long=True)
    lookup = set(nodes)

    highest = []
    for node in nodes:
        # If no parents are within the nodes input list
        # then this is a highest node
        if not any(n in lookup for n in lib.iter_uri(node, "|")):
            highest.append(node)

    return highest


def parse_active_camera():
    """Parse the active camera

    Raises
        RuntimeError: When no active modelPanel an error is raised.

    Returns:
        str: Name of camera

    """
    panel = capture.parse_active_panel()
    camera = cmds.modelPanel(panel, query=True, camera=True)

    return camera


def connect_message(source, target, attrname, lock=True):
    """Connect nodes with message channel

    This will build a convenience custom connection between two nodes:

        source.message -> target.attrname

    Pop warning if source or target node does not exists.

    Args:
        source (str): Message output node
        target (str): Message input node
        attrname (str): Name of input attribute of target node
        lock (bool, optional): Lock attribute if set to True (default True)

    """
    if not cmds.objExists(source):
        cmds.warning("Source node {!r} not exists.".format(source))
        return
    if not cmds.objExists(target):
        cmds.warning("Target node {!r} not exists.".format(target))
        return

    cmds.addAttr(target, longName=attrname, attributeType="message")

    target_attr = target + "." + attrname
    cmds.connectAttr(source + ".message", target_attr)
    cmds.setAttr(target_attr, lock=lock)


def to_namespace(node, namespace):
    """Return node name as if it's inside the namespace.

    Args:
        node (str): Node name
        namespace (str): Namespace

    Returns:
        str: The node in the namespace.

    """
    namespace_prefix = "|{}:".format(namespace)
    node = namespace_prefix.join(node.split("|"))
    return node


def ls_startup_cameras():
    cameras = [cam for cam in cmds.ls(cameras=True, long=True)
               if cmds.camera(cam, query=True, startupCamera=True)]
    cameras += cmds.listRelatives(cameras, parent=True, fullPath=True)

    return cameras


def ls_renderable_cameras(layer=None):
    layer = layer or cmds.editRenderLayerGlobals(query=True,
                                                 currentRenderLayer=True)
    return [
        cam for cam in cmds.ls(type="camera", long=True)
        if query_by_renderlayer(cam, "renderable", layer)
    ]


def acquire_lock_state(nodes):
    nodes = cmds.ls(nodes, objectsOnly=True, long=True)
    is_lock = cmds.lockNode(nodes, query=True, lock=True)
    is_lockName = cmds.lockNode(nodes, query=True, lockName=True)
    is_lockUnpub = cmds.lockNode(nodes, query=True, lockUnpublished=True)

    return {
        "uuids": cmds.ls(nodes, uuid=True),
        "isLock": is_lock,
        "isLockName": is_lockName,
        "isLockUnpublished": is_lockUnpub
    }


def lock_nodes(nodes, lock=True, lockName=True, lockUnpublished=True):
    # (NOTE) `lockNode` command flags:
    #    lock: If flag not supplied, default `True`
    #    lockName: If flag not supplied, default `False`
    #    lockUnpublished: No default, change nothing if not supplied
    #    ignoreComponents: If components presence in the input list,
    #                      will raise RuntimeError and nothing will
    #                      be locked. But if this flag supplied, it
    #                      will silently ignore components.
    cmds.lockNode(nodes,
                  lock=lock,
                  lockName=lockName,
                  lockUnpublished=lockUnpublished,
                  ignoreComponents=True)


def restore_lock_state(lock_state):
    for _ in range(len(lock_state["uuids"])):
        uuid = lock_state["uuids"].pop(0)
        node = cmds.ls(uuid)
        if not node:
            continue

        cmds.lockNode(node,
                      lock=lock_state["isLock"].pop(0),
                      lockName=lock_state["isLockName"].pop(0),
                      lockUnpublished=lock_state["isLockUnpublished"].pop(0),
                      ignoreComponents=True)


def reference_node_by_namespace(namespace):
    """Find reference node by a given namespace

    Args:
        namespace (str): Absolute namespace

    Return:
        (str or None): Reference node name or None if not found

    """
    return next((ref for ref in cmds.ls(type="reference")
                 if cmds.referenceQuery(ref, namespace=True) == namespace),
                None)


def get_ns(node):
    """Get Absolute namespace from node name string

    Args:
        node (str): Node name

    Returns:
        str: Absolute namespace

    """
    parts = node.rsplit("|", 1)[-1].rsplit(":", 1)
    return (":" + parts[0]) if len(parts) > 1 else ":"


def pick_cacheable(nodes):
    """Filter out cacheable (deformable) nodes

    Args:
        nodes (list): A list of node names

    Returns:
        list: A list of cacheable node names

    """
    nodes = cmds.listRelatives(nodes, allDescendents=True, fullPath=True) or []
    shapes = cmds.ls(nodes,
                     type="deformableShape",
                     noIntermediate=True,
                     long=True)
    cacheables = set()
    for node in shapes:
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        transforms = cmds.ls(parent, long=True)
        cacheables.update(transforms)

    return list(cacheables)
