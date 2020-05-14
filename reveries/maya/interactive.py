
import os
import json
import logging
from maya import cmds, mel

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
    nodes = (set(cmds.ls(type="geometryShape", long=True)) -
             set(cmds.ls(readOnly=True, long=True)) -
             set(cmds.ls(lockedNodes=True, long=True)))

    transforms = cmds.listRelatives(list(nodes),
                                    allParents=True,  # include instances
                                    fullPath=True) or []

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

    (Deprecated)

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

    (Deprecated)

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
            xgen.legacy.bake_description(palette, description)


def bake_all_xgen_legacy_modifiers(*args):
    for palette in xgen.legacy.list_palettes():
        for description in xgen.legacy.list_descriptions(palette):
            xgen.legacy.bake_modules(palette, description)


def copy_mesh_to_world(*args):
    for node in cmds.ls(sl=True, long=True):
        new_node = cmds.duplicate(node, inputConnections=True)[0]
        cmds.parent(new_node, world=True)


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


def update_uv(*args):
    """Update Rig deformed geo's UV"""
    def get_meshes(node):
        return cmds.listRelatives(node, shapes=True, path=True, type="mesh")

    def get_target_mesh(meshes):
        """Locate original mesh shape to transfer UV to"""
        return next(m for m in meshes
                    if cmds.getAttr(m + ".intermediateObject")
                    and not cmds.referenceQuery(m, isNodeReferenced=True))

    selection = cmds.ls(sl=True)

    if len(selection) == 2:
        # Update UV from another model
        source, target = selection
        meshes = get_meshes(target)
        target = get_target_mesh(meshes)

    elif len(selection) == 1:
        # Update UV from referenced intermediate shape node
        transform = selection[0]
        meshes = get_meshes(transform)
        target = get_target_mesh(meshes)
        source = meshes[0]

        if target == source:
            raise Exception("Source and target is the same.")
    else:
        raise Exception("No object to update.")

    cmds.setAttr(target + ".intermediateObject", False)

    cmds.transferAttributes(source,
                            target,
                            transferPositions=0,
                            transferNormals=0,
                            transferUVs=2,
                            transferColors=0,
                            sampleSpace=1,
                            searchMethod=3,
                            flipUVs=0)

    cmds.delete(target, constructionHistory=True)

    cmds.setAttr(target + ".intermediateObject", True)


def fix_renderGlobalsEncoding_not_found(*args):
    """Fix renderGlobalsEncoding not found error while switching renderlayers

    For unknown reason, sometimes (rare) switching renderlayer or renderer when
    using Arnold in Maya 2018 may raise "renderGlobalsEncoding not found" error
    and causing render settings GUI not able to show the image format properly.

    The simplest way to reproduce this bug, is to `source` the mel script
    `createMayaSoftwareCommonGlobalsTab.mel` again, then switching renderers.

    Might be something to do with defaultRenderGlobals' "Custom Image Format",
    or scriptJob that related to it. Not sure.

    I remember we had the same issue when using VRay a while back, but can't
    remember whether we were using Maya 2018 or 2016, but based on the script
    of proc `updateMayaSoftwareImageFormatControl` in Maya 2018, VRay has been
    take cared so I think it was Maya 2016.

    """
    if cmds.about(version=True) != "2018":
        cmds.warning("This fix is only for Maya 2018.")
        return

    def parse_proc(path, name, new_name=None):
        proc = []
        with open(path, "r") as script:
            for line in script.readlines():
                if "proc %s(" % name in line:
                    if new_name:
                        line = line.replace(name, new_name)
                    proc.append(line)
                    continue
                if proc:
                    proc.append(line)
                    if line.startswith("}"):
                        break
        return "".join(proc)

    mel.eval("source createMayaSoftwareCommonGlobalsTab.mel;")
    result = mel.eval("whatIs createMayaSoftwareCommonGlobalsTab;")
    path = result[len("Mel procedure found in: "):]

    proc_name = "updateMayaSoftwareImageFormatControl"
    new_proc_name = "_the_buggy_one"

    new_proc = parse_proc(path, proc_name, new_proc_name)
    sub = parse_proc(path, "enableCompressorbutton")

    # Re-define procs
    mel.eval("""
    {{
        {sub}

        {bug}
    }}
    """.format(sub=sub, bug=new_proc))

    # Wrap fix
    mel.eval("""
    global proc {fix}()
    {{
        if (`currentRenderer` == "arnold")
            return;

        {bug}();
    }}
    """.format(fix=proc_name, bug=new_proc_name))


def separate_with_id(*args):
    """Separate meshes with AvalonID preserved"""
    selection = cmds.ls(sl=True, objectsOnly=True)
    assert len(selection) == 1, "Select one object or faces in one object."
    node = selection[0]
    type = cmds.nodeType(node)

    if type == "transform":
        child = cmds.listRelatives(node,
                                   shapes=True,
                                   noIntermediate=True,
                                   path=True)
        if not child:
            raise Exception("Please select mesh type object, this is a group.")
        parent = node

    elif type == "mesh":
        parent = cmds.listRelatives(node, parent=True, path=True)[0]

    else:
        raise Exception("Please select mesh type object.")

    id = utils.get_id(parent)
    asset_id = utils.get_id_namespace(parent)

    mel.eval("performPolyShellSeparate")
    new_nodes = cmds.ls(sl=True, type="transform")
    cmds.delete(new_nodes, constructionHistory=True)

    with utils.id_namespace(asset_id):
        for sep in new_nodes:
            utils.upsert_id(sep, id=id)

    cmds.rename(parent, parent + "_sep")


def combine_with_id(*args):
    """Combine meshes with AvalonID preserved"""
    selection = cmds.ls(sl=True, objectsOnly=True, type="transform")
    assert len(selection) > 1, "Select at least two objects to combine."

    anchor = selection[-1]
    parent = cmds.listRelatives(anchor, parent=True, path=True)[0]
    id = utils.get_id(anchor)
    asset_id = utils.get_id_namespace(anchor)

    cmds.polyUnite(constructionHistory=False, centerPivot=True)
    new_node = cmds.ls(sl=True, type="transform")[0]

    with utils.id_namespace(asset_id):
        utils.upsert_id(new_node, id=id)

    cmds.parent(new_node, parent)
