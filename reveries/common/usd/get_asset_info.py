from pxr import Usd, Sdf, UsdGeom
from reveries.common.path_resolver import PathResolver


class GetAssetInfo(object):
    def __init__(self, usd_file=None):
        """
        Get asset information from usd file.
        :param usd_file: (str) USD file path.
        asset_info = {
            'PropBox': {
                'BoxB': {
                    'usd_file_path': '.../PropBox/BoxB/publish/assetPrim/v002/USD/asset_prim.usda'},
                'BoxC': {
                    'usd_file_path': '.../PropBox/BoxC/publish/assetPrim/v001/USD/asset_prim.usda'}
            },
            'Set': {
                'PollutedSea': {
                    'usd_file_path': '.../Set/PollutedSea/publish/assetPrim/v001/USD/asset_prim.usda'}
            },
            'Shot': {
                'layerBillboardA': {
                    'step': u'Layout',
                    'step_type': u'usd_layer',
                    'usd_file_path': '.../Shot/SEQ01_SEQ01_Sh0100/publish/layerBillboardA/v001/USD/layerBillboardA_prim.usda'}
            }
        }
        """
        self.usd_file = usd_file
        self.asset_info = {}
        self._get_data()

    def _get_data(self):
        # source_stage = None
        # root_layer = None

        source_stage = Usd.Stage.Open(self.usd_file)
        root_layer = source_stage.GetRootLayer()
        layers = [s.replace('\\', '/') for s in root_layer.GetExternalReferences() if s]

        print ('layers: ', layers)

        resolver_obj = PathResolver()
        for _path in layers:
            resolver_obj.analysis_path(file_path=_path)
            silo_name = resolver_obj.get_silo_name()
            if silo_name in ['Shot']:
                subset_name = resolver_obj.get_subset_name()
                resolver_obj.get_subset_id()

                _tmp = {
                    subset_name: {
                        'step': resolver_obj.subset_data.get('data', {}).get('subsetGroup'),
                        'usd_file_path': _path,
                        'step_type': resolver_obj.subset_data.get('step_type')
                    }
                }
                self.asset_info.setdefault(silo_name, dict()).update(_tmp)
            else:
                asset_name = resolver_obj.get_asset_name()
                _tmp = {
                    asset_name: {
                        'usd_file_path': _path
                    }
                }
                self.asset_info.setdefault(silo_name, dict()).update(_tmp)


def test():
    tmp_usd = r'Q:\199909_AvalonPlay\Avalon\Shot\SEQ01_SEQ01_Sh0100\work\layout\houdini\scenes\test\lay_prim_v03.usda'
    asset_obj = GetAssetInfo(usd_file=tmp_usd)
    asset_obj.asset_info
