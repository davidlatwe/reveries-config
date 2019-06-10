
import re
import logging
from collections import defaultdict
from maya import cmds, mel
from maya.api import OpenMaya as om

from .. import lib
from ..vendor.six import string_types
from .vendor import capture


log = logging.getLogger(__name__)


AVALON_ID_ATTR_LONG = lib.AVALON_ID

AVALON_NAMESPACE_WRAPPER_ID = "000000000000000000000000"

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


def is_using_renderSetup():
    """Is Maya currently using renderSetup system ?"""
    try:
        return cmds.mayaHasRenderSetup()
    except AttributeError:
        return False


def pretty_layer_name(layer):
    """Get GUI renderlayer name

    If using renderSetup, the return node name is renderSetupLayer name.

    Args:
        layer (str): Legacy renderlayer name

    Returns:
        str: GUI renderlayer name

    """
    if layer.endswith("defaultRenderLayer"):
        return "masterLayer"
    else:
        layername = cmds.ls(cmds.listHistory(layer, future=True),
                            type="renderSetupLayer")
        if layername:
            # has renderSetup
            return layername[0]
        else:
            return layer


def ls_renderable_layers():
    """List out renderable renderlayers

    This will ignore referenced renderlayer, and if using renderSetup,
    the returned node name is legacy renderlayer node name, not renderSetup
    nodes.

    Returns:
        list: A list of renderable renderlayer node names

    """
    return [i for i in cmds.ls(type="renderLayer") if
            cmds.getAttr("{}.renderable".format(i)) and not
            cmds.referenceQuery(i, isNodeReferenced=True)]


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
    if is_using_renderSetup():
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
    """Query attribute without switching renderSetupLayer

    Arguments:
        node (str): node long name
        attr (str): node attribute name
        layer (str): renderLayer name (NOT renderSetupLayer)

    """
    node_attr = node + "." + attr

    def original_value(attr_=None):
        attr_ = attr_ or attr
        node_attr_ = node + "." + attr_
        appliers = cmds.ls(cmds.listHistory(node_attr_, pruneDagObjects=True),
                           type="applyOverride")
        if appliers:
            return cmds.getAttr(appliers[-1] + ".original", asString=True)
        else:
            return cmds.getAttr(node + "." + attr_, asString=True)

    current_layer = cmds.editRenderLayerGlobals(query=True,
                                                currentRenderLayer=True)
    if layer == current_layer:
        # At current layer, simple get
        return cmds.getAttr(node_attr, asString=True)

    if layer == "defaultRenderLayer":
        # Querying masterLayer, get original value
        return original_value()

    # Handling compound attribute
    parent_attr = cmds.attributeQuery(attr, node=node, listParent=True) or []
    child_attrs = cmds.attributeQuery(attr, node=node, listChildren=True) or []

    attrs = set([attr])
    attrs.update(parent_attr + child_attrs)

    enabled_overrides = set()

    for at in attrs:
        enabled = [n for n in cmds.ls(type="override") if
                   cmds.getAttr(n + ".attribute") == at and
                   cmds.getAttr(n + ".enabled")]
        enabled_overrides.update(enabled)

    if not enabled_overrides:
        # No Override enabled in every layer
        return cmds.getAttr(node_attr, asString=True)

    setup_layer = cmds.listConnections(layer + ".message",
                                       type="renderSetupLayer")[0]
    # (NOTE) We starting from the highest collection because if the node
    #        being collected in multiple collections, only the overrides
    #        in higher collection has effect.
    #
    highest_col = cmds.listConnections(setup_layer + ".collectionHighest")
    if highest_col is None:
        # Empty layer, get original value
        return original_value()

    # The hunt begins...

    def is_selected_by(selector):
        """Did the collection selector select this node ?"""
        pattern = cmds.getAttr(selector + ".pattern")
        selection = cmds.getAttr(selector + ".staticSelection")
        if (node in selection.split() or
                node in cmds.ls(re.split(";| ", pattern), long=True)):
            return True
        return False

    def walk_siblings(item):
        """Walk renderSetup nodes from highest(bottom) to lowest(top)"""
        yield item
        previous = cmds.listConnections(item + ".previous")
        if previous is not None:
            for sibling in walk_siblings(previous[0]):
                yield sibling

    def walk_hierarchy(item):
        """Walk renderSetup nodes with depth prior"""
        for sibling in walk_siblings(item):
            yield sibling
            try:
                children = cmds.listConnections(sibling + ".listItems")
                overrides = set(cmds.ls(children, type="override"))
                no_others = len(children) == len(overrides)
                if no_others and not enabled_overrides.intersection(overrides):
                    continue
                highest = cmds.listConnections(sibling + ".childHighest")[0]
            except (ValueError, TypeError):
                continue
            else:
                for child in walk_hierarchy(highest):
                    yield child

    # compound value filter
    if parent_attr:
        index = cmds.attributeQuery(parent_attr[0],
                                    node=node,
                                    listChildren=True).index(attr)
        filter = (lambda compound, _: compound[0][index])

    elif child_attrs:
        default = cmds.attributeQuery(attr, node=node, listDefault=True)
        filter = (lambda val, ind: [val if i == ind else v
                                    for i, v in enumerate(default)])
    else:
        filter = None

    def value_filter(value, attr_):
        if attr_ in parent_attr:
            return filter(value, None)
        elif attr_ in child_attrs:
            return filter(value, child_attrs.index(attr_))
        else:
            return value

    # Locate leaf collection and get overrides from there

    overrides = []

    for item in walk_hierarchy(highest_col[0]):
        try:
            selector = cmds.listConnections(item + ".selector")[0]
        except ValueError:
            # Is an override
            if item in enabled_overrides:
                overrides.append(item)

        else:
            # Is a collection
            if is_selected_by(selector):
                if not cmds.getAttr(item + ".selfEnabled"):
                    # Collection not enabled, not a member
                    return original_value()

                overrides = []

    if not overrides:
        return original_value()

    # Collect values from overrides

    root = None
    relatives = []

    for override in overrides:
        attr_ = cmds.getAttr(override + ".attribute")

        try:
            # Absolute override
            root = cmds.getAttr(override + ".attrValue", asString=True)
            root = value_filter(root, attr_)
            if attr_ in child_attrs:
                for i, ca in enumerate(child_attrs):
                    if not ca == attr_:
                        root[i] = original_value(ca)

            if not len(relatives):
                return root
            else:
                break

        except ValueError:
            # Relative override
            multiply = cmds.getAttr(override + ".multiply")
            multiply = value_filter(multiply, attr_)
            offset = cmds.getAttr(override + ".offset")
            offset = value_filter(offset, attr_)
            relatives.insert(0, (multiply, offset))

    else:
        root = original_value()

    # Compute value

    if child_attrs:
        # compound value
        for m, o in relatives:
            for r_arr, m_arr, o_arr in zip(root, m, o):
                new = list()
                for R, M, O in zip(r_arr, m_arr, o_arr):
                    new.append(R * M + O)
                root = new
        return root

    for m, o in relatives:
        root = root * m + o
    return root


def is_visible(node,
               displayLayer=True,
               intermediateObject=True,
               parentHidden=True,
               visibility=True,
               time=None):
    """Is `node` visible?

    Returns whether a node is hidden by one of the following methods:
    - The node exists (always checked)
    - The node must be a dagNode (always checked)
    - The node's visibility is off.
    - The node is set as intermediate Object.
    - The node is in a disabled displayLayer.
    - Whether any of its parent nodes is hidden.
    - Whether it's visible at the given time.

    Roughly based on: http://ewertb.soundlinker.com/mel/mel.098.php

    Args:
        ndoe (str): Node name string
        displayLayer (bool): Check displayLayer, Default True
        intermediateObject (bool): Check 'intermediateObject', Default True
        parentHidden (bool): Check parent node, Default True
        visibility (bool): Check atttribute 'visibility', Default True
        time (int or float, optional): Evaluate the visible state at the given
            time instead of the current time. Default current time.

    Returns:
        bool: Whether the node is visible in the scene

    """
    time = cmds.currentTime(query=True) if time is None else time
    kwargs = dict()
    if cmds.listConnections('{0}.visibility'.format(node),
                            source=True,
                            destination=False,
                            connections=False):
        # `time` flag may return incorrect value sometimes if the attribute
        # did not have any input connections. Reason unknow.
        kwargs = {"time": time}

    # Only existing objects can be visible
    if not cmds.objExists(node):
        return False

    # Only dagNodes can be visible
    if not cmds.objectType(node, isAType='dagNode'):
        return False

    if visibility:
        if not cmds.getAttr('{0}.visibility'.format(node), **kwargs):
            return False

    if intermediateObject and cmds.objectType(node, isAType='shape'):
        if cmds.getAttr('{0}.intermediateObject'.format(node), **kwargs):
            return False

    if displayLayer:
        # Display layers set overrideEnabled and overrideVisibility on members
        if cmds.attributeQuery('overrideEnabled', node=node, exists=True):
            override_enabled = cmds.getAttr('{}.overrideEnabled'.format(node),
                                            **kwargs)
            override_visibility = cmds.getAttr(
                '{}.overrideVisibility'.format(node), **kwargs)
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
                              visibility=visibility,
                              **kwargs):
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


def bake(nodes,
         frame_range=None,
         step=1.0,
         simulation=True,
         preserve_outside_keys=False,
         disable_implicit_control=True,
         shape=True):
    """Bake the given nodes over the time range.

    This will bake all attributes of the node, including custom attributes.

    Args:
        nodes (list): Names of transform nodes, eg. camera, light.
        frame_range (list): frame range with start and end frame.
            or if None then takes timeSliderRange
        simulation (bool): Whether to perform a full simulation of the
            attributes over time.
        preserve_outside_keys (bool): Keep keys that are outside of the baked
            range.
        disable_implicit_control (bool): When True will disable any
            constraints to the object.
        shape (bool): When True also bake attributes on the children shapes.
        step (float): The step size to sample by.

    Returns:
        None

    """
    from .capsule import keytangent_default  # Avoid circular import

    # Parse inputs
    if not nodes:
        return

    assert isinstance(nodes, (list, tuple)), "Nodes must be a list or tuple"

    # If frame range is None fall back to time slider playback time range
    if frame_range is None:
        frame_range = [cmds.playbackOptions(query=True, minTime=True),
                       cmds.playbackOptions(query=True, maxTime=True)]

    # If frame range is single frame bake one frame more,
    # otherwise maya.cmds.bakeResults gets confused
    if frame_range[1] == frame_range[0]:
        frame_range[1] += 1

    # Bake it
    with keytangent_default(in_tangent_type='auto',
                            out_tangent_type='auto'):
        cmds.bakeResults(nodes,
                         simulation=simulation,
                         preserveOutsideKeys=preserve_outside_keys,
                         disableImplicitControl=disable_implicit_control,
                         shape=shape,
                         sampleBy=step,
                         time=(frame_range[0], frame_range[1]))


def bake_to_world_space(nodes,
                        frame_range=None,
                        simulation=True,
                        preserve_outside_keys=False,
                        disable_implicit_control=True,
                        shape=True,
                        step=1.0):
    """Bake the nodes to world space transformation (incl. other attributes)

    Bakes the transforms to world space (while maintaining all its animated
    attributes and settings) by duplicating the node. Then parents it to world
    and constrains to the original.

    Other attributes are also baked by connecting all attributes directly.
    Baking is then done using Maya's bakeResults command.

    See `bake` for the argument documentation.

    Returns:
         list: The newly created and baked node names.

    """
    from .capsule import delete_after  # Avoid circular import

    def _get_attrs(node):
        """Workaround for buggy shape attribute listing with listAttr"""
        attrs = cmds.listAttr(node,
                              write=True,
                              scalar=True,
                              settable=True,
                              connectable=True,
                              keyable=True,
                              shortNames=True) or []
        valid_attrs = []
        for attr in attrs:
            node_attr = '{0}.{1}'.format(node, attr)

            # Sometimes Maya returns 'non-existent' attributes for shapes
            # so we filter those out
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue

            # We only need those that have a connection, just to be safe
            # that it's actually keyable/connectable anyway.
            if cmds.connectionInfo(node_attr,
                                   isDestination=True):
                valid_attrs.append(attr)

        return valid_attrs

    transform_attrs = set(["t", "r", "s",
                           "tx", "ty", "tz",
                           "rx", "ry", "rz",
                           "sx", "sy", "sz"])

    world_space_nodes = []
    with delete_after() as delete_bin:

        # Create the duplicate nodes that are in world-space connected to
        # the originals
        for node in nodes:

            # Duplicate the node
            short_name = node.rsplit("|", 1)[-1]
            new_name = "{0}_baked".format(short_name)
            new_node = cmds.duplicate(node,
                                      name=new_name,
                                      renameChildren=True)[0]

            # Connect all attributes on the node except for transform
            # attributes
            attrs = _get_attrs(node)
            attrs = set(attrs) - transform_attrs if attrs else []

            for attr in attrs:
                orig_node_attr = '{0}.{1}'.format(node, attr)
                new_node_attr = '{0}.{1}'.format(new_node, attr)

                # unlock to avoid connection errors
                cmds.setAttr(new_node_attr, lock=False)

                cmds.connectAttr(orig_node_attr,
                                 new_node_attr,
                                 force=True)

            # If shapes are also baked then connect those keyable attributes
            if shape:
                children_shapes = cmds.listRelatives(new_node,
                                                     children=True,
                                                     fullPath=True,
                                                     shapes=True)
                if children_shapes:
                    orig_children_shapes = cmds.listRelatives(node,
                                                              children=True,
                                                              fullPath=True,
                                                              shapes=True)
                    for orig_shape, new_shape in zip(orig_children_shapes,
                                                     children_shapes):
                        attrs = _get_attrs(orig_shape)
                        for attr in attrs:
                            orig_node_attr = '{0}.{1}'.format(orig_shape, attr)
                            new_node_attr = '{0}.{1}'.format(new_shape, attr)

                            # unlock to avoid connection errors
                            cmds.setAttr(new_node_attr, lock=False)

                            cmds.connectAttr(orig_node_attr,
                                             new_node_attr,
                                             force=True)

            # Parent to world
            if cmds.listRelatives(new_node, parent=True):
                new_node = cmds.parent(new_node, world=True)[0]

            # Unlock transform attributes so constraint can be created
            for attr in transform_attrs:
                cmds.setAttr('{0}.{1}'.format(new_node, attr), lock=False)

            # Constraints
            delete_bin.extend(cmds.parentConstraint(node, new_node, mo=False))
            delete_bin.extend(cmds.scaleConstraint(node, new_node, mo=False))

            world_space_nodes.append(new_node)

        bake(world_space_nodes,
             frame_range=frame_range,
             step=step,
             simulation=simulation,
             preserve_outside_keys=preserve_outside_keys,
             disable_implicit_control=disable_implicit_control,
             shape=shape)

    return world_space_nodes


def bake_camera(camera, startFrame, endFrame, step=1.0):
    """Bake camera to worldspace

    Returns:
        str: A newly baked camera

    """
    shape = None
    if cmds.objectType(camera) == "transform":
        transform = camera
        shape = (cmds.listRelatives(camera, shapes=True, fullPath=True) or
                 [None])[0]
    elif cmds.objectType(camera) == "camera":
        transform = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
        shape = camera

    if shape is None:
        raise TypeError("{} is not a camera.".format(camera))

    # make sure attrs all keyable
    cmds.setAttr(transform + ".visibility", keyable=True, lock=False)
    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(transform + "." + attr, keyable=True, lock=False)
    for attr in CAMERA_SHAPE_KEYABLES:
        cmds.setAttr(shape + "." + attr, keyable=True, lock=False)

    return bake_to_world_space([transform],
                               (startFrame, endFrame),
                               step=step)[0]


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
    from . import utils  # Avoid circular import

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

        id_ = utils.get_id(transform)

        if id_ is None:
            continue

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

            id_ = utils.get_id(transform)

            if id_ is None:
                continue

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
        # Add namespace to shader group identifier.
        # E.g. `blinn1SG` -> `Bruce_:blinn1SG`
        relationships = {
            "%s:%s" % (namespace, shader): relationships[shader]
            for shader in relationships
        }

    target_namespaces = target_namespaces or [None]

    for shader_, ids in relationships.items():

        shader = next(iter(cmds.ls(shader_)), None)
        if shader is None:
            log.warning("{!r} Not found. Skipping..".format(shader_))
            log.warning("Associated shader not part of asset, this is a bug.")
            continue

        face_map = defaultdict(set)
        for id_ in ids:
            id, face = (id_.rsplit(".", 1) + [""])[:2]
            face_map[id].add(face)

        surface_cache = defaultdict(set)
        for target_namespace in target_namespaces:
            _map = ls_nodes_by_id(set(face_map.keys()), target_namespace)
            for id, nodes in _map.items():
                surface_cache[id].update(nodes)

        surfaces = []
        for id, faces in face_map.items():
            # Find all surfaces matching this particular ID
            # Convert IDs to surface + faceid, e.g. "nameOfNode.f[1:100]"
            surfaces += list(".".join([n, face])
                             for n in surface_cache[id]
                             for face in faces)

        if not surfaces:
            continue

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
    target_namespaces = target_namespaces or [None]
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

        edge_map = defaultdict(set)
        for member in members:
            id, edge_id = member.split(".")
            edge_map[id].add(edge_id)

        surface_cache = defaultdict(set)
        for target_namespace in target_namespaces:
            _map = ls_nodes_by_id(set(edge_map.keys()), target_namespace)
            for id, nodes in _map.items():
                surface_cache[id].update(nodes)

        edges = []
        for id, edge_ids in edge_map.items():
            # Find all surfaces matching this particular ID
            # Convert IDs to surface + edgeid, e.g. "nameOfNode.e[1:100]"
            edges += list(".".join([n, edge])
                          for n in surface_cache[id]
                          for edge in edge_ids)

        if not edges:
            continue

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

    (NOTE): This method will return True when you are querying against to a
            transform node but the attribute is in it's shape node.

    Arguments:
        node (str): Name of Maya node
        attr (str): Name of Maya attribute

    Example:
        >> hasAttr("pCube1", "translateX")
        True

    """
    return cmds.objExists(node + "." + attr)


def hasAttrExact(node, attr):
    """Convenience function for determining if a node has the attribute

    This function is using `cmds.attributeQuery`, it's a bit slower but able
    to differ the arrtibute is in transform node or it's shape node.

    Arguments:
        node (str): Name of Maya node
        attr (str): Name of Maya attribute

    Example:
        >> hasAttrExact("pCube1", "translateX")
        True

    """
    return cmds.attributeQuery(attr, node=node, exists=True)


def ls_nodes_by_id(ids, namespace=None):
    """Return nodes by matching Avalon UUID

    This function is faster then using `lsAttrs({"AvalonID": id})` because
    it does not return nodes with long name, and matching a list of ids in
    one `ls`.

    Args:
        ids (list or set): A list of ids
        namespace (str, optional): Search under this namespace, default all.

    Returns:
        defaultdict(set): {id(str): nodes(set)}

    """
    from . import utils  # Avoid circular import

    def is_namespace_wrapper(id, node):
        return (id == AVALON_NAMESPACE_WRAPPER_ID and
                cmds.nodeType(node) == "objectSet")

    namespace = namespace or ""
    nodes = cmds.ls("{0}*.{1}".format(namespace, AVALON_ID_ATTR_LONG),
                    long=False,
                    objectsOnly=True,
                    recursive=True)

    id_map = defaultdict(set)
    for node in nodes:
        id = utils.get_id(node)

        if id is None:
            continue

        if id in ids:
            id_map[id].add(node)

        elif is_namespace_wrapper(id, node):
            for member in cmds.sets(node, query=True, nodesOnly=True) or []:
                id = utils.get_id(member)
                if id is not None and id in ids:
                    id_map[id].add(member)

    return id_map


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
    """List out renderable camera in layer

    Args:
        layer (str, optional): renderLayer name, default current layer

    Returns:
        list: A list of cameraShape name

    """
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
        list: A list of cacheable transfrom node names

    """
    nodes += cmds.listRelatives(nodes,
                                allDescendents=True,
                                fullPath=True) or []
    shapes = set(cmds.ls(nodes,
                         type="deformableShape",
                         noIntermediate=True,
                         long=True))
    cacheables = set()
    for node in shapes:
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        transforms = cmds.ls(parent, long=True)
        cacheables.update(transforms)

    return list(cacheables)


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
    from .capsule import (  # Avoid circular import
        no_undo,
        maintained_selection,
        reset_polySelectConstraint,
    )

    kwargs.pop("mode", None)

    with no_undo(flush=False):
        with maintained_selection():
            # Apply constraint using mode=2 (current and next) so
            # it applies to the selection made before it; because just
            # a `maya.cmds.select()` call will not trigger the constraint.
            with reset_polySelectConstraint():
                cmds.select(components, r=1, noExpand=True)
                cmds.polySelectConstraint(*args, mode=2, **kwargs)
                result = cmds.ls(selection=True)
                cmds.select(clear=True)

    return result


def get_reference_node(nodes):
    """Get exact reference nodes from nodes

    Collect the references without .placeHolderList[] attributes as
    unique entries (objects only) and skipping the sharedReferenceNode
    and _UNKNOWN_REF_NODE_.

    Args:
        nodes (list): list of node names

    Returns:
        set: A set of reference node names.

    """
    references = set()

    for ref in cmds.ls(nodes, exactType="reference", objectsOnly=True):

        # Ignore any `:sharedReferenceNode`
        if ref.rsplit(":", 1)[-1].startswith("sharedReferenceNode"):
            continue

        # Ignore _UNKNOWN_REF_NODE_ (PLN-160)
        if ref.rsplit(":", 1)[-1].startswith("_UNKNOWN_REF_NODE_"):
            continue

        references.add(ref)

    return references


def get_highest_reference_node(references):
    """Get highest reference node (least parents)

    Args:
        references (list): A list of reference nodes.

    Returns:
        str: A reference node that has least parents.

    """
    highest = min(references,
                  key=lambda x: len(get_reference_node_parents(x)))
    return highest


def get_reference_node_parents(reference):
    """Return all parent reference nodes of reference node

    Args:
        reference (str): reference node.

    Returns:
        list: The upstream parent reference nodes.

    """
    parent = cmds.referenceQuery(reference,
                                 referenceNode=True,
                                 parent=True)
    parents = []
    while parent:
        parents.append(parent)
        parent = cmds.referenceQuery(parent,
                                     referenceNode=True,
                                     parent=True)
    return parents
