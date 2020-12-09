# -*- coding: utf-8 -*-
from avalon import io

from pxr import Usd, UsdGeom
from reveries.common import get_frame_range
from reveries.common import timing


class FinalUsdBuilder(object):
    @timing
    def __init__(self, shot_name='', frame_range=[]):
        self.stage = None
        self.usd_dict = {}
        self.shot_name = shot_name

        # Check frame range
        if frame_range:
            self.frame_in, self.frame_out = frame_range
        else:
            self.frame_in, self.frame_out = get_frame_range.get(self.shot_name)

        self._get_shot_data()
        self._build()

    def _get_shot_data(self):
        """
        Get shot data.
        usd_dict = {
            'lay': r'/.../publish/layPrim/v001/USD/lay_prim.usda',
            'ani': r'/.../publish/aniPrim/v012/USD/ani_prim.usda',
            'cam': r'/.../publish/camPrim/v001/USD/cam_prim.usda',
            'fx': r'/.../publish/aniPrim/v013/USD/fx_prim.usda',
        }
        """
        from reveries.common import get_publish_files

        self.usd_dict = {}

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)

        # Get camPrim/aniPrim/layPrim usd file
        for step_key in ["ani", "cam", "lay", "fx"]:
            _filter = {
                "type": "subset",
                "parent": shot_data['_id'],
                "name": "{}Prim".format(step_key)
            }
            prim_data = io.find_one(_filter)
            if prim_data:
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
        root_define = UsdGeom.Xform.Define(self.stage, "/ROOT")
        root_prim = self.stage.GetPrimAtPath("/ROOT")
        self.stage.GetRootLayer().documentation = \
            "Final usd for {}".format(self.shot_name)

        # Add shot variants
        step_variants = root_define.GetPrim().GetVariantSets().\
            AddVariantSet("step")

        with step_variants.GetVariantEditContext():
            # Set ani option
            self._set_step_variants("ani", step_variants, root_prim)

            # Set lay option
            self._set_step_variants("lay", step_variants, root_prim)

            # Set lay option
            self._set_step_variants("fx", step_variants, root_prim)

            # Set final option
            self._set_step_variants("final", step_variants, root_prim)

        # Add camera sublayer
        if "cam" in self.usd_dict.keys():
            root_layer = self.stage.GetRootLayer()
            root_layer.subLayerPaths.append(self.usd_dict["cam"])

        # Set default prim to ROOT
        root_prim = self.stage.GetPrimAtPath("/ROOT")
        self.stage.SetDefaultPrim(root_prim)

        print("Done")

    @timing
    def _set_step_variants(self, step_name, step_variants, root_prim):
        """
        Generate step variant option
        :param step_name: (str) Step name, ani/lay/fx/final
        :param step_variants: (obj)
        :param root_prim: (obj)
        :return:
        """
        # Set final option
        print("Running step: {}".format(step_name))
        step_variants.AddVariant(step_name)
        step_variants.SetVariantSelection(step_name)

        step_usd_key = ["fx", "ani", "lay"]
        usd_dict_key = list(self.usd_dict.keys())

        if step_name == "final":
            with step_variants.GetVariantEditContext():
                for step in step_usd_key:
                    if step in usd_dict_key:
                        root_prim.GetReferences().AddReference(
                            assetPath=self.usd_dict[step],
                            primPath="/ROOT"
                        )
        elif step_name in usd_dict_key:
            with step_variants.GetVariantEditContext():
                root_prim.GetReferences().AddReference(
                    assetPath=self.usd_dict[step_name],
                    primPath="/ROOT"
                )


    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # print(self.stage.GetRootLayer().ExportToString())
