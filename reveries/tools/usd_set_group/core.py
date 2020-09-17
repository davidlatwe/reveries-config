import sys
import ast


class BuildSetGroupUSD(object):
    def __init__(self, set_data):
        """
        Build usd file for set group asset
        :param set_data: (dict) set asset name, subset asset name and geom.usda file data.
            {
                'BillboardGroup': {
                    'BillboardA': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda',
                    'BillboardB': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
                }
            }
        """
        assert set_data, 'Please provide set name and usd file path.'

        self.set_data = set_data

        self._build()

    def _build(self):
        from pxr import Usd, Sdf, UsdGeom

        self.stage = Usd.Stage.CreateInMemory()

        # Create shot prim
        UsdGeom.Xform.Define(self.stage, "/ROOT")
        self.stage.GetRootLayer().documentation = "Set group"
        # UsdGeom.Xform.Define(self.stage, "/ROOT/asset")
        # UsdGeom.Xform.Define(self.stage, "/ROOT/asset/Set")

        for set_name, child_data in self.set_data.items():
            UsdGeom.Xform.Define(self.stage, "/ROOT/asset/Set/{}".format(set_name))
            for child_name, child_geom_usd in child_data.items():
                _child_path = "/ROOT/asset/Set/{}/{}".format(set_name, child_name)
                UsdGeom.Xform.Define(self.stage, _child_path)

                # Add usd reference
                _prim = self.stage.GetPrimAtPath(_child_path)

                # child_geom_usd = self._get_geom_usd(child_name)
                if child_geom_usd:
                    _prim.GetReferences().SetReferences([Sdf.Reference(child_geom_usd)])

        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)

    # def _get_geom_usd(self, asset_name):
    #     from avalon import io, api
    #     from reveries.common import get_publish_files
    #
    #     # Get asset id
    #     _filter = {"type": "asset", "name": asset_name}
    #     asset_data = io.find_one(_filter)
    #     asset_id = asset_data['_id']
    #
    #     # Get asset prim usd file
    #     _filter = {"type": "subset", "name": "assetPrim", "parent": asset_id}
    #     assetprim_data = io.find_one(_filter)
    #     if not assetprim_data:
    #         # self.log.warning('No asset prim publish file found.')
    #         return False
    #
    #     geom_usd = get_publish_files.get_files(assetprim_data['_id']).get('USD', [])
    #
    #     return geom_usd[0] if geom_usd else False

    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # print(self.stage.GetRootLayer().ExportToString())


def run():
    arg_dict = {}
    for arg_pair in sys.argv[1:]:
        [key, val] = arg_pair.split('=', 1)
        if key == 'set_data':
            val = ast.literal_eval(val)
        arg_dict[key] = val
        print(key, type(val), val)

    obj = BuildSetGroupUSD(arg_dict.get('set_data', {}))
    obj.export(arg_dict.get('save_path', {}))


if __name__ == "__main__":
    run()
    print('Set USD Done')
