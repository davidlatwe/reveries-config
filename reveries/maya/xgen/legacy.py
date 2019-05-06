
import os
import contextlib
import xgenm as xg
import xgenm.xgGlobal as xgg

import pymel.core as pmc
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


def list_fx_modules(description, activated=None):
    palette = get_palette_by_description(description)
    modules = xg.fxModules(palette, description)

    if activated is not None:
        state = "true" if activated else "false"
        matched = list()
        for fxm in modules:
            if xg.getAttr("active", palette, description, fxm) == state:
                matched.append(fxm)
        return matched

    else:
        return modules


def is_modifier_under_bake_manager(palette, description, modifier):
    """Is this modifier stack under an active bake groom manager ?

    Args:
        palette (str): XGen Legacy palette name
        description (str): XGen Legacy description name
        modifier (str): Name of an XGen modifier object

    Returns:
        (bool)

    """
    fxmod_typ = (lambda fxm: xg.fxModuleType(palette, description, fxm))

    fx_modules = xg.fxModules(palette, description)
    bake_found = False
    for fxm in reversed(fx_modules):
        if fxm == modifier:
            return bake_found

        if fxmod_typ(fxm) == "BakedGroomManagerFXModule":
            if xg.getAttr("active", palette, description, fxm) == "true":
                bake_found = True


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


def current_data_paths(palette, expand=False):
    paths = list()
    for path in xg.getAttr("xgDataPath", palette).split(";"):
        if expand:
            path = xg.expandFilepath(str(path), "")
        paths.append(path)
    return paths


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
    "MeshFile": "meshFile",
    "inputMapDir": "controlMapDir",
    "controlMap": "controlMapDir",
    "tiltU": "offU",
    "tiltV": "offV",
    "tiltN": "offN",
    "aroundN": "aboutN",
}


def _parse_attribute(attr, obj):
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
        if attr.endswith("Bak") or attr.endswith("Bake"):
            attr = "bakeDir"
        elif attr.endswith("Point"):
            if obj == "FileGenerator":
                attr = "inputDir"
            else:
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
        attr, attr_indx = _parse_attribute(attr, subtype)

        return palette, description, subtype, attr, attr_indx

    else:
        # Example: descriptionShape.primitive.ClumpingFXModule(1).HeadPoint

        modifier_cls, mod_indx = address[2][:-1].split("(")
        mod_indx = int(mod_indx)

        attr = address[3]
        attr, attr_indx = _parse_attribute(attr, subtype)

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

        if not (path.endswith(".ptx") or path.endswith(".abc")):
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
        palette, _, obj, _, _ = parents
        if obj in list_fx_modules(description, activated=False):
            # Ignore if not active
            cmds.warning("FxModule %s not active, transfer skipped." % obj)
            continue

        if is_modifier_under_bake_manager(palette,
                                          description,
                                          obj):
            # Ignore if obj is a modifier and is under an active bake
            # groom manager
            continue

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
    """Bake description with BakedGroomManagerFXModule

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

    # bake groom modifiers
    fxm = xg.addFXModule(palette, description, "BakedGroomManagerFXModule")
    xg.setAttr("active", "true", palette, description, fxm)
    xg.bakedGroomManagerBake(palette, description)
    # set Generator to XPD
    xg.setActive(palette, description, "FileGenerator")


def bake_modules(palette, description):
    """Bake description's modifiers which data needs to be baked

    This bakes NoiseFXModule and MeshCutFXModule, also set ClumpingFXModule
    attribute 'cvAttr' to True for AnimModifiers.

    Args:
        palette (str): XGen Legacy palette name
        description (str): XGen Legacy description name

    """
    fxmod_typ = (lambda fxm: xg.fxModuleType(palette, description, fxm))

    fx_modules = xg.fxModules(palette, description)

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


def guides_to_curves(guides):
    cmds.select(guides, replace=True)
    # This mel command does not reture correct converted curve names,
    # only selecting them.
    mel.eval("xgmCreateCurvesFromGuides(0, true)")
    # Return curve name by selection
    return cmds.ls(selection=True, long=True)


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

    if xg.getAttr("iMethod", palette, description, primitive) == "1":
        return "Guides"
    else:
        # iMethod == "0"
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


def build_hair_system(palette):
    """Build hair system and link to the descriptions that has animWire modifier

    Args:
        palette (str): XGen Legacy palette name

    """

    def exportCurvesMel(descName):
        """
        Replace original "exportCurvesMel", since "xgmNullRender" will fail
        if scene is too large
        """
        # select guides
        cmds.select(xg.descriptionGuides(descName), replace=True)
        # guides to curves
        pmc.mel.xgmCreateCurvesFromGuides(0, False)

    def xgmMakeCurvesDynamic(descHairSysName, collide):
        """
        Create nHairSystem with good name before MakeCurvesDynamic
        and without optionBox UI
        """
        selection = pmc.ls(sl=True, long=True)
        # find hair holding mesh for later rigid body rename
        meshPatch = []
        for dag in selection:
            if dag.getShape().type() == "mesh":
                meshPatch.append(dag.name())

        # create the first time we hit a valid curve
        hsys = pmc.createNode("hairSystem")
        hsys.getParent().rename(descHairSysName)

        # we want uniform stiffness because the curves
        # are initially point locked to both ends
        pmc.removeMultiInstance(hsys.stiffnessScale[1], b=True)

        hsys.clumpWidth.set(0.00001)
        hsys.hairsPerClump.set(1)
        pmc.connectAttr("time1.outTime", hsys.currentTime)

        nucleus = pmc.mel.getActiveNucleusNode(False, True)
        pmc.mel.addActiveToNSystem(hsys, nucleus)
        pmc.connectAttr(nucleus + ".startFrame", hsys.startFrame)

        # select the hairSystem we just created and well named,
        # and maya won't create one when making curves dynamic
        selection.append(hsys)
        # re-select curves, mesh and hairSystem
        pmc.select(selection, replace=True)
        # trun on 'Collide With Mesh'
        pmc.optionVar(
            intValue=["makeCurvesDynamicCollideWithMesh", int(collide)]
        )
        # MakeCurvesDynamic callback
        mel.eval('makeCurvesDynamic 2 { "1", "1", "1", "1", "0"}')

        return meshPatch, hsys.name()

    def nRigidRename(meshPatch):
        # `meshPatch` is a list of geo long name
        renameDict = {}
        for rigid in cmds.ls(type="nRigid"):
            shapes = cmds.listConnections(rigid + ".inputMesh", shapes=True)
            if shapes and cmds.nodeType(shapes[0]) == "mesh":
                meshName = cmds.listRelatives(shapes[0],
                                              parent=True,
                                              fullPath=True)[0]
                if meshName in meshPatch:
                    renameDict[rigid] = meshName
        # rename rigid body
        for rigidName in renameDict:
            rigid = cmds.ls(rigidName)
            if not rigid:
                continue
            cmds.rename(cmds.listRelatives(rigid[0], parent=True)[0],
                        "%s_nRigid" % renameDict[rigidName])

    def getHairCurves(descHairSysName):
        """List out curves which output from descHairSysName"""
        # since we had our nHairSystem well named, we can search it by name
        hsysList = cmds.ls(descHairSysName)
        if not hsysList:
            return

        curves = []
        shapes = cmds.listRelatives(hsysList[0], shapes=True, fullPath=True)
        if cmds.nodeType(shapes[0]) == "hairSystem":
            # find curves
            hsys = shapes[0]
            follicles = cmds.listConnections(
                hsys + ".inputHair", shapes=True, type="follicle")
            for foll in follicles:
                curve = cmds.listConnections(
                    foll + ".outCurve", shapes=True, type="nurbsCurve")
                curves.extend(curve)
        return curves

    def attachSlot(palette, desc, fxmName, descHairSysName):
        if not (str(xg.fxModuleType(palette, desc, fxmName)) ==
                "AnimWiresFXModule"):
            return

        refwFrame = xg.getAttr("refWiresFrame", palette, desc, fxmName)
        if str(xg.getAttr("liveMode", palette, desc, fxmName)) == "false":
            wiresfile = xg.getAttr("wiresFile", palette, desc, fxmName)
            pmc.mel.xgmFindAttachment(
                d=desc, f=wiresfile, fm=int(refwFrame), m=fxmName)
        else:
            curves = getHairCurves(descHairSysName)
            if curves:
                # attach wires to curves
                cmds.select(curves, replace=True)
                pmc.mel.xgmFindAttachment(d=desc, fm=int(refwFrame), m=fxmName)
                # print('The following curves were attached: ',
                #       [c.name() for c in curves])
            else:
                cmds.warning("No curves selected. Nothing to attach.")

    # Start process

    preview_clear()

    get_hsys_name = (lambda desc: desc + "_hairSystem")

    nHairAttrs = {
        "stretchResistance": 600,
        "compressionResistance": 100,
        "startCurveAttract": 0.3,
        "mass": 0.05
    }

    palette = str(palette)

    # get active AnimWire module list
    animWireDict = {}
    for desc in xg.descriptions(palette):
        for fxm in xg.fxModules(palette, desc):
            if xg.fxModuleType(palette, desc, fxm) != "AnimWiresFXModule":
                continue
            if xg.getAttr("active", palette, desc, fxm) == "true":

                hsysName = get_hsys_name(desc)
                hsysTransforms = [cmds.listRelatives(hsys, parent=True)[0]
                                  for hsys in cmds.ls(type="hairSystem")]

                if hsysName in hsysTransforms:
                    cmds.warning("Description %s has hairSystem [%s], "
                                 "skipped." % (desc, hsysName))
                else:
                    animWireDict[desc] = fxm

    # build hairSystem
    for desc in animWireDict:

        print("Building hairSystem for description: %s, FXModule: %s"
              "" % (desc, fxm))

        fxm = animWireDict[desc]
        descHairSysName = get_hsys_name(desc)

        exportCurvesMel(desc)
        # add patch to selection
        cmds.select(list_bound_geometry(desc), add=True)
        meshPatch, hsys = xgmMakeCurvesDynamic(descHairSysName, False)
        nRigidRename(meshPatch)
        attachSlot(palette, desc, fxm, descHairSysName)

        print("HairSystem linked.")

        # set some attributes
        for attr, val in nHairAttrs.items():
            cmds.setAttr(hsys + "." + attr, val)


def set_refWires_frame(refWiresFrame, palette):
    """Setup refWireFrame to the descriptions that has animWire modifier

    Args:
        refWiresFrame (int, float): refWireFrame value
        palette (str): XGen Legacy palette name

    """
    refWiresFrame = str(int(refWiresFrame))
    palette = str(palette)

    for desc in xg.descriptions(palette):
        for fxm in xg.fxModules(palette, desc):
            if xg.fxModuleType(palette, desc, fxm) != "AnimWiresFXModule":
                continue
            xg.setAttr("refWiresFrame", refWiresFrame, palette, desc, fxm)
