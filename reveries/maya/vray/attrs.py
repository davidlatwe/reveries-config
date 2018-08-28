"""
Extra V-Ray Attributes
https://docs.chaosgroup.com/display/VRAY3MAYA/Extra+V-Ray+Attributes

Scene Objects:
    Mesh
    NURBS Surface
    Particle
    Transform
    Curves

Lights and Cameras:
    Camera
    Light
    Material

Materials and Shading:
    Shading Group
    Texture
    Placement

Specialty:
    Fluid
    Hair
    Bifrost
    XGen Interactive Groom Splines

"""

import sys
import inspect
from maya import cmds

from ...vendor.six import string_types


class _AttrsGroup(object):

    def __init__(self, **kwargs):
        vray_attrs = self._vray_attrs()
        # input values
        for attr, value in kwargs.items():
            if attr in vray_attrs:
                setattr(self, attr, value)

    def _compatible(self, node):
        return cmds.nodeType(node) in self._types

    def _attr_group_exists(self, node):
        label_name = "vraySeparator_" + self._name
        return cmds.attributeQuery(label_name, node=node, exists=True)

    def _vray_attrs(self):
        return [attr for attr in dir(self) if attr.startswith("vray")]

    def _get(self, node):
        values = dict()

        if self._compatible(node) and self._attr_group_exists(node):
            for attr in self._vray_attrs():
                path = node + "." + attr

                values[attr] = cmds.getAttr(path)

        return values

    def get(self, nodes):
        if isinstance(nodes, string_types):
            return self._get(nodes)

        else:
            values_list = list()

            for node in nodes:
                values = self._get(node)
                if values:
                    values_list.append(values)

            return values_list

    def _cmds_setAttr(self, path, value):
        if isinstance(value, (tuple, list)):
            cmds.setAttr(path, *value)
        elif isinstance(value, string_types):
            cmds.setAttr(path, value, type="string")
        else:
            cmds.setAttr(path, value)

    def set(self, nodes):
        if isinstance(nodes, string_types):
            nodes = [nodes]

        for node in nodes:
            if not self._compatible(node):
                continue

            cmds.vray("addAttributesFromGroup", node, self._name, 1)

            for attr in self._vray_attrs():
                path = node + "." + attr
                value = getattr(self, attr)
                if value is not None:
                    self._cmds_setAttr(path, value)

    def unset(self, nodes):
        if isinstance(nodes, string_types):
            nodes = [nodes]

        for node in nodes:
            if not self._compatible(node):
                continue

            cmds.vray("addAttributesFromGroup", node, self._name, 0)


ATTRS_GROUP_CLS_MAP = {
    member._name: member for _, member in
    inspect.getmembers(sys.modules[__name__],
                       lambda mem: (inspect.isclass(mem) and
                                    hasattr(mem, "_name")))
}


def attributes_gather(node):
    attr_set = dict()

    for group_name, cls in ATTRS_GROUP_CLS_MAP.items():
        label_name = "vraySeparator_" + group_name
        if cmds.attributeQuery(label_name, node=node, exists=True):
            attr_set[group_name] = cls().get(node)

    return attr_set


def attributes_scatter(node, attr_set):
    for group_name, values in attr_set.items():
        cls = ATTRS_GROUP_CLS_MAP[group_name]
        cls(**values).set(node)


class SceneUserAttributes(_AttrsGroup):

    _name = "vray_user_attributes"

    _types = ("transform", "mesh", "nurbsSurface")

    vrayUserAttributes = None  # ""


class SceneObjectID(_AttrsGroup):

    _name = "vray_objectID"

    _types = (
        "transform",
        "mesh",
        "nurbsSurface",
        "VRayLightDomeShape",
        "VRayLightRectShape",
        "VRayLightSphereShape",
    )

    vrayObjectID = None  # 0


class TransformSkipRendering(_AttrsGroup):

    _name = "vray_skip_export"

    _types = ("transform",)

    vraySkipExport = None  # True


class MeshSubdivision(_AttrsGroup):

    _name = "vray_subdivision"

    _types = ("mesh",)

    vraySubdivEnable = None  # True
    vrayPreserveMapBorders = None  # 1
    vraySubdivUVs = None  # True
    vrayStaticSubdiv = None  # 1
    vrayClassicalCatmark = None  # False


class MeshSubdivsAndDispQuality(_AttrsGroup):

    _name = "vray_subquality"

    _types = ("mesh",)

    vrayOverrideGlobalSubQual = None  # True
    vrayViewDep = None  # True
    vrayEdgeLength = None  # 4.0
    vrayMaxSubdivs = None  # 4


class MeshDispControl(_AttrsGroup):

    _name = "vray_displacement"

    _types = ("mesh",)

    vrayDisplacementNone = None  # False
    vrayDisplacementStatic = None  # 1
    vrayDisplacementType = None  # 1
    vrayDisplacementAmount = None  # 1.0
    vrayDisplacementShift = None  # 0.0
    vrayDisplacementKeepContinuity = None  # False
    vrayEnableWaterLevel = None  # False
    vrayWaterLevel = None  # 0.0
    vrayDisplacementCacheNormals = None  # False
    vray2dDisplacementResolution = None  # 256
    vray2dDisplacementPrecision = None  # 8
    vray2dDisplacementTightBounds = None  # False
    vray2dDisplacementMultiTile = None  # False
    vray2dDisplacementFilterTexture = None  # True
    vray2dDisplacementFilterBlur = None  # 0.003
    vrayDisplacementUseBounds = None  # 0
    vrayDisplacementMinValue = None  # (0.0, 0.0, 0.0)
    vrayDisplacementMaxValue = None  # (1.0, 1.0, 1.0)


class MeshOpenSubdiv(_AttrsGroup):

    _name = "vray_opensubdiv"

    _types = ("mesh",)

    vrayOsdSubdivEnable = None  # True
    vrayOsdSubdivDepth = None  # 2
    vrayOsdSubdivType = None  # 0
    vrayOsdPreserveMapBorders = None  # 1
    vrayOsdSubdivUVs = None  # True
    vrayOsdPreserveGeomBorders = None  # False


class MeshRoundEdges(_AttrsGroup):

    _name = "vray_roundedges"

    _types = ("mesh",)

    vrayRoundEdges = None  # True
    vrayRoundEdgesRadius = None  # 1.0
    vrayRoundEdgesConsiderSameObjectsOnly = None  # True
    vrayRoundEdgesCorners = None  # 0


class MeshFogFadeOut(_AttrsGroup):

    _name = "vray_fogFadeOut"

    _types = ("mesh",)

    vrayFogFadeOut = None  # 0.0


class MeshLocalRayServer(_AttrsGroup):

    _name = "vray_localrayserver"

    _types = ("mesh",)

    vrayLocalRayserver = None  # True


class TextureInputGamma(_AttrsGroup):

    _name = "vray_file_gamma"

    _types = ("file", "VRayPtex", "substance", "imagePlane")

    vrayFileGammaEnable = None  # True
    vrayFileColorSpace = None  # 1
    vrayFileGammaValue = None  # 2.2


class TextureAllowNegColors(_AttrsGroup):

    _name = "vray_file_allow_neg_colors"

    _types = ("file", "substance", "imagePlane")

    vrayFileAllowNegColors = None  # True


class TextureImageFileList(_AttrsGroup):

    _name = "vray_file_ifl"

    _types = ("file",)

    vrayFileIFLStartFrame = None  # 0
    vrayFileIFLEndCondition = None  # 0
    vrayFileIFLPlaybackRate = None  # 1.0


class TextureFilter(_AttrsGroup):

    _name = "vray_texture_filter"

    _types = ("file", "substance")

    vrayOverrideTextureFilter = None  # True
    vrayTextureFilter = None  # 1
    vrayTextureSmoothType = None  # 0
