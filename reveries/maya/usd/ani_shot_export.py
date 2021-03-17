# -*- coding: utf-8 -*-

from avalon import io

from pxr import Usd, Sdf, UsdGeom
from reveries import common as utils
from reveries.common import get_frame_range
from reveries.common import get_publish_files

ANI_CACHE_FAMILY = [
    'reveries.pointcache.usd',
    'reveries.skeletoncache'
]


class AniUsdBuilder(object):
    def __init__(self, shot_name='', frame_in=None, frame_out=None):
        self.stage = None
        self.frame_in = frame_in
        self.frame_out = frame_out
        self.shot_name = shot_name
        self.asset_usd_dict = {}

        self._get_shot_data()
        self._build()

    def _get_shot_data(self):
        """
        Get shot data.
        asset_usd_dict = {
            'Char': {
                u'BoxC_rig_01_': u'/.../v003/USD/pointcache_prim.usda'
            },
            'props': {
            }
        }
        """
        if not self.frame_in or not self.frame_out:
            self.frame_in, self.frame_out = get_frame_range.get(self.shot_name)

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)
        shot_id = shot_data['_id']

        # Get animation cache
        _filter = {"type": "subset", "parent": shot_id}
        asset_datas = io.find(_filter)
        for asset_data in asset_datas:
            subset_name = asset_data['name']

            if asset_data["data"].get("subsetGroup", "") not in ["Animation"]:
                continue

            # Check family
            families = asset_data['data']["families"]

            if set(families).intersection(set(ANI_CACHE_FAMILY)):
                ns = self.__get_group_name(subset_name)
                asset_type = utils.check_asset_type_from_ns(ns)
                subset_id = asset_data['_id']
                files = get_publish_files.get_files(
                    subset_id,
                    key='entryFileName').get('USD', '')
                self.asset_usd_dict.setdefault(asset_type, dict())[ns] = files

        from pprint import pprint
        pprint(self.asset_usd_dict)

    def __get_group_name(self, subset_name):
        _type = subset_name.split('.')[0]
        if _type in ["pointcache"]:
            _prefix = "pc"
        else:
            _prefix = "sc"
        ns = "{}_{}".format(subset_name.split('.')[1], _prefix)

        return ns

    def _build(self):
        from reveries.common import get_fps
        from reveries.common.usd.utils import get_UpAxis

        self.stage = Usd.Stage.CreateInMemory()
        self.stage.SetStartTimeCode(self.frame_in)
        self.stage.SetEndTimeCode(self.frame_out)

        self.stage.SetFramesPerSecond(get_fps())
        self.stage.SetTimeCodesPerSecond(get_fps())
        UsdGeom.SetStageUpAxis(self.stage, get_UpAxis(host="Maya"))

        # Create ani prim
        shot_define = UsdGeom.Xform.Define(self.stage, "/ROOT")
        self.stage.GetRootLayer().documentation = \
            "Animation shot usd for {}".format(self.shot_name)

        for _asset_type in self.asset_usd_dict.keys():
            UsdGeom.Xform.Define(
                self.stage,
                "/ROOT/Asset/{}".format(_asset_type)
            )
            if _asset_type in self.asset_usd_dict.keys():
                for _asset_name, _usd_path in \
                        self.asset_usd_dict[_asset_type].items():
                    _instance_path = "/ROOT/Asset/{}/{}".format(
                        _asset_type, _asset_name)
                    UsdGeom.Xform.Define(self.stage, _instance_path)

                    # Add usd reference
                    if _usd_path:
                        _prim = self.stage.GetPrimAtPath(_instance_path)
                        _prim.GetReferences().SetReferences(
                            [Sdf.Reference(_usd_path)]
                        )

        # Add camera sublayer
        root_layer = self.stage.GetRootLayer()
        cam_prim_file = self._get_camera_prim_files(self.shot_name)
        if cam_prim_file:
            root_layer.subLayerPaths.append(cam_prim_file)

        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)

        # Override camera variant set
        ani_cam_subset_name = self._get_ani_cam_subset_name(self.shot_name)
        if ani_cam_subset_name:
            over_xform_prim = self.stage.OverridePrim("/ROOT/Camera")
            # variants = over_xform_prim.GetVariantSets(). \
            #     AddVariantSet("camera_subset")
            # variants.SetVariantSelection(ani_cam_subset_name)

            vs = over_xform_prim.GetVariantSet("camera_subset")
            vs.SetVariantSelection(ani_cam_subset_name)

    def _get_ani_cam_subset_name(self, shot_name):
        _filter = {'type': 'asset', 'name': shot_name}
        shot_data = io.find_one(_filter)

        _filter = {
            'type': 'subset',
            'data.task': 'animation',
            'data.families': 'reveries.camera',
            'parent': shot_data['_id']
        }
        subset_data = io.find_one(_filter)

        if subset_data:
            return subset_data.get("name", None)
        else:
            return None

    def _get_camera_prim_files(self, shot_name):
        _filter = {"type": "asset", "name": shot_name}
        shot_data = io.find_one(_filter)

        _filter = {
            "parent": shot_data["_id"],
            "name": "camPrim",
            "type": "subset"
        }
        subset_data = io.find_one(_filter)
        if subset_data:
            usd_file = get_publish_files.get_files(
                subset_data["_id"], key='entryFileName').get('USD', '')
            return usd_file

        return None

    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # print(self.stage.GetRootLayer().ExportToString())
