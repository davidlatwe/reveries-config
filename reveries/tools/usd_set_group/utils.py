import os
import json
from avalon import io

from reveries.common.shotgun_io import ShotgunIO


def check_set_asset_exists(set_name):
    from reveries.common.publish import publish_asset

    _filter = {"type": "asset", "name": set_name}
    _set_data = io.find_one(_filter)
    if not _set_data:
        print('set {} not in db'.format(set_name))
        publish_asset.publish(set_name, 'Set')


class PublishSetGroup(object):
    def __init__(self):
        self.version_name = None
        self.reps_id = None

    def publish(self, asset_name, publish_files):
        from reveries.common.publish import publish_subset, \
            publish_version, \
            publish_representation

        # Get asset data
        asset_data = io.find_one({
            "type": "asset",
            "name": asset_name
        })

        # === Publish subset === #
        subset_name = 'assetPrim'
        families = ['reveries.look.asset_prim']
        subset_id = publish_subset.publish(asset_data['_id'], subset_name, families)

        # === Publish version === #
        version_id = publish_version.publish(subset_id)

        # === Publish representation === #
        name = 'USD'
        reps_data = {
            'entryFileName': 'asset_prim.usda',
            'subAssetJsonName': 'subAsset_data.json'
        }
        self.reps_id = publish_representation.publish(version_id, name, publish_files,
                                                      delete_source=True,
                                                      data=reps_data)
        if self.reps_id:
            self._get_version_name(version_id)
            print('{} publish done.\n'.format(asset_name))
            return True

        return False

    def _get_version_name(self, version_id):
        _filter = {
            'type': 'version',
            '_id': version_id
        }
        ver_data = io.find_one(_filter)
        self.version_name = ver_data.get('name', None)


class GetSetAssets(object):
    def __init__(self):
        self.asset_data = {}
        self.error_msg = ''

    def _check_tag(self, tag_context):
        if tag_context:
            for _context in tag_context:
                if _context.get('name', '').lower() in ['USD_SetGroup', 'usd_setgroup']:
                    return True
        return False

    def get_assets(self):
        """
        Get set asset list from shotgun.
        :return: asset_data
        asset_data = {
            'BillboardGroup': ['BillboardA', 'BillboardB']
        }
        """

        # For test
        # self.asset_data['BoxGroup_1'] = ['BoxB', 'BoxC', 'BoxD']
        # self.asset_data['BoxGroup_2'] = ['BoxA', 'BoxB']
        # self.asset_data['BoxGroup_3'] = ['BoxB', 'BoxC']
        # # self.asset_data['CanGroup'] = ['CanA', 'CanB', 'CanC', 'CanD']
        # return self.asset_data
        # For test end

        show_data = io.find_one({'type': 'project'}, projection={"name": True})
        shotgun_io = ShotgunIO(db_show_name=show_data['name'])

        # Check shotgun project exists
        if not shotgun_io.sg_project:
            self.error_msg = "Can't found \"{}\" in shotgun.\nPlease check with your PM.".format(show_data['name'])
            return False

        # Generate asset data
        asset_data_shotgun = shotgun_io.get_assets(
            fields=['tags', 'assets'],
            filters=[['sg_asset_type', 'is', 'Set']]
        )

        for _asset_info in asset_data_shotgun:
            if self._check_tag(_asset_info.get('tags', [])):
                set_name = _asset_info['code']
                sub_assets = [s['name'] for s in _asset_info.get('assets', [])]
                self.asset_data[set_name] = sub_assets

        return self.asset_data


class ValidateSetAsset(object):
    def __init__(self, set_data):
        self.validate_result = True
        self.set_data = set_data

    def _update_validate_data(self, status, log='', usd_file=''):
        _tmp_data = {
            'status': status,
            'status_log':  log,
            'asset_usd_file_path': usd_file
        }
        return _tmp_data

    def validate(self, progressbar_obj=None):
        from reveries.common import get_publish_files

        validate_data = {}
        i = 0
        if progressbar_obj:
            progressbar_obj.setBarRange(i, len(list(self.set_data.keys())))
            progressbar_obj.progressbar.setValue(i)

        for set_name, sub_assets in self.set_data.items():

            # Check set asset exists, if not exists will auto publish it
            check_set_asset_exists(set_name)
            validate_data[set_name] = {}

            # Check subAsset with previous version
            _filter = {"type": "asset", "name": set_name}
            _asset_data = io.find_one(_filter)

            _filter = {"type": "subset", "parent": _asset_data['_id'], 'name': 'assetPrim'}
            _subset_data = io.find_one(_filter)
            if _subset_data:
                json_file = get_publish_files.get_files(_subset_data['_id'], key='subAssetJsonName').get('USD', '')
                if json_file and os.path.exists(json_file):
                    with open(json_file) as json_file:
                        subAsset_data = json.load(json_file)

                    pub_children = list(subAsset_data[set_name].keys())
                    if pub_children.sort() == sub_assets.sort():
                        self.validate_result = False
                        validate_data[set_name]['status'] = False
                        validate_data[set_name]['status_log'] = 'SubAssets are same with previous version.'

            # Check sub asset already publish usd file
            for _child in sub_assets:
                validate_data[set_name][_child] = {}

                # Check subAsset exists
                _filter = {"type": "asset", "name": _child}
                _asset_data = io.find_one(_filter)

                if not _asset_data:
                    self.validate_result = False
                    validate_data[set_name][_child].update(self._update_validate_data(
                        False,
                        log='SubAsset not publish.'
                    ))
                    continue

                # Check model assetPrim subset published
                _filter = {"type": "subset", "parent": _asset_data['_id'], 'name': 'assetPrim'}
                _subset_data = io.find_one(_filter)

                if not _subset_data:
                    self.validate_result = False
                    validate_data[set_name][_child].update(self._update_validate_data(
                        False,
                        log='Model USD not publish.'
                    ))
                    continue

                # Check usd published
                asset_prim_usd_files = get_publish_files.get_files(_subset_data['_id']).get('USD', [])
                if not asset_prim_usd_files:
                    self.validate_result = False
                    validate_data[set_name][_child].update(self._update_validate_data(
                        False,
                        log="Can't found USD file in publish."
                    ))
                    continue

                # Update validate data
                validate_data[set_name][_child]['status'] = True
                validate_data[set_name][_child]['status_log'] = ''
                validate_data[set_name][_child]['asset_usd_file_path'] = asset_prim_usd_files[0]

            if progressbar_obj:
                i += 1
                progressbar_obj.progressbar.setValue(i)

        return validate_data
