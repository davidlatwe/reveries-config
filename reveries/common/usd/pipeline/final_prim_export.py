# -*- coding: utf-8 -*-

from avalon import io

from pxr import Usd, UsdGeom
from reveries import common as utils


class FinalUsdBuilder(object):
    def __init__(self, shot_name='', frame_in=None, frame_out=None):
        self.stage = None
        self.frame_in = frame_in
        self.frame_out = frame_out
        self.shot_name = shot_name
        self.usd_dict = {}

        self._get_shot_data()
        self._build()

    def _get_shot_data(self):
        """
        Get shot data.
        usd_dict = {
            'lay': r'/.../publish/layPrim/v001/USD/lay_prim.usda',
            'ani': r'/.../publish/aniPrim/v012/USD/ani_prim.usda',
            'cam': r'/.../publish/camPrim/v001/USD/cam_prim.usda'
        }
        """
        from reveries.common import get_publish_files

        if not self.frame_in or not self.frame_out:
            self.frame_in, self.frame_out = utils.get_frame_range(
                self.shot_name)

        self.usd_dict = {}

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)

        # Get camPrim/aniPrim/layPrim usd file
        for step_key in ["ani", "cam", "lay"]:
            _filter = {
                "type": "subset",
                "parent": shot_data['_id'],
                "name": "{}Prim".format(step_key)
            }
            prim_data = io.find_one(_filter)
            self.usd_dict[step_key] = get_publish_files.get_files(
                prim_data["_id"],
                key="entryFileName").get("USD", "")

        from pprint import pprint
        pprint(self.usd_dict)

    def _build(self):
        self.stage = Usd.Stage.CreateInMemory()
        self.stage.SetStartTimeCode(self.frame_in)
        self.stage.SetEndTimeCode(self.frame_out)

        # Create shot prim
        shot_define = UsdGeom.Xform.Define(self.stage, "/ROOT")
        self.stage.GetRootLayer().documentation = \
            "Final usd for {}".format(self.shot_name)

        # Add shot variants
        variants = shot_define.GetPrim().GetVariantSets().AddVariantSet("shot")
        variants.AddVariant(self.shot_name)
        variants.SetVariantSelection(self.shot_name)

        with variants.GetVariantEditContext():
            # Add step variants
            asset_define = UsdGeom.Xform.Define(self.stage, "/ROOT/Asset")
            asset_prim = self.stage.GetPrimAtPath("/ROOT/Asset")
            step_variants = asset_define.GetPrim().\
                GetVariantSets().AddVariantSet("step")

            # Set ani option
            self._set_step_variants("ani", step_variants, asset_prim)

            # Set lay option
            self._set_step_variants("lay", step_variants, asset_prim)

            # Set final option
            self._set_step_variants("final", step_variants, asset_prim)

        # Add camera sublayer
        root_layer = self.stage.GetRootLayer()
        root_layer.subLayerPaths.append(self.usd_dict['cam'])

        # Set default prim to ROOT
        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)

    def _set_step_variants(self, step_name, step_variants, asset_prim):
        """
        Generate step variant option
        :param step_name: (str) Step name, ani/lay/final
        :param step_variants: (obj)
        :param asset_prim: (obj)
        :return:
        """
        # Set final option
        step_variants.AddVariant(step_name)
        step_variants.SetVariantSelection(step_name)

        if step_name == "final":
            step_usd_key = ["ani", "lay"]
        else:
            step_usd_key = [step_name]

        for _key in step_usd_key:
            with step_variants.GetVariantEditContext():
                asset_prim.GetReferences().AddReference(
                    assetPath=self.usd_dict[_key],
                    primPath="/ROOT/Asset"
                )

    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # print self.stage.GetRootLayer().ExportToString()
