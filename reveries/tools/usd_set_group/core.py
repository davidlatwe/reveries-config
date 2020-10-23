import sys
import ast
import json


class BuildSetGroupUSD(object):
    def __init__(self, set_data):
        """
        Build usd file for set group asset
        :param set_data: (dict) set asset name, subset asset name and geom.usda file data.
        set_data = {
            'status': False,
            'status_log': 'The subAssets are same with previous version.'
            'BillboardGroup': {
                'BillboardA': {
                    'asset_usd_file_path': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
                },
                'BillboardB': {
                    'asset_usd_file_path': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
                }
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
            UsdGeom.Xform.Define(self.stage, "/ROOT/Set/{}".format(set_name))
            for child_name, _info in child_data.items():
                if child_name in ['status', 'status_log']:
                    continue
                _child_path = "/ROOT/Set/{}/{}".format(set_name, child_name)
                UsdGeom.Xform.Define(self.stage, _child_path)

                # Add usd reference
                _prim = self.stage.GetPrimAtPath(_child_path)
                child_geom_usd = _info.get('asset_usd_file_path', '')

                if child_geom_usd:
                    _prim.GetReferences().SetReferences([Sdf.Reference(child_geom_usd)])

        root_prim = self.stage.GetPrimAtPath('/ROOT')
        self.stage.SetDefaultPrim(root_prim)

    def export(self, save_path):
        self.stage.GetRootLayer().Export(save_path)
        # print(self.stage.GetRootLayer().ExportToString())


class WriteSubAssetJson(object):
    def __init__(self, set_data, save_path):
        """
        Build usd file for set group asset
        :param set_data: (dict) set asset name, subset asset name and geom.usda file data.
        set_data = {
            'BillboardGroup': {
                'BillboardA': {
                    'asset_usd_file_path': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
                },
                'BillboardB': {
                    'asset_usd_file_path': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
                }
            }
        }
        """
        assert set_data, 'Please provide set name and usd file path.'

        self.set_data = set_data
        self.save_path = save_path

        self._write_json()

    def _write_json(self):
        dict_keys = list(self.set_data.keys())

        for del_key in ['status', 'status_log']:
            if del_key in dict_keys:
                del self.set_data[del_key]

        with open(self.save_path, 'w') as f:
            json.dump(self.set_data, f, ensure_ascii=False, indent=4)


def run():
    arg_dict = {}
    for arg_pair in sys.argv[1:]:
        [key, val] = arg_pair.split('=', 1)
        if key == 'set_data':
            val = ast.literal_eval(val)
        arg_dict[key] = val

    obj = BuildSetGroupUSD(arg_dict.get('set_data', {}))
    obj.export(arg_dict.get('usd_save_path', ''))
    print('1.USD')

    WriteSubAssetJson(arg_dict.get('set_data', {}),
                      arg_dict.get('json_save_path', ''))
    print('2.Json')


if __name__ == "__main__":
    run()
    print('Set USD Done')
