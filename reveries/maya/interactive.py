
import os
import json
import logging
from maya import cmds

from avalon import api, io

from .vendor import capture
from . import lib, pipeline, xgen, utils
from .io import bind_xgen_LGC_description
from ..utils import get_representation_path_


log = logging.getLogger(__name__)


def active_view_snapshot(*args):
    capture.snap(
        clipboard=True,
        display_options={
            "displayGradient": cmds.displayPref(
                query=True, displayGradient=True),
            "background": cmds.displayRGBColor(
                "background", query=True),
            "backgroundTop": cmds.displayRGBColor(
                "backgroundTop", query=True),
            "backgroundBottom": cmds.displayRGBColor(
                "backgroundBottom", query=True),
        }
    )


def wipe_all_namespaces():
    all_NS = cmds.namespaceInfo(":",
                                listOnlyNamespaces=True,
                                recurse=True,
                                absoluteName=True)
    for NS in reversed(all_NS):
        if NS in (":UI", ":shared"):
            continue

        try:
            cmds.namespace(removeNamespace=NS,
                           force=True,
                           mergeNamespaceWithRoot=True)
        except RuntimeError:
            pass


def apply_avalon_uuid(*args):
    # (TODO): Implement GUI
    nodes = (set(cmds.ls(type="surfaceShape", long=True)) -
             set(cmds.ls(long=True, readOnly=True)) -
             set(cmds.ls(long=True, lockedNodes=True)))

    transforms = cmds.listRelatives(list(nodes), parent=True) or list()

    # Add unique identifiers
    for node in transforms:
        if utils.get_id(node) is None:
            utils.upsert_id(node)


def swap_to_published_model(*args):
    """Hide the working model and load the published version of it

    This is for the case that artist was working on model and lookDev all
    together, while publishing turntable require the model to be published
    version.

    Using this tool could load the latest version via the instance that was
    used to publish this model.

    """
    MSG = "Please select '|ROOT' node, and '|ROOT' node only."

    selection = cmds.ls(selection=True, long=True, type="transform")
    assert len(selection) == 1, MSG

    root = selection[0]
    assert root.endswith("|ROOT"), MSG

    instances = lib.lsAttrs({"id": "pyblish.avalon.instance",
                             "family": "reveries.model"})

    project = api.Session.get("AVALON_PROJECT")
    asset = None
    subset = None
    for set_ in cmds.listSets(object=root) or []:
        if set_ in instances:
            asset = cmds.getAttr(set_ + ".asset")
            subset = cmds.getAttr(set_ + ".subset")
            break

    assert project is not None, "Project undefined, this is not right."
    assert asset and subset, "Model instance not found."
    assert len(instances) == 1, "Too many model instances in scene."

    representation = io.locate([project, asset, subset, -1, "mayaBinary"])

    Loaders = api.discover(api.Loader)
    Loader = next((loader for loader in Loaders
                   if loader.__name__ == "ModelLoader"), None)

    assert Loader is not None, "ModelLoader not found, this is a bug."
    assert representation is not None, "Representation not found."

    container = api.load(Loader, representation)

    group = pipeline.get_group_from_container(container["objectName"])

    parent = cmds.listRelatives(root, parent=True)
    if parent:
        cmds.parent(group, parent)

    # Re-assign shaders
    nodes = cmds.listRelatives(root, allDescendents=True, fullPath=True)
    shader_by_id = lib.serialise_shaders(nodes)
    lib.apply_shaders(shader_by_id)

    # Hide unpublished model
    cmds.setAttr(root + ".visibility", False)


def __ensure_nodes_in_same_namespace(nodes, err_msg):
    namespaces = set()
    for node in nodes:
        namespaces.add(lib.get_ns(node))

    if not len(namespaces) == 1:
        raise Exception(err_msg)

    return namespaces.pop()


def __get_representation(namespace):
    container_node = pipeline.get_container_from_namespace(namespace)
    _id = io.ObjectId(cmds.getAttr(container_node + ".representation"))
    return io.find_one({"_id": _id})


def __get_package_path(representation):
    parents = io.parenthood(representation)
    return get_representation_path_(representation, parents)


def __load_bounding_data(representation, package_path):
    file_path = os.path.join(package_path, representation["data"]["linkFname"])
    # Load map
    bound_map = None
    try:
        with open(file_path) as f:
            bound_map = json.load(f)
    except IOError:
        log.warning("Asset has no bounding data.\n"
                    "{!r} not found".format(file_path))

    return bound_map


def bind_xgen_interactive_by_selection(*args):
    """Bind XGen interactive groom via selecting XGen and Model subset

    Select loaded XGen IGS subset group and bound mesh subset group

    """
    selection = cmds.ls(sl=True)
    selection += cmds.listRelatives(selection, allDescendents=True) or []

    descriptions = xgen.interactive.list_lead_descriptions(selection)
    meshes = cmds.ls(selection, long=True, type="mesh")

    # Get descriptions' container by namespace
    err_msg = ("Can only process on one set of XGen Descriptions.")
    desc_namespace = __ensure_nodes_in_same_namespace(descriptions, err_msg)

    # Ensure selected meshes are under same namespace
    err_msg = ("Can only process on one set of XGen Bound Mesh.")
    mesh_namespace = __ensure_nodes_in_same_namespace(meshes, err_msg)

    # Get representation from database and retrive link map
    representation = __get_representation(desc_namespace)
    if representation is None:
        return

    package_path = __get_package_path(representation)
    bound_map = __load_bounding_data(representation, package_path)
    if bound_map is None:
        return

    # Collect and check
    _bound = dict()
    for desc in descriptions:
        desc_id = utils.get_id(desc)

        if desc_id is None:
            raise Exception("Description {!r} has no ID, this is a bug."
                            "".format(desc))

        bound_meshes = []
        ids = bound_map[desc_id]
        nodes = lib.ls_nodes_by_id(ids, mesh_namespace + ":")
        for id in ids:
            models = list(nodes[id])
            _meshes = cmds.listRelatives(models,
                                         shapes=True,
                                         noIntermediate=True,
                                         fullPath=True) or []
            if not _meshes:
                raise Exception("Bound mesh {!r} has no ID.".format(desc))

            # Only bound to selected model
            bound_meshes += [m for m in _meshes if m in meshes]

        _bound[desc] = bound_meshes

    # Bind !
    cmds.evalDeferred("from reveries.maya.io import attach_xgen_IGS_preset")
    for d, bm in _bound.items():
        cmds.evalDeferred("attach_xgen_IGS_preset({0!r}, {1})".format(d, bm))


def __duplicate_mesh_to_xgen_subset(bound_mesh, from_namespace, to_namespace):
    new_name = to_namespace + ":" + bound_mesh.rsplit(":", 1)[-1]
    new_mesh = cmds.duplicate(bound_mesh,
                              name=new_name,
                              inputConnections=True)[0]
    new_nodes = cmds.listRelatives(new_mesh, shapes=True)
    new_nodes.append(new_mesh)

    from_container = pipeline.get_container_from_namespace(from_namespace)
    to_container = pipeline.get_container_from_namespace(to_namespace)

    cmds.sets(new_nodes, forceElement=to_container)
    cmds.sets(new_nodes, remove=from_container)

    cmds.parent(new_mesh, world=True)

    return new_mesh


def bind_xgen_legacy_by_selection(*args):
    """Bind XGen legacy via selecting XGen and Model subset

    Select loaded XGen Legacy palette nodes and bound mesh subset group

    (NOTE) This will duplicate bound meshes into XGen subset's namespace
           and parent to world. Because XGen Legacy require them exists
           under same namespace.

    """
    selection = cmds.ls(sl=True)
    selection += cmds.listRelatives(selection, allDescendents=True) or []

    palettes = cmds.ls(selection, type="xgmPalette")
    meshes = cmds.ls(selection, long=True, type="mesh")

    # Get palettes' container by namespace
    err_msg = ("Can only process on one set of XGen Palettes.")
    pal_namespace = __ensure_nodes_in_same_namespace(palettes, err_msg)

    # Ensure selected meshes are under same namespace
    err_msg = ("Can only process on one set of XGen Bound Mesh.")
    mesh_namespace = __ensure_nodes_in_same_namespace(meshes, err_msg)

    # Get representation from database and retrive link map
    representation = __get_representation(pal_namespace)
    if representation is None:
        return

    package_path = __get_package_path(representation)
    bound_map = __load_bounding_data(representation, package_path)
    if bound_map is None:
        return

    # Collect and check
    _bound = dict()
    for palette in palettes:
        descriptions = xgen.legacy.list_descriptions(palette)
        for desc in descriptions:
            desc_id = utils.get_id(desc)

            if desc_id is None:
                raise Exception("Description {!r} has no ID, this is a bug."
                                "".format(desc))

            bound_meshes = []
            ids = bound_map[desc_id]
            nodes = lib.ls_nodes_by_id(ids, mesh_namespace + ":")
            for id in ids:
                models = list(nodes[id])
                _meshes = cmds.listRelatives(models,
                                             shapes=True,
                                             noIntermediate=True,
                                             fullPath=True) or []
                if not _meshes:
                    raise Exception("Bound mesh {!r} has no ID.".format(desc))

                # Only bound to selected model
                bound_meshes += [cmds.listRelatives(m, parent=True)[0]
                                 for m in _meshes if m in meshes]

            # Get guides
            guide_path = None
            if xgen.legacy.description_ctrl_method(desc) == "Guides":
                guide_path = os.path.join(package_path,
                                          "guides",
                                          palette.rsplit(":", 1)[-1],
                                          desc.rsplit(":", 1)[-1] + ".abc")

                if not os.path.isfile(guide_path):
                    raise Exception("Guides alembic file not exists, "
                                    "this is a bug. {}".format(guide_path))

            _bound[desc] = (bound_meshes, guide_path)

    # Bind !
    duplicated = dict()
    for d, (bm, guide) in _bound.items():
        _bm = []
        for mesh in bm:
            try:
                _mesh = duplicated[mesh]
            except KeyError:
                _mesh = __duplicate_mesh_to_xgen_subset(mesh,
                                                        mesh_namespace,
                                                        pal_namespace)
                duplicated[mesh] = _mesh

            _bm.append(_mesh)

        before_nodes = set(cmds.ls(long=True))
        bind_xgen_LGC_description(d, _bm, guide)
        after_nodes = set(cmds.ls(long=True))
        # Push new nodes into container
        container = pipeline.get_container_from_namespace(pal_namespace)
        cmds.sets(list(after_nodes - before_nodes), forceElement=container)

    # Apply deltas
    for palette in palettes:
        deltas = os.path.join(package_path,
                              "deltas",
                              palette.rsplit(":", 1)[-1])

        if not os.path.isdir(deltas):
            continue

        xgen.legacy.apply_deltas(palette,
                                 [os.path.join(deltas, f).replace("\\", "/")
                                  for f in os.listdir(deltas)])

    # Disable tubeshade and inCamOnly
    for palette in palettes:
        xgen.legacy.disable_tube_shade(palette)
        xgen.legacy.disable_in_camera_only(palette)


def bake_all_xgen_legacy_descriptions(*args):
    for palette in xgen.legacy.list_palettes():
        for description in xgen.legacy.list_descriptions(palette):
            xgen.legacy.bake_description(palette, description, rebake=True)


def bake_all_xgen_legacy_modifiers(*args):
    for palette in xgen.legacy.list_palettes():
        for description in xgen.legacy.list_descriptions(palette):
            xgen.legacy.bake_modules(palette, description)


def link_palettes_to_hair_system(*args):
    selection = cmds.ls(sl=True)
    selection += cmds.listRelatives(selection, allDescendents=True) or []
    palettes = cmds.ls(selection, type="xgmPalette")

    assert palettes, "No XGen palette node selected."

    for palette in cmds.ls(selection, type="xgmPalette"):
        xgen.legacy.build_hair_system(palette)


def set_refwires_frame_by_nucleus(*args):
    selection = cmds.ls(sl=True)
    selection += cmds.listRelatives(selection, allDescendents=True) or []

    palettes = cmds.ls(selection, type="xgmPalette")
    nucleus = cmds.ls(selection, type="nucleus")

    assert len(nucleus) == 1, "Select at least one and only nucleus node."

    assert palettes, "Select at least one XGen palette."

    start_frame = cmds.getAttr(nucleus[0] + ".startFrame")

    for pal in palettes:
        xgen.legacy.set_refWires_frame(start_frame, pal)
