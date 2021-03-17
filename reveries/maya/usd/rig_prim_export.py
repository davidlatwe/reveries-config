from avalon import io

from reveries.maya import utils
from reveries.maya import lib, pipeline


class RigPrimValidation(object):
    def __init__(self):
        self.validation_result = True
        self.validation_log = []
        self.model_data = {}

    def get_invalid_group(self):
        _, invalid_group = utils.get_model_reference_group("Geometry")
        return invalid_group

    def get_model_subset_data(self):
        import maya.cmds as cmds

        model_group, _ = utils.get_model_reference_group("Geometry")

        for _group in model_group:
            children = cmds.listRelatives(
                _group, allDescendents=True, type="transform")

            for _child in reversed(children):
                if not _child.endswith("ROOT"):
                    continue

                ns = _child.split(":")[0]
                container = pipeline.get_container_from_namespace(ns)
                maya_long_path = cmds.ls(_child, long=True)[0]
                prim_path = maya_long_path.replace("{}:".format(ns), '')

                subset_id = cmds.getAttr("{}.subsetId".format(container))
                asset_id = cmds.getAttr("{}.assetId".format(container))
                version_id = cmds.getAttr("{}.versionId".format(container))

                _grp_short_name = cmds.ls(_group, long=False)[0]
                self.model_data.setdefault(
                    _grp_short_name, dict())["asset_id"] = \
                    self._check_id_exists(asset_id, _grp_short_name, "Asset")
                self.model_data[_grp_short_name]["subset_id"] = \
                    self._check_id_exists(subset_id, _grp_short_name, "Subset")
                self.model_data[_grp_short_name]["version_id"] = \
                    self._check_id_exists(version_id, _grp_short_name, "Version")

                self.model_data[_grp_short_name]["maya_long_path"] = maya_long_path
                self.model_data[_grp_short_name]["usd_prim_path"] = prim_path
                self.model_data[_grp_short_name]["asset_prim_file"] = \
                    self._get_asset_prim_file(_grp_short_name, asset_id)

                continue

        return self.model_data

    def _check_id_exists(self, _id, grp_name, id_type):
        _filter = {
            "_id": io.ObjectId(_id)
        }
        _data = io.find_one(_filter)
        if _data:
            return _id
        else:
            self._set_log("{}: {} not exist in publish.".format(grp_name, id_type))
            return None

    def _get_asset_prim_file(self, grp_name, asset_id):
        from reveries.common import get_publish_files

        _filter = {
            "type": "subset",
            "name": "assetPrim",
            "parent": io.ObjectId(asset_id)
        }
        asset_prim_data = io.find_one(_filter)
        if not asset_prim_data:
            self._set_log("{}: No assetPrim published.".format(grp_name))
            return None

        asset_prim_id = asset_prim_data["_id"]
        asset_prim_file = get_publish_files.get_files(
            asset_prim_id, key='entryFileName').get("USD", "")

        if not asset_prim_file:
            self._set_log("{}: Missing asset_prim.usd file.".format(grp_name))

        return asset_prim_file

    def _set_log(self, msg):
        self.validation_result = False
        self.validation_log.append(msg)


class RigPrimExporter(object):
    def __init__(self, output_path, asset_name=None, rig_subset_name=None, model_data=None):
        """
        Export rig usd file.

        :param output_path (str): Output path
        :param asset_name (str): Asset name. eg.MonsterSharkB
        :param rig_subset_name (str): Rig subset name. eg.rigDefault
        :param model_data (dict): Model data.
            Example:
            model_data={
                'MonsterSharkB_model_01_:modelDefault': {
                    'asset_id': u'5faa433292db633f34cbc8ab',
                    'asset_prim_file': u'/.../USD/asset_prim.usda',
                    'subset_id': u'5faa539092db6347b83feb78',
                    'usd_prim_path': u'|ROOT|Group|Geometry|modelDefault|ROOT',
                }
            }
        """
        validator = RigPrimValidation()

        self.model_data = model_data or validator.get_model_subset_data()
        self.output_path = output_path

        self.rig_subset_name = rig_subset_name
        self.asset_name = asset_name

        print("model_data: ", self.model_data)

    def _get_look_variant(self, model_subset_id):
        _filter = {
            "type": "subset",
            "data.families": "reveries.look",
            "data.model_subset_id": model_subset_id}
        lookdev_data = io.find_one(_filter)
        if lookdev_data:
            look_variant = lookdev_data["name"]
            return look_variant

        return None

    def _get_skeleton_usd_file(self):
        from reveries.common import get_publish_files

        _filter = {"type": "asset", "name": self.asset_name}
        asset_data = io.find_one(_filter)

        _filter = {
            "type": "subset",
            "name": "{}Skeleton".format(self.rig_subset_name),
            "parent": io.ObjectId(asset_data["_id"])
        }
        subset_data = io.find_one(_filter)
        if not subset_data:
            return None
        usd_file = get_publish_files.get_files(
            subset_data["_id"], key='entryFileName').get("USD", "")
        return usd_file

    def export(self):
        from pxr import Usd, Sdf, UsdGeom
        from reveries.common import get_fps
        from reveries.common.usd.utils import get_UpAxis

        stage = Usd.Stage.CreateInMemory()

        for _, _data in self.model_data.items():
            usd_prim_path = _data["usd_prim_path"].replace("|", "/")
            UsdGeom.Xform.Define(stage, usd_prim_path)
            prim = stage.GetPrimAtPath(usd_prim_path)

            asset_prim_file = _data["asset_prim_file"]
            look_variant = self._get_look_variant(_data["subset_id"])

            if asset_prim_file and look_variant:
                prim.GetReferences().SetReferences(
                    [Sdf.Reference(asset_prim_file)])

                try:
                    vs = prim.GetVariantSet("appearance")
                    vs.SetVariantSelection(look_variant)
                except Exception as e:
                    print("Set lookdev to {} failed. Error: {}".format(look_variant, e))

        # Add skeleton data usd
        skele_usd = self._get_skeleton_usd_file()
        root_layer = stage.GetRootLayer()
        root_layer.subLayerPaths.append(skele_usd)

        # Stage setting
        root_prim = stage.GetPrimAtPath('/ROOT')
        stage.SetDefaultPrim(root_prim)
        stage.SetFramesPerSecond(get_fps())
        stage.SetTimeCodesPerSecond(get_fps())
        UsdGeom.SetStageUpAxis(stage, get_UpAxis(host="Maya"))

        stage.GetRootLayer().Export(self.output_path)
        # print(stage.GetRootLayer().ExportToString())
