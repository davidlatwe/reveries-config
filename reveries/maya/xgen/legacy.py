
import contextlib
import maya.cmds as cmds
import xgenm as xg
import xgenm.xgGlobal as xgg

from xgenm.ui.widgets.xgExpressionUI import ExpressionUI
from avalon.vendor.Qt import QtCore


def _getMapExprStrings():
    """Return patterns for parsing map file paths from expression

    The attribute value of mapped texture has format like:

        $a=map('${DESC}/paintmaps/length');
        $b=map('${DESC}/paintmaps/regionMask/myMap.ptx');#3dpaint,5.0
        $c=map('${DESC}/paintmaps/seq/mask_${PAL,mySeq}.ptx');#3dpaint,5.0

    The format of $b and $c was not supported in Maya, the pattenrs returned
    from this function does.

    """
    exprString0 = ('\\$(\\w+)\\s*=\\s*map\\([\"\']'
                   '([\\w${}\\-\\\\/.${,}]+)[\"\']\\);'
                   '\\s*#3dpaint,(-?[\\d.]*)')
    exprString1 = ('\\$(\\w+)\\s*=\\s*map\\([\"\']'
                   '([\\w${}\\-\\\\/.${,}]+)[\"\']\\);'
                   '\\s*#file')
    exprString2 = ('\\$(\\w+)\\s*=\\s*vmap\\([\"\']'
                   '([\\w${}\\-\\\\/.${,}]+)[\"\']\\);'
                   '\\s*#vpaint')
    exprStrings = [exprString0, exprString1, exprString2]

    return exprStrings


def _parseMapString(exprText):
    """Return a list of map file item from expression in an object attribute

    This function was modified from `ExpressionUI.parseMapString`.

    """
    # vmap and map expressions
    mapExprStrings = _getMapExprStrings()

    exprStrings = [
        [mapExprStrings[0], "3dpaint"],
        [mapExprStrings[1], "file"],
        [mapExprStrings[2], "vpaint"],
    ]

    retMaps = []
    for s in exprStrings:
        re = QtCore.QRegExp(s[0])
        offset = 0
        while True:
            item = ExpressionUI.MapItem()
            pos = re.indexIn(exprText, offset)
            if (pos < 0):
                break
            offset = pos + 1
            item.name = re.cap(1)
            item.file = re.cap(2)
            item.mode = s[1]
            if s[1] == "3dpaint":
                item.mode = item.mode + "," + re.cap(3)

            item.pos = pos

            retMaps.append(item)

    return retMaps


def _parseMapString_override(self, exprText):
    """This is used for overriding `ExpressionUI.parseMapString` in Maya

    (NOTE) Why we need to override ?
    In order to support explicit .ptx file path in expression.
    Here's the detail...

    XGen allowed explicity pointing a .ptx file in expression, like:
    ```
    $a=map('${DESC}/paintmaps/length');#3dpaint,5.0
    $b=map('${DESC}/paintmaps/variate/tweak.ptx');#3dpaint,5.0
    $a = $a * $b;
    $a

    ```
    But this would expose the enitre expression as plain string value in
    attribute GUI input field, not like the default format that has paint
    and save button next to the text field with only map dir path shown.

    To fix this, we need to modify the matching pattern for catching paths
    like these:
        map('${DESC}/paintmaps/regionMask/myMap.ptx')
        map('${DESC}/paintmaps/seq/mask_${PAL,mySeq}.ptx')

    Then the path would show up correctly in GUI, but there comes the next
    problem.

    Maya paint tool only use bounding geometry name as the file name to bake
    .ptx file, so those path with explicit custom name wont work with paint
    tool. So instead of exposing unusable widget, we filter out those paths
    from being shown on GUI.

    Finally, we could now pointing explicit .ptx file path in expression,
    without breaking the GUI.

    """
    filtered = list()
    # Here we use our own parser
    for item in _parseMapString(exprText):
        if item.file.endswith(".ptx"):
            # Block the explicit map path from GUI
            continue
        filtered.append(item)

    return filtered


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


@contextlib.contextmanager
def switch_data_path(palette, data_path):

    Args:



def parse_expr_maps(attr, palette, description, object):
    """Return a list of map file data from expression in an object attribute

    Args:
        attr (str): Modifier attribute name
        palette (str): XGen Legacy palette name
        description (str): XGen Legacy description name
        object (str): Name of an XGen object

    Returns:
        (list): A list of `ExpressionUI.MapItem` object.
            Object attribute:
                name: Expression var name
                file: Map file path
                mode: Map file mode
                pos: Expression var in line position

    """
    expr = xg.getAttr(attr, palette, description, object)
    return _parseMapString(expr)


_ATTR_ALIAS = {
    "region": "regionMap",
    "HeadBak": "bakeDir",
    "HeadPoint": "pointDir",
    "inputMap": "mapDir",
    "controlMap": "controlMapDir",
}


def _parse_attribute(attr):
    if attr.endswith(")"):
        attr, attr_indx = attr[:-1].split("(")
        attr_indx = int(attr_indx)
    else:
        attr_indx = 0

    attr = str(_ATTR_ALIAS.get(attr, attr))

    return attr, attr_indx


def parse_objects(map_attr):
    """Parse attribute returned from `filePathEditor` into XGen object names

    (NOTE) Remember to refresh filePathEditor by calling
           `cmds.filePathEditor(refresh=True)`, or the
           fxmodule index might not return correctly.

    >>> cmds.filePathEditor(refresh=True)
    >>> maps = cmds.filePathEditor(q=1, listFiles="", withAttribute=1)
    ["descriptionShape.primitive.ClumpingFXModule(1).HeadPoint", ...]
    >>> parse_objects(maps[0])
    ('CY_Mon_Hair', 'description', 'Clumping2', 'pointDir', 0)

    Args:
        map_attr (str): An attribute path returned from `cmds.filePathEditor`

    Returns:
        tuple: Names of palette, description, object, attr, attr-index

    """
    address = map_attr.split(".")

    description = str(cmds.listRelatives(address[0], parent=True)[0])
    palette = get_palette_by_description(description)
    subtype = xg.getActive(palette, description, str(address[1].capitalize()))

    if len(address) < 4:
        # Example: descriptionShape.generator.mask

        attr = address[2]
        attr, attr_indx = _parse_attribute(attr)

        return palette, description, subtype, attr, attr_indx

    else:
        # Example: descriptionShape.primitive.ClumpingFXModule(1).HeadPoint

        modifier_cls, mod_indx = address[2][:-1].split("(")
        mod_indx = int(mod_indx)

        attr = address[3]
        attr, attr_indx = _parse_attribute(attr)

        try:
            module = xg.fxModules(palette, description)[mod_indx]
        except IndexError:
            raise IndexError("Object not found, possible `filePathEditor` "
                             "not refreshed: {}".format(map_attr))
        else:
            if xg.fxModuleType(palette, description, module) == modifier_cls:

                return palette, description, module, attr, attr_indx

        raise Exception("Object not found, this is a bug: {}".format(map_attr))
