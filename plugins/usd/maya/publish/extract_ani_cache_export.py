import os
import pyblish.api
from avalon import io, api


class ExtractAniCacheUSDExport(pyblish.api.InstancePlugin):
    """Publish animation usd file.

    """

    order = pyblish.api.ExtractorOrder + 0.492
    hosts = ["maya"]
    label = "Extract PointCache (usd)"
    families = [
        "reveries.pointcache.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin

        self.out_cache = instance.data.get("outCache")
        self.start_frame = instance.data.get("startFrame")
        self.end_frame = instance.data.get("endFrame")
        self.mod_long_name = instance.data.get("mod_long_name")
        self.mod_root_path = instance.data.get("mod_root_path")
        self.asset_name = instance.data.get("asset_name")

        if not self.out_cache:
            self.log.warning("No output geometry found in your scene.")
            return

        if not self.start_frame or not self.end_frame:
            self.log.warning("No frame range found in your instance.")
            return

        self.files_info = {
            'authored_data': 'authored_data.usda',
            'source': 'source.usda',
            'ani': 'ani_cache_prim.usda'
        }
        self.staging_dir = utils.stage_dir()

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [
            self.files_info['authored_data'],
            self.files_info['source'],
            self.files_info['ani']
        ]
        instance.data["repr.USD.entryFileName"] = self.files_info['ani']

        load_maya_plugin()
        self.export_usd()

        self._publish_instance(instance)

    def export_usd(self):
        print 'start frame: {}\nend_frame: {}'.format(self.start_frame, self.end_frame)

        # === Export source.usd === #
        self.source_outpath = os.path.join(self.staging_dir, self.files_info['source'])
        self._export_source(self.source_outpath)
        print 'source.usda done.'

        # === Export authored_data.usda === #
        outpath = os.path.join(self.staging_dir, self.files_info['authored_data'])
        self._export_authored_data(outpath)
        print 'authored_data.usda done'

        # === Export ani.usda === #
        outpath = os.path.join(self.staging_dir, self.files_info['ani'])
        self._export_ani(outpath)

        print 'Export ani_cache_prim.usda done.'

    def _export_source(self, outpath):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        cmds.select(self.mod_long_name)  # r'HanMaleA_rig_02:HanMaleA_model_01_:Geometry'

        exporter = MayaUsdExporter(export_path=outpath,
                                   frame_range=[self.start_frame, self.end_frame],
                                   export_selected=True)
        exporter.mergeTransformAndShape = True
        exporter.animation = True
        exporter.export()

        cmds.select(cl=True)

    def _export_authored_data(self, outpath):
        from reveries.maya.usd import ani_cache_export

        # Check has proxy group
        has_proxy = self._check_has_proxy()

        ani_cache_export.export(
            self.source_outpath, outpath,
            mod_root_path=self.mod_root_path,  # r'/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT'
            asset_name=self.asset_name,
            has_proxy=has_proxy
        )

    def _export_ani(self, outpath):
        from pxr import Usd, UsdGeom
        from reveries.common import get_publish_files

        # Get asset id
        _filter = {"type": "asset", "name": self.asset_name}
        asset_data = io.find_one(_filter)
        asset_id = asset_data['_id']

        # Get asset prim usd file
        _filter = {
            "type": "subset",
            "name": "assetPrim",
            "parent": asset_id
        }
        assetprim_data = io.find_one(_filter)
        asset_prim_usd_files = get_publish_files.get_files(assetprim_data['_id']).get('USD', [])

        if asset_prim_usd_files:
            asset_prim_usd = asset_prim_usd_files[0]
        else:
            asset_prim_usd = ''
            self.log.warning('No asset prim publish file found.')

        # Generate usd file
        stage = Usd.Stage.CreateInMemory()

        root_layer = stage.GetRootLayer()
        root_layer.subLayerPaths.append(self.files_info['authored_data'])
        root_layer.subLayerPaths.append(asset_prim_usd)

        UsdGeom.Xform.Define(stage, "/ROOT")
        shot_prim = stage.GetPrimAtPath('/ROOT')
        stage.SetDefaultPrim(shot_prim)
        stage.SetStartTimeCode(self.start_frame)
        stage.SetEndTimeCode(self.end_frame)

        stage.GetRootLayer().Export(outpath)

    def _check_has_proxy(self):
        import maya.cmds as cmds

        ts_children = cmds.listRelatives(self.mod_long_name, ad=True, f=True, typ='transform')

        for _cache in self.out_cache + ts_children:
            if 'proxy_geo' in _cache:
                return True

        return False

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)

