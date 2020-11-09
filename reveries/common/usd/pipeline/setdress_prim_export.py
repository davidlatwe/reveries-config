from avalon import io


class SetDressPrimExport(object):
    def __init__(self, output_path, shot_name):
        self.output_path = output_path
        self.shot_name = shot_name

        self._export()

    def _get_setdress_layer_usd(self):
        from reveries.common import get_publish_files

        # Get shot id
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)
        shot_id = shot_data['_id']

        # Get setdress layer usd file
        _filter = {
            "type": "subset",
            "parent": shot_id,
            "data.families": "reveries.setdress.layer_prim"
        }
        setdress_datas = [s for s in io.find(_filter)]

        setdress_usd_files = []
        if setdress_datas:
            for _setdress_data in setdress_datas:
                publish_files = get_publish_files.get_files(_setdress_data['_id'])
                setdress_usd_files += publish_files.get('USD', [])

        return setdress_usd_files

    def _export(self):
        from pxr import Usd, UsdGeom

        setdress_usd_files = self._get_setdress_layer_usd()

        # Generate usd file
        stage = Usd.Stage.CreateInMemory()

        root_layer = stage.GetRootLayer()
        for _file in setdress_usd_files:
            root_layer.subLayerPaths.append(_file)

        UsdGeom.Xform.Define(stage, "/ROOT")
        root_prim = stage.GetPrimAtPath('/ROOT')
        stage.SetDefaultPrim(root_prim)

        stage.GetRootLayer().Export(self.output_path)
        # print(stage.GetRootLayer().ExportToString())

    @classmethod
    def export(cls, output_path, shot_name):
        cls(output_path, shot_name)
