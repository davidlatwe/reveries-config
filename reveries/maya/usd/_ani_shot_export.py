# -*- coding: utf-8 -*-

from avalon import io

from pxr import Usd, Sdf, UsdGeom
from reveries import common as utils
from reveries.common import get_publish_files


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
            'character': {
                u'HanMaleA_rig_02': u'Q:/199909_AvalonPlay/Avalon/Shot/sh0100/publish/usd.HanMaleA_rig_02.Default/v002/USD/ani_prim.usda'
            },
            'props': {
            }
        }
        """
        if not self.frame_in or not self.frame_out:
            self.frame_in, self.frame_out = utils.get_frame_range(self.shot_name)

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)
        shot_id = shot_data['_id']

        #
        _filter = {"type": "subset", "parent": shot_id}
        asset_datas = io.find(_filter)
        for asset_data in asset_datas:
            subset_name = asset_data['name']
            if subset_name.startswith('pointcache.'):
                ns = subset_name.split('.')[1]
                asset_type = utils.check_asset_type_from_ns(ns)
                subset_id = asset_data['_id']
                files = get_publish_files.get_files(subset_id, key='entryFileName').get('USD', '')
                self.asset_usd_dict.setdefault(asset_type, dict())[ns] = files

        from pprint import pprint
        pprint(self.asset_usd_dict)

    def _build(self):
        self.stage = Usd.Stage.CreateInMemory()
        self.stage.SetStartTimeCode(self.frame_in)
        self.stage.SetEndTimeCode(self.frame_out)

        # Create shot prim
        shot_define = UsdGeom.Xform.Define(self.stage, "/ROOT")
        self.stage.GetRootLayer().documentation = "Animation shot usd for {}".format(self.shot_name)

        # Add shot variants
        variants = shot_define.GetPrim().GetVariantSets().AddVariantSet("shot")
        variants.AddVariant(self.shot_name)
        variants.SetVariantSelection(self.shot_name)

        with variants.GetVariantEditContext():
            # Add step variants
            asset_define = UsdGeom.Xform.Define(self.stage, "/ROOT/asset")
            step_variants = asset_define.GetPrim().GetVariantSets().AddVariantSet("step")
            step_variants.AddVariant('ani')
            step_variants.SetVariantSelection('ani')

            # Add asset type prim
            with step_variants.GetVariantEditContext():
                for _asset_type in self.asset_usd_dict.keys():
                    UsdGeom.Xform.Define(self.stage, "/ROOT/asset/{}".format(_asset_type))
                    if _asset_type in self.asset_usd_dict.keys():
                        for _asset_name, _usd_path in self.asset_usd_dict[_asset_type].items():
                            _instance_path = "/ROOT/asset/{}/{}".format(_asset_type, _asset_name)
                            UsdGeom.Xform.Define(self.stage, _instance_path)

                            # Add usd reference
                            _prim = self.stage.GetPrimAtPath(_instance_path)
                            _prim.GetReferences().SetReferences([Sdf.Reference(_usd_path)])

        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)

    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # self.stage.GetRootLayer().ExportToString()
