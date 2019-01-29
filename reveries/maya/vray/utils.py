
from maya import cmds
from .. import lib


def create_vray_settings():

    # Try register vray
    try:
        cmds.renderer("vray")
    except RuntimeError:
        print("Vray already Registered")

    # Collect all vray-Attributes
    globalsTabLabels = cmds.renderer("vray", query=True, globalsTabLabels=True)
    globalsTabCreateProcNames = cmds.renderer("vray",
                                              query=True,
                                              globalsTabCreateProcNames=True)
    globalsTabUpdateProcNames = cmds.renderer("vray",
                                              query=True,
                                              globalsTabUpdateProcNames=True)
    # Construct Vray-Renderer
    for tab_id in range(len(globalsTabLabels)):
        cmds.renderer("vray",
                      edit=True,
                      addGlobalsTab=[
                          str(globalsTabLabels[tab_id]),
                          str(globalsTabCreateProcNames[tab_id]),
                          str(globalsTabUpdateProcNames[tab_id]),
                      ])
    # Create DAG for VRAYSETTINGS
    cmds.shadingNode("VRaySettingsNode", asUtility=True, name="vraySettings")


def get_vray_output_image_format():
    is_multichannel_exr = None

    if cmds.optionMenuGrp("vrayImageFormatMenu", query=True, exists=True):
        ext = cmds.optionMenuGrp("vrayImageFormatMenu",
                                 query=True,
                                 value=True)
    else:
        ext = cmds.getAttr("vraySettings.imageFormatStr")
        if ext == "":
            # For some reason this happens if you have not
            # changed the format
            ext = "png"

    if ext.startswith("exr"):
        multichannel = " (multichannel)"
        if ext.endswith(multichannel):
            ext = ext[:-len(multichannel)]
            is_multichannel_exr = True
        else:
            is_multichannel_exr = False

    return ext, is_multichannel_exr


def get_vray_element_nodes(layer=None):
    element_nodes = []

    ext, is_multichannel_exr = get_vray_output_image_format()
    enable_all = cmds.getAttr("vraySettings.relements_enableall")
    use_referenced = cmds.getAttr("vraySettings.relements_usereferenced")
    layer = layer or cmds.editRenderLayerGlobals(query=True,
                                                 currentRenderLayer=True)

    if not is_multichannel_exr and enable_all:
        for element in cmds.ls(type=("VRayRenderElement",
                                     "VRayRenderElementSet")):
            enabled = lib.query_by_renderlayer(element, "enabled", layer)
            if not enabled:
                continue

            is_referenced = cmds.referenceQuery(element, isNodeReferenced=True)
            if is_referenced and not use_referenced:
                continue

            element_nodes.append(element)

    return element_nodes


def get_vray_element_names(layer=None):
    element_names = []

    for element in get_vray_element_nodes(layer):

        elem_type = cmds.getAttr(element + ".vrayClassType")
        elem_name = ""

        if elem_type in ("ExtraTexElement", "MaterialSelectElement"):
            attrs = cmds.listAttr(element, string="vray_explicit_name_*")
            elem_name = cmds.getAttr(element + "." + attrs[0])

            if elem_name == "":
                attrs = cmds.listAttr(element, string="vray_name_*")
                elem_name = cmds.getAttr(element + "." + attrs[0])

                if elem_type == "ExtraTexElement":
                    attr = "vray_texture_extratex"
                elif elem_type == "MaterialSelectElement":
                    attr = "vray_mtl_mtlselect"

                addition = cmds.listConnections(element + "." + attr)
                if addition:
                    elem_name += "_" if elem_name else ""
                    elem_name += addition[0]

        else:
            attrs = (cmds.listAttr(element, string="vray_name_*") or
                     cmds.listAttr(element, string="vray_filename_*"))
            elem_name = cmds.getAttr(element + "." + attrs[0])

        elem_name = elem_name.replace(" ", "_")
        element_names.insert(0, elem_name)

    separate_alpha = cmds.getAttr("vraySettings.separateAlpha")
    if separate_alpha:
        element_names.insert(0, "Alpha")

    return element_names


def vrmeshes_by_transforms(transforms):
    """Return VRayMesh nodes from input transform nodes

    Arguments:
        transforms (list): A list of transforms nodes.

    """

    vrmeshes = list()

    for node in cmds.ls(transforms, long=True, type="transform"):
        preview = cmds.listRelatives(node,
                                     shapes=True,
                                     fullPath=True,
                                     type="VRayMeshPreview")

        if not preview:
            continue

        vrmesh = list(set(cmds.listConnections(preview,
                                               source=True,
                                               destination=False,
                                               plugs=False,
                                               connections=False,
                                               type="VRayMesh")))

        vrmeshes += vrmesh

    return vrmeshes
