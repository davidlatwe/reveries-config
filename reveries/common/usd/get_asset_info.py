from pxr import Usd
from reveries.common import path_resolver


class GetAssetInfo(object):
    def __init__(self, usd_file=None):
        """
        Get asset information from usd file.
        :param usd_file: (str) USD file path.
        asset_info = {
            'PropBox': {
                'BoxB': {
                    'usd_file_path': '/.../v002/USD/asset_prim.usda'},
                'BoxC': {
                    'usd_file_path': '/.../v001/USD/asset_prim.usda'}
            },
            'Set': {
                'PollutedSea': {
                    'usd_file_path': '/.../v001/USD/asset_prim.usda'}
            },
            'Shot': {
                'layerBillboardA': {
                    'step': u'Layout',
                    'step_type': u'usd_layer',
                    'usd_file_path': '/.../v001/USD/layerBillboardA_prim.usda'}
            }
        }
        """
        self.usd_file = usd_file
        self.asset_info = {}
        self._get_data()

    def _get_data(self):
        source_stage = Usd.Stage.Open(self.usd_file)
        root_layer = source_stage.GetRootLayer()
        layers = [s.replace('\\', '/')
                  for s in root_layer.GetExternalReferences() if s]

        resolver_obj = path_resolver.PathResolver()
        for _path in layers:
            resolver_obj.analysis_path(file_path=_path)
            silo_name = resolver_obj.get_silo_name()
            if silo_name in ['Shot']:
                subset_name = resolver_obj.get_subset_name()
                subset_id = str(resolver_obj.get_subset_id())
                subset_data = resolver_obj.subset_data
                version_id = str(resolver_obj.get_version_id())
                representation_id = str(resolver_obj.get_representation_id())
                version_name = resolver_obj.current_version_name  # v002

                _tmp = {
                    subset_name: {
                        'version_name': version_name,
                        'subset_id': subset_id,
                        'version_id': version_id,
                        'representation_id': representation_id,
                        'type': 'subset',
                        'step': subset_data.get('data', {}).get(
                            'subsetGroup', ''),
                        'usd_file_path': _path,
                        'families': subset_data.get('data', {}).get(
                            'families', []),
                        # 'step_type': subset_data.get('step_type', '')
                    }
                }
                self.asset_info.setdefault(silo_name, dict()).update(_tmp)
            else:
                asset_name = resolver_obj.get_asset_name()
                asset_id = str(resolver_obj.get_asset_id())
                _tmp = {
                    asset_name: {
                        'asset_id': asset_id,
                        'type': 'asset',
                        'usd_file_path': _path
                    }
                }
                self.asset_info.setdefault(silo_name, dict()).update(_tmp)


def test():
    tmp_usd = r'\...\houdini\scenes\test\lay_prim_v03.usda'
    GetAssetInfo(usd_file=tmp_usd)
