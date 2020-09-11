import avalon

import pyblish.api


class ValidateAniUSDOutputs(pyblish.api.InstancePlugin):
    """Validate renderer setting exists in db."""

    order = pyblish.api.ValidatorOrder + 0.49

    label = "Validate Ani USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd"
    ]

    def process(self, instance):
        from reveries.maya import pipeline

        self.out_cache = instance.data.get("outCache")
        top_group = self.out_cache[0].split('|')[1]
        container = pipeline.get_container_from_group(top_group)

        # Check asset exists
        asset_data = self._check_asset_exists(container)
        if not asset_data:
            raise Exception("Can't found asset: {} in this show.".format(container.split('_')[0]))

        asset_id = asset_data['_id']
        asset_name = asset_data.get('name', '')
        instance.data["asset_name"] = asset_name

        # Check asset already publish USD geom.usd
        geom_exists = self._check_model_geom_exists(asset_id)
        # geom_exists = r'Q:\199909_AvalonPlay\Avalon\Char\Robot\publish\modelDefault\v001\USD\geom.usda'
        if not geom_exists:
            raise Exception("Can't found {} model USD publish file.".format(asset_name))

        # Check MOD group long name
        mod_long_name, mod_root_path = self._check_model_hierarchy(self.out_cache[0])
        if not mod_long_name or not mod_root_path:
            raise Exception("Can't get correct model hierarchy, please check with TD.")

        instance.data["mod_long_name"] = mod_long_name  # r'|..|..|HanMaleA_rig_02:HanMaleA_model_01_:Geometry'
        instance.data["mod_root_path"] = mod_root_path  # r'/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT'

    def _check_model_geom_exists(self, asset_id):
        from reveries.new_utils import get_publish_files

        # Get asset prim usd file
        _filter = {
            "type": "subset",
            "name": "assetPrim",
            "parent": asset_id
        }
        assetprim_data = avalon.io.find_one(_filter)
        if not assetprim_data:
            return ''

        asset_prim_usd_files = get_publish_files.get_files(assetprim_data['_id']).get('USD', [])

        return asset_prim_usd_files

    def _check_asset_exists(self, container):
        import maya.cmds as cmds

        asset_id = cmds.getAttr('{}.assetId'.format(container))
        _filter = {"type": "asset", "_id": avalon.io.ObjectId(asset_id)}
        asset_data = avalon.io.find_one(_filter)

        return asset_data

    def _check_model_hierarchy(self, geom):
        import maya.cmds as cmds

        cmds.listRelatives(geom, allDescendents=True)
        geom_long = cmds.ls(geom, long=True)
        if not geom_long:
            return '', ''
        parents = geom_long[0].split("|")[1:-1]
        parents_long_named = ["|".join(parents[:i]) for i in xrange(1, 1 + len(parents))]
        mod_long_name = [_p for _p in parents_long_named if _p.endswith(':Geometry')]  # MOD

        # Get mod root path
        mod_root_path = ''
        parents_without_ns = [parents[i].split(':')[-1] for i in xrange(0, len(parents))]
        for item in ["|".join(parents_without_ns[:i]) for i in xrange(1, 1 + len(parents_without_ns))]:
            # if item.endswith('MOD'):
            if item.endswith('ROOT') and item.split('|')[-2] != 'rigDefault':
                mod_root_path = '|{}'.format(item).replace('|MOD', '').replace('|', '/')

        return mod_long_name[0] if mod_long_name else '', mod_root_path
