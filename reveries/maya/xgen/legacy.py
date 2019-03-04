
import os
import contextlib
import xgenm as xg
import xgenm.xgGlobal as xgg

from maya import cmds, mel
from avalon.vendor.Qt import QtCore
from .. import capsule


def _getMapExprStrings():
    """Return patterns for parsing map file paths from expression

    The attribute value of mapped texture has format like:

        $x=map('${DESC}/paintmaps/mask');
        $a=map('${DESC}/${HAHA}/mask');#3dpaint,5.0
        $b=map('${DESC}/paintmaps/regionMask/pSphere2.ptx');#3dpaint,5.0aa
        $c=map('${DESC}/paintmaps/mask_${PAL,mySeq}.ptx');#file
        $d=map('${DESC}/noise.%d.map.ptx', 10);#3dpaint,5.0
        $e=map('${DESC}/fenceColor-%04d.ptx', 12);
        $f=map('${DESC}/map_%d', $objectId);#3dpaint,5.0
        $g=map('${DESC}/map-%d.ptx', cycle($objectId, 10, 20));
        $h=map('${DESC}/map-%d.ptx', pick($objectId, 10, 20));#3dpaint,5.0

        or this kind... plain map()

        map('${DESC}/groom/orient/',0)

    The format of $b and $c was not supported in Maya, the pattenrs returned
    from this function does.

    """
    exprStr0 = ('\\$(\\w+)\\s*=\\s*map\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\);\\s*#3dpaint,(-?[\\d.]*)')

    exprStr1 = ('\\$(\\w+)\\s*=\\s*map\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\);\\s*#file')

    exprStr2 = ('\\$(\\w+)\\s*=\\s*vmap\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\);\\s*#vpaint')

    exprStr3 = ('\\$(\\w+)\\s*=\\s*map\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\);')

    exprStr4 = ('\\$(\\w+)\\s*=\\s*vmap\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\);')

    exprStr5 = ('map\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\)')

    exprStr6 = ('vmap\\([\"\']([\\w${}\\-\\\\/%.${,}]+)'
                '[\"\'][,.$()a-zA-Z0-9 ]*\\)')

    exprStrings = [exprStr0, exprStr1, exprStr2, exprStr3,
                   exprStr4, exprStr5, exprStr6]

    return exprStrings


def _parseMapString(exprText):
    """Return a list of map file item from expression in an object attribute

    This function was modified from `ExpressionUI.parseMapString`.

    """
    from xgenm.ui.widgets.xgExpressionUI import ExpressionUI

    # vmap and map expressions
    mapExprStrings = _getMapExprStrings()

    exprStrings = [
        [mapExprStrings[0], "3dpaint"],
        [mapExprStrings[1], "file"],
        [mapExprStrings[2], "vpaint"],
        [mapExprStrings[3], ""],  # map() without comment
        [mapExprStrings[4], ""],  # vmap() without comment
        [mapExprStrings[5], "_plain"],  # plain map(), no comment
        [mapExprStrings[6], "_plain"],  # plain vmap(), no comment
    ]

    poses = []
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

            if pos in poses:
                # Possible already matched via previous regex if current
                # regex does no matching comment string.
                continue
            poses.append(pos)

            if s[1] == "_plain":
                item.name = ""
                item.file = re.cap(1)
                item.mode = ""
            else:
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
        if item.file.endswith(".ptx") or "%" in item.file:
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


def list_guides(description):
    return xg.descriptionGuides(description)


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


def current_data_path(palette, expand=False):
    path = xg.getAttr("xgDataPath", palette)
    if expand:
        return xg.expandFilepath(str(path), "")
    return path


@contextlib.contextmanager
def switch_data_path(palette, data_path):
    """Switch xgDataPath context

    Args:
        palette (str): XGen Legacy palette name
        data_path (str): xgDataPath

    """
    origin = xg.getAttr("xgDataPath", palette)
    data_path = data_path.replace("\\", "/")
    try:
        xg.setAttr("xgDataPath", data_path, palette)
        yield
    finally:
        xg.setAttr("xgDataPath", origin, palette)


def set_data_path(palette, data_path):
    data_path = data_path.replace("\\", "/")
    xg.setAttr("xgDataPath", str(data_path), str(palette))


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
    "inputMap": "mapDir",
    "controlMap": "controlMapDir",
    "tiltU": "offU",
    "tiltV": "offV",
    "tiltN": "offN",
    "aroundN": "aboutN",
}


def _parse_attribute(attr):
    if attr.endswith(")"):
        attr, attr_indx = attr[:-1].split("(")
        attr_indx = int(attr_indx)
    else:
        attr_indx = 0

    try:
        attr = _ATTR_ALIAS[attr]
    except KeyError:
        # (TODO) It seems these attributes will prefixed
        #        with description name.
        if attr.endswith("Bak"):
            attr = "bakeDir"
        elif attr.endswith("Point"):
            attr = "pointDir"
    finally:
        attr = str(attr)

    return attr, attr_indx


def get_palette_long_name(palette):
    """Return palette long name from short name

    This is useful if there are other nodes using same name

    Args:
        palette (str): XGen Legacy palette name

    Returns:
        str: XGen Legacy palette long name

    """
    for node in cmds.ls(palette, long=True):
        if cmds.nodeType(node) == "xgmPalette":
            return node


def get_description_long_name(description, shape=False):
    """Return palette long name from short name

    This is useful if there are other nodes using same name

    Args:
        description (str): XGen Legacy description name
        shape (bool, optional): Decide to return shape node or transform
            node name. Default `False` (return transform)

    Returns:
        str: XGen Legacy description long name

    """
    for node in cmds.ls(description, long=True):
        shapes = cmds.listRelatives(node,
                                    shapes=True,
                                    fullPath=True) or []
        if not shapes:
            continue

        for shape_node in shapes:
            if cmds.nodeType(shape_node) == "xgmDescription":
                return shape_node if shape else node


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

    # The description shape name in `map_attr` string is a short name,
    # and since we only need the description transform short name, it
    # doesn't matter which shape node we get from `cmds.ls`.
    desc_shape = cmds.ls(address[0])[0]
    description = str(cmds.listRelatives(desc_shape,
                                         parent=True)[0])  # get short name
    palette = get_palette_by_description(description)

    if address[1] == "glRenderer":
        subtype = "GLRenderer"
    else:
        # primitive, generator
        subtype = xg.getActive(palette,
                               description,
                               str(address[1].capitalize()))

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


def parse_map_path(map_attr):
    """Parse attribute returned from `filePathEditor` into file path

    (NOTE) Remember to refresh filePathEditor by calling
           `cmds.filePathEditor(refresh=True)`, or the
           fxmodule index might not return correctly.

    Args:
        map_attr (str): An attribute path returned from `cmds.filePathEditor`

    Returns:
        str: File path
        tuple: Name of the attribute and it's parent objects

    """
    palette, description, obj, attr, index = parse_objects(map_attr)

    expr_maps = parse_expr_maps(attr, palette, description, obj)

    if not expr_maps:
        # Not expression type
        path = xg.getAttr(attr, palette, description, obj)
    else:
        path = expr_maps[index].file

    parents = (palette, description, obj, attr, index)

    return path, parents


def parse_description_maps(description):
    """Get all path of maps and attributes which used them by description

    Args:
        description (str): XGen Legacy description name

    Returns:
        list: A list of tuple of file path and attribute objects

    """
    cmds.filePathEditor(refresh=True)
    resloved = (cmds.filePathEditor(query=True,
                                    listFiles="",
                                    withAttribute=True,
                                    byType="xgmDescription",
                                    unresolved=False) or [])

    collected_paths = list()

    desc_shape_long = get_description_long_name(description, shape=True)

    for map_attr, fname in zip(resloved[1::2], resloved[0::2]):
        desc_shape = map_attr.split(".", 1)[0]
        if desc_shape_long not in cmds.ls(desc_shape,
                                          type="xgmDescription",
                                          long=True):
            continue

        path, parents = parse_map_path(map_attr)

        if not path.endswith(".ptx"):
            sep = "" if path.endswith("/") else "/"
            path += sep + fname

        collected_paths.append((path, parents))

    return collected_paths


def maps_to_transfer(description):
    """Get all expanded map file/dir path from description for transfer

    Args:
        description (str): XGen Legacy description name

    Returns:
        list: A list of collected map files

    Raise:
        RuntimeError if collected path not exists.

    """
    transfer = set()

    for path, parents in parse_description_maps(description):
        if "${FXMODULE}" in path:
            path = path.replace("${FXMODULE}", parents[2])
        dir_path = os.path.dirname(path)
        dir_path = xg.expandFilepath(str(dir_path), str(description))

        if not os.path.isdir(dir_path):
            raise RuntimeError("{0}: Map dir not exists: {1}"
                               "".format(parents, dir_path))

        file_name = os.path.basename(path)
        file_path = os.path.join(dir_path, file_name)

        if os.path.isfile(file_path):
            # Copy file
            transfer.add(file_path.replace("\\", "/"))

        else:
            # Possible contain variables in file name, copy folder
            for file in os.listdir(dir_path):
                path = os.path.join(dir_path, file)
                if os.path.isfile(path):
                    transfer.add(path.replace("\\", "/"))

    return sorted(list(transfer))


def bake_description(palette, description, rebake=False):
    """Bake a description and it's modifiers which data needs to be baked

    Args:
        palette (str): XGen Legacy palette name
        description (str): XGen Legacy description name
        rebake (bool): Remove previous bake groom modifier if set to True,
            default False.

    Raise:
        RuntimeError if there are bake groom modifier existed and `rebake`
            is False.

    """
    fxmod_typ = (lambda fxm: xg.fxModuleType(palette, description, fxm))

    fx_modules = xg.fxModules(palette, description)

    for fxm in fx_modules:
        if not fxmod_typ(fxm) == "BakedGroomManagerFXModule":
            continue
        if not rebake:
            raise RuntimeError("This description has been baked.")
        # Remove bake module
        xg.removeFXModule(palette, description, fxm)

    previous_clump = None

    # (NOTE) fxModules iterate from bottom to top
    for fxm in fx_modules:

        if fxmod_typ(fxm) == "ClumpingFXModule":
            # set the top clumpingMod cvAttr to True, for AnimModifiers
            # which needs clump
            if previous_clump:
                xg.setAttr("cvAttr",
                           "false",
                           palette,
                           description,
                           previous_clump)

            xg.setAttr("cvAttr", "true", palette, description, fxm)
            previous_clump = fxm

        if fxmod_typ(fxm) in ("NoiseFXModule", "MeshCutFXModule"):
            # temporarily turn off lod so we dont bake it in
            lod = xg.getAttr("lodFlag", palette, description)
            xg.setAttr("lodFlag", "false", palette, description)
            # change mode for bake
            xg.setAttr("mode", "2", palette, description, fxm)
            # bake the noise
            cmds.xgmNullRender(description, progress=True)
            # restore
            xg.setAttr("lodFlag", lod, palette, description)
            # change mode to baked
            xg.setAttr("mode", "1", palette, description, fxm)

    # bake groom modifiers
    fxm = xg.addFXModule(palette, description, "BakedGroomManagerFXModule")
    xg.setAttr("active", "true", palette, description, fxm)
    xg.bakedGroomManagerBake(palette, description)
    # set Generator to XPD
    xg.setActive(palette, description, "FileGenerator")


def guides_to_curves(guides):
    cmds.select(guides, replace=True)
    return mel.eval("xgmCreateCurvesFromGuides(0, true)")


def curves_to_guides(description, curves):
    cmds.select(curves, replace=True)
    return mel.eval("xgmCurveToGuide -tipSnapPower 1.0 -tipSnapAmount 1.0 "
                    "-deleteCurve -description {}".format(description))


def export_palette(palette, out_path):
    out_path = out_path.replace("\\", "/")
    xg.exportPalette(str(palette), str(out_path))


def import_palette(xgen_path, deltas=None, namespace="", wrapPatches=True):
    xgen_path = xgen_path.replace("\\", "/")
    deltas = deltas or []
    return xg.importPalette(str(xgen_path),
                            deltas,
                            str(namespace),
                            bool(wrapPatches))


def bind(description, meshes):
    """Bind description to meshes

    Args:
        description (str): XGen Legacy description name
        meshes (list): A list of meshes (transform node names) to bind with

    """
    palette = get_palette_by_description(description)
    with capsule.maintained_selection():
        cmds.select(meshes, replace=True)
        xg.modifyFaceBinding(palette,
                             description,
                             mode="Append",
                             placeGuidesWithUVBasedMethod=True,
                             rotateGuide=False)


def description_ctrl_method(description):
    """
    Find out what instance method used by description to control primitives,
    and return type name:
        'Guides'
        'Attribute'
        'Groom'
    """
    palette = get_palette_by_description(description)
    primitive = xg.getActive(palette, description, "Primitive")

    if xg.getAttr("iMethod", palette, description, primitive):
        return "Guides"
    else:
        if xg.getAttr("groom", palette, description):
            return "Groom"
        else:
            return "Attribute"


def save_culled_as_delta(palette, out_path):
    """Save culled primitives info as XGen delta

    Args:
        palette (str): XGen Legacy palette name
        out_path (str): .xgd file output path

    """
    header = ("# XGen Delta File (Culled Primitives)\n"
              "#\n"
              "# Version:  {version}\n"
              "# Author:   {user}\n"
              "# Date:     {date}\n")

    lines = []
    line = "Patch   culledPrims {patch}    {description}  {face} {len} {ids}"
    for description in list_descriptions(palette):
        for patch in xg.culledPrimPatches(palette, description):
            for face in xg.culledPrimFaces(palette, description, patch):
                ids = xg.culledPrims(palette, description, patch, face)
                lines.append(line.format(patch=patch,
                                         description=description,
                                         face=face,
                                         len=len(ids),
                                         ids=" ".join(str(i) for i in ids)))
            lines.append("\n")

    if not lines:
        return False

    delta = header.format(version=cmds.getAttr(palette + ".xgVersion"),
                          user=os.environ.get("USER", ""),
                          date=cmds.about(ctime=True))
    delta += "\n".join(lines)

    out_dir = os.path.dirname(out_path)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    with open(out_path, "w") as xgd:
        xgd.write(delta)

    return True


def apply_deltas(palette, delta_paths):
    """Apply deltas to palette

    Args:
        palette (str): XGen Legacy palette name
        delta_paths (list): A list of .xgd file path

    """
    for path in delta_paths:
        xg.applyDelta(str(palette), str(path))


def disable_tube_shade(palette):
    """
    Args:
        palette (str): XGen Legacy palette name
    """
    palette = str(palette)
    for description in list_descriptions(palette):
        prim = xg.getActive(palette, description, "Primitive")
        if xg.attrExists("tubeShade", palette, description, prim):
            xg.setAttr("tubeShade", "false", palette, description, prim)


def disable_in_camera_only(palette):
    """
    Args:
        palette (str): XGen Legacy palette name
    """
    palette = str(palette)
    for description in list_descriptions(palette):
        prev = xg.getActive(palette, description, "Previewer")
        if xg.attrExists("inCameraOnly", palette, description, prev):
            xg.setAttr("inCameraOnly", "false", palette, description, prev)


def delete_palette(palette):
    """
    Args:
        palette (str): XGen Legacy palette name
    """
    xg.deletePalette(str(palette))
