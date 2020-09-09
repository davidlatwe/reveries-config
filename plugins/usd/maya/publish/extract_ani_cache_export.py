import os
import pyblish.api
from avalon import io, api


class ExtractAniCacheUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

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
        # Get MOD group long neme
        self.mod_long_name, self.mod_root_path = self._get_mod_long_name(self.out_cache[0])

        # === Export source.usd === #
        self.source_outpath = os.path.join(self.staging_dir, self.files_info['source'])
        self._export_source(self.source_outpath)

        # === Export authored_data.usda === #
        outpath = os.path.join(self.staging_dir, self.files_info['authored_data'])
        self._export_authored_data(outpath)

        # === Export ani.usda === #
        outpath = os.path.join(self.staging_dir, self.files_info['ani'])
        self._export_ani(outpath)

        print 'Export ani cache usd done.'

    def _export_source(self, outpath):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        # cmds.select(self.out_cache)
        cmds.select(self.mod_long_name)  # r'HanMaleA_rig_02:HanMaleA_model_01_:MOD'

        exporter = MayaUsdExporter(export_path=outpath, export_selected=True)
        exporter.mergeTransformAndShape = True
        exporter.animation = True
        exporter.export()

    def _export_authored_data(self, outpath):
        from reveries.maya.usd import ani_cache_export

        # Check has proxy group
        has_proxy = self._check_has_proxy()

        ani_cache_export.export(self.source_outpath,
                                outpath,
                                mod_root_path=self.mod_root_path,
                                asset_name=self.asset_name,
                                has_proxy=has_proxy)

    def _export_ani(self, outpath):
        from pxr import Usd, UsdGeom
        from reveries.new_utils import get_publish_files

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

    def _get_mod_long_name(self, geom):
        import maya.cmds as cmds

        cmds.listRelatives(geom, allDescendents=True)
        geom_long = cmds.ls(geom, long=True)
        if not geom_long:
            self.log.warning('Get MOD group failed.')
            return ''
        parents = geom_long[0].split("|")[1:-1]
        parents_long_named = ["|".join(parents[:i]) for i in xrange(1, 1 + len(parents))]
        mod_long_name = [_p for _p in parents_long_named if _p.endswith(':MOD')]

        # Get mod root path
        mod_root_path = ''
        parents_without_ns = [parents[i].split(':')[-1] for i in xrange(0, len(parents))]
        for item in ["|".join(parents_without_ns[:i]) for i in xrange(1, 1 + len(parents_without_ns))]:
            if item.endswith('MOD'):
                mod_root_path = '|{}'.format(item).replace('|MOD', '').replace('|', '/')

        return mod_long_name[0] if mod_long_name else '', mod_root_path

    def _check_has_proxy(self):
        import maya.cmds as cmds

        ts_children = cmds.listRelatives(self.mod_long_name, ad=True, f=True, typ='transform')

        for _cache in self.out_cache + ts_children:
            if 'proxy_geo' in _cache:
                return True

        return False

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.new_utils import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)

