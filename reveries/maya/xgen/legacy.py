
import contextlib
import maya.cmds as cmds
import xgenm as xg
import xgenm.xgGlobal as xgg

from xgenm.ui.widgets.xgExpressionUI import ExpressionUI
from avalon.vendor.Qt import QtCore


def list_palettes():
    """Return all palettes in scene"""
    return list(xg.palettes())


def get_palette_by_description(description):
    """Get the palette for the given description

    To do this, the list of descriptions for each palette is searched,
    which assumes that all of the descriptions are uniquely named.

    Args:
        description (str): XGen Legacy description name

    Return:
        (str): Name of palette

    """
    return xg.palette(str(description))


def list_descriptions(palette=""):
    """Return all descriptions of the palette or in scene

    Get a list of descriptions for the given palette; or, if no palette name
    is given, return all descriptions in the scene.

    Args:
        palette (str, optional): XGen Legacy palette name

    Return:
        (list): A list of description names

    """
    return list(xg.descriptions(str(palette)))


def list_bound_geometry(description):
    """Return bounded meshes of the XGen Legacy description

    Args:
        description (str): XGen Legacy description name

    Return:
        (list): A list of bounded meshes' transform node name

    """
    palette = get_palette_by_description(description)
    return list(xg.boundGeometry(palette, description))


def preview_auto_update(auto):
    """XGen auto Update preview on/off

    Args:
        auto (bool): Auto update switch value

    """
    de = xgg.DescriptionEditor
    if de is not None:
        # set auto update
        de.setPlayblast(auto)
        de.updatePreviewControls()


def preview_refresh(level):
    """Refresh XGen preview

    Args:
        level (str): XGen refresh level: 'Full', 'Palette', 'Description'.

    """
    de = xgg.DescriptionEditor
    if de is not None:
        de.refresh(level)


def preview_clear():
    """Clear XGen preview"""
    de = xgg.DescriptionEditor
    if de is not None:
        # stop auto update
        de.setPlayblast(False)
        de.updatePreviewControls()
        # clear all preview
        de.clearMode = 2
        de.updateClearControls()
        de.clearPreview()


@contextlib.contextmanager
def xgen_preview_all(palette):
    """Preview all XGen Legacy primitives instead of in view only

    Args:
        palette (str): XGen Legacy palette name

    """
    origin_value = {}

    for desc in xg.descriptions(palette):
        origin_value[desc] = xg.getAttr("inCameraOnly",
                                        palette,
                                        desc,
                                        "GLRenderer")
        xg.setAttr("inCameraOnly", "false", palette, desc, "GLRenderer")

    try:
        yield

    finally:
        # restore value
        for desc in xg.descriptions(palette):
            xg.setAttr("inCameraOnly",
                       origin_value[desc],
                       palette,
                       desc,
                       "GLRenderer")


def parse_expr_maps(attr, palette, description, object):
    """Return a list of map file data from expression attribute in object

    This function was modified from `ExpressionUI.parseMapString`.

    Args:
        attr (str): Modifier attribute name
        palette (str): XGen Legacy palette name
        description (str): XGen Legacy description name
        object (str): Name of an XGen object

    Returns:
        (list): A list of `dict` object.
            Object Entry:
                {
                    "name": Expression var name,
                    "file": Map file path,
                    "mode": Map file mode,
                    "pos": Expression var in line position,
                }

    """
    expr = xg.getAttr(attr, palette, description, object)

    mapExprStrings = xg.ui.xgSetMapAttr.getMapExprStrings()
    exprStrings = [[mapExprStrings[0], "3dpaint"], [
        mapExprStrings[1], "file"], [mapExprStrings[2], "vpaint"]]

    retMaps = []
    for s in exprStrings:
        re = QtCore.QRegExp(s[0])
        offset = 0
        while True:
            item = ExpressionUI.MapItem()
            pos = re.indexIn(expr, offset)
            if (pos < 0):
                break
            offset = pos + 1
            item.name = re.cap(1)
            item.file = re.cap(2)
            item.mode = s[1]
            if s[1] == "3dpaint":
                item.mode = item.mode + "," + re.cap(3)

            item.pos = pos

            retMaps.append({
                "name": item.name,
                "file": item.file,
                "mode": item.mode,
                "pos": item.pos,
            })

    return retMaps


_ATTR_ALIAS = {
    "HeadBak": "bakeDir",
    "HeadPoint": "pointDir",
    "inputMap": "mapDir",
    "controlMap": "controlMapDir",
}


def parse_objects(map_attr):
    """Parse attribute returned from `filePathEditor` into XGen object names

    (NOTE) Remember to refresh filePathEditor by calling
           `cmds.filePathEditor(refresh=True)`
           or the fxmodule index might not return correctly

    >>> cmds.filePathEditor(refresh=True)
    >>> maps = cmds.filePathEditor(q=1, listFiles="", withAttribute=1)
    ["descriptionShape.primitive.ClumpingFXModule(1).HeadPoint", ...]
    >>> parse_objects(maps[0])
    ('pointDir', 'CY_Mon_Hair', 'description', 'Clumping2')

    Args:
        map_attr (str): An attribute path returned from `cmds.filePathEditor`

    Returns:
        tuple: Names of attribute, palette, description, object

    """
    address = map_attr.split(".")

    description = str(cmds.listRelatives(address[0], parent=True)[0])
    palette = get_palette_by_description(description)
    subtype = xg.getActive(palette, description, str(address[1].capitalize()))

    if len(address) < 4:
        attr = address[2].split("(")[0]
        attr = str(_ATTR_ALIAS.get(attr, attr))

        return attr, palette, description, subtype

    else:
        attr = address[3].split("(")[0]
        attr = str(_ATTR_ALIAS.get(attr, attr))

        modifier_cls, index = address[2][:-1].split("(")
        index = int(index)

        try:
            module = xg.fxModules(palette, description)[index]
        except IndexError:
            raise IndexError("Object not found, possible `filePathEditor` "
                             "not refreshed: {}".format(map_attr))
        else:
            if xg.fxModuleType(palette, description, module) == modifier_cls:

                return attr, palette, description, module

        raise Exception("Object not found, this is a bug: {}".format(map_attr))
