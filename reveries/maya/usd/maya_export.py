
class MayaUsdExporter(object):
    EXT = "usd"
    TYPE = "usd"
    PLUGIN_NAMES = ["pxrUsd", "pxrUsdPreviewSurface"]

    def __init__(self, export_path=None, frame_range=[], export_selected=True,
                 rename_uv_set=True):
        """
        :param export_path:(str) absolute path for export dir or file
        :param frame_range:(list) list with 2 elements, first and last frame
        :param export_selected:(bool) Selection export True/False
        :param rename_uv_set:(bool) Rename uv set name to "st"
        """
        import maya.cmds as cmds

        self.load_plugin()

        if not frame_range:
            self.first_frame = cmds.playbackOptions(query=True, ast=True)
            self.end_frame = cmds.playbackOptions(query=True, aet=True)
        else:
            self.first_frame, self.end_frame = frame_range

        self.export_selected = bool(export_selected) or False

        # common options
        self.file_path = export_path
        self.frameRange = [self.first_frame, self.end_frame]
        self.selection = export_selected
        self.mergeTransformAndShape = True
        self.rename_uv_set = rename_uv_set

        # usd options
        self.exportColorSets = False
        self.exportUVs = False
        self.exportVisibility = True
        self.shadingMode = 'none'
        self.exportDisplayColor = False
        self.stripNamespaces = True

        self.animation = True
        self.nurbsCurves = True
        self.meshes = False

    def load_plugin(self):
        """
        Load usd plugin in current session
        """
        import maya.cmds as cmds

        for plugin_name in self.PLUGIN_NAMES:
            cmds.loadPlugin(plugin_name, quiet=True)

    def pre_process(self):
        if self.rename_uv_set:
            self._rename_uv_set("st")

    def post_process(self):
        if self.rename_uv_set:
            self._rename_uv_set("map1")

        return self.file_path

    def _rename_uv_set(self, new_name):
        import maya.cmds as cmds

        sel = cmds.ls(sl=True)[0]

        meshs = cmds.listRelatives(sel,
                                   type="shape",
                                   allDescendents=True,
                                   path=True)
        for _mesh in meshs:
            uvset = cmds.polyUVSet(_mesh, query=True, currentUVSet=True)
            if uvset:
                if uvset[0] != new_name:
                    cmds.polyUVSet(
                        _mesh, rename=True, newUVSet=new_name, uvSet=uvset[0])

    def export(self, plugin_name='usd'):

        self.pre_process()

        if plugin_name == 'usd':
            self.usd_export_cmd()
        else:
            self.al_export_cmd()

        return self.post_process()

    def usd_export_cmd(self):
        import maya.cmds as cmds

        if not self.animation:
            current_frame = cmds.currentTime(q=True)
            self.frameRange = [current_frame, current_frame]

        # Make sure that you have selected something in Maya before exporting
        cmds.usdExport(
            file=self.file_path,
            selection=self.selection,
            mergeTransformAndShape=self.mergeTransformAndShape,
            exportColorSets=self.exportColorSets,
            exportUVs=self.exportUVs,
            exportVisibility=self.exportVisibility,
            shadingMode=self.shadingMode,
            exportDisplayColor=self.exportDisplayColor,
            stripNamespaces=self.stripNamespaces,
            frameRange=self.frameRange
        )

    def al_export_cmd(self):
        import maya.cmds as cmds

        cmds.AL_usdmaya_ExportCommand(
            file=self.file_path,
            selected=self.selection,
            animation=self.animation,
            nurbsCurves=self.nurbsCurves,
            mergeTransforms=self.mergeTransformAndShape,
            frameRange=self.frameRange,
            meshes=self.meshes
        )
