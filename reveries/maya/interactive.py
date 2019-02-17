
from maya import cmds

from avalon import api, io

from .vendor import capture
from . import lib, pipeline


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
