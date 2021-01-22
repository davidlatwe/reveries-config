import maya.cmds as cmds
import maya.api.OpenMaya as om
from pxr import Usd, UsdShade, UsdGeom, Sdf


class MtoaShadersToUSD:

    def __init__(self, filename=None, root=None):
        self.shaderMap = {}
        self.filename = filename
        self.root = root

    def exportUSD(self, scope="/ROOT/Looks"):
        assert self.root is not None

        self.shadingGroups = self.getShadingGroups(self.root)
        self.scope = scope
        cmds.arnoldExportAss(self.root, f=self.filename, s=1, shadowLinks=0, mask=16,
                             lightLinks=0, forceTranslateShadingEngines=1, boundingBox=1, fullPath=1)
        self.post_process()

    def post_process(self):
        stage = Usd.Stage.Open(self.filename)
        edit = Sdf.BatchNamespaceEdit()

        UsdGeom.Xform.Define(stage, "/ROOT")

        scope_prim = UsdGeom.Scope.Define(stage, self.scope)
        shaders_scope_prim = UsdGeom.Scope.Define(
            stage, self.scope + '/shaders')

        for prim in stage.Traverse():
            path = prim.GetPath()
            if prim.GetTypeName() == "Shader":
                if "/" not in str(path.MakeRelativePath("/")):
                    edit.Add(path, shaders_scope_prim.GetPath(
                    ).AppendPath(path.MakeRelativePath("/")))

        stage.GetRootLayer().Apply(edit)

        edit_dict = {}
        for i in edit.edits:
            edit_dict[i.currentPath] = i.newPath

        for prim in stage.Traverse():
            if prim.GetTypeName() == "Shader":
                shader = UsdShade.Shader.Define(stage, prim.GetPath())
                for i in shader.GetInputs():
                    attr = i.GetAttr()
                    if len(attr.GetConnections()) > 0:
                        con = attr.GetConnections()[0]
                        k = con.ReplacePrefix(
                            "/", shaders_scope_prim.GetPath())
                        i.ConnectToSource(k)

        for shadingGroup in self.shadingGroups:
            connection_attrs_map = {"surfaceShader": "surface",
                                    "displacementShader": "displacement", "volumeShader": "volume"}
            for connection_attr in connection_attrs_map.keys():
                maya_shader = cmds.listConnections(shadingGroup + "." + connection_attr)
                if maya_shader:
                    maya_shader = maya_shader[0]
                if maya_shader:
                    material = UsdShade.Material.Define(
                        stage, scope_prim.GetPath().AppendPath(self.stripNamespace(shadingGroup)))
                    shader = UsdShade.Shader.Define(
                        stage, shaders_scope_prim.GetPath().AppendPath(str(maya_shader)))
                    shader.CreateOutput(
                        connection_attrs_map[connection_attr], Sdf.ValueTypeNames.Token)
                    material.CreateOutput(
                        "arnold:" + connection_attrs_map[connection_attr], Sdf.ValueTypeNames.Token).ConnectToSource(shader, connection_attrs_map[connection_attr])

        # Set default prim to ROOT
        root_prim = stage.GetPrimAtPath("/ROOT")
        stage.SetDefaultPrim(root_prim)

        stage.Save()

    def getConnectionNodes(self, node, shadingGroup):
        res = cmds.listConnections(node, d=False, c=False, p=False)
        if res:
            for shader in res:
                self.shaderMap[str(shader)] = str(shadingGroup)
                self.getConnectionNodes(shader, shadingGroup)

    def setFilename(self, filename):
        self.filename = filename

    def getShadingGroups(self, root):
        children_meshs = cmds.listRelatives(
            root, ad=True, typ='surfaceShape', f=True)
        mesh_list = om.MSelectionList()
        for mesh in children_meshs:
            mesh_list.add(mesh)
        shadingGroup_list = []
        for i in range(mesh_list.length()):
            mesh = om.MFnMesh(mesh_list.getDagPath(i))
            shadingGroups = [om.MFnDependencyNode(
                x).name() for x in mesh.getConnectedShaders(0)[0]]
            shadingGroup_list += shadingGroups
        shadingGroup_list = list(set(shadingGroup_list))

        return shadingGroup_list

    def stripNamespace(self, name):
        _name = name.split(':')[-1]
        if ":" in _name:
            self.stripNamespace(_name)
        return _name


def export(sel, out_path=None):
    # sel = cmds.ls(sl=True)[0]
    # filenames = cmds.fileDialog2(
    #     fm=0, startingDirectory='C:/', fileFilter="USD (*.usd *.usda)")

    # if filenames:
    # filename = filenames[0]
    k = MtoaShadersToUSD(out_path, sel)
    k.exportUSD()
