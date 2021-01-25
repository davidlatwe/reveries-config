from avalon import io


class FxPrimExport(object):
    def __init__(self, output_path, shot_name):
        self.output_path = output_path
        self.shot_name = shot_name

        self._export()

    def _get_fx_layer_usd(self):
        from reveries.common import get_publish_files, path_resolver

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)
        shot_id = shot_data['_id']

        # Get setdress layer usd file
        _filter = {
            "type": "subset",
            "parent": shot_id,
            "data.families": "reveries.fx.layer_prim"
        }
        fx_data = [s for s in io.find(_filter)]

        fx_usd_files = {}
        if fx_data:
            for _data in fx_data:
                _file = get_publish_files.get_files(
                    _data["_id"],
                    key="entryFileName").get("USD", "")
                if _file:
                    resolver_obj = path_resolver.PathResolver(file_path=_file)
                    subset_name = resolver_obj.subset_name
                    version_data = resolver_obj.get_version_data()
                    usd_type = version_data.get("data", {}).get("usd_type", "")

                    fx_usd_files[subset_name] = {
                        "usd_type": usd_type,
                        "file": _file
                    }

        return fx_usd_files

    def _export(self):
        from pxr import Usd, UsdGeom

        fx_usd_files = self._get_fx_layer_usd()

        # Generate usd file
        stage = Usd.Stage.CreateInMemory()
        root_layer = stage.GetRootLayer()

        UsdGeom.Xform.Define(stage, "/ROOT")
        root_prim = stage.GetPrimAtPath('/ROOT')
        stage.SetDefaultPrim(root_prim)

        for _subset_name, _data in fx_usd_files.items():
            # Create sublayer
            if _data["usd_type"] == "Sublayer":
                root_layer.subLayerPaths.append(_data["file"])

            # Create reference
            elif _data["usd_type"] == "Reference":
                prim_path = "/ROOT/Fx/{}".format(_subset_name)
                UsdGeom.Xform.Define(stage, prim_path)
                _prim = stage.GetPrimAtPath(prim_path)
                _prim.GetReferences().AddReference(
                    assetPath=_data["file"],
                    primPath="/ROOT"
                )
            else:
                print("{}: Can't found usd type in publish data. "
                      "Skip it.".format(_subset_name))

        stage.GetRootLayer().Export(self.output_path)
        # print(stage.GetRootLayer().ExportToString())

    @classmethod
    def export(cls, output_path, shot_name):
        cls(output_path, shot_name)
