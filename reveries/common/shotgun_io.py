import sys
sys.path.append(r'Q:\Resource\python_modules')

# set PATH=C:\Python27\;C:\Python27\Scripts\;%PATH%
# sys.path.insert(0, r'C:\Python27')
# sys.path.insert(0, r'C:\Python27\Scripts')

# from pprint import pprint

import shotgun_api3


class ShotgunIO(object):
    def __init__(self, server='https://moonshine.shotgunstudio.com/', login='artist', password='Artist1234',
                 sg_show_name=None, db_show_name=None):
        self.sg_project = None

        if not sg_show_name and not db_show_name:
            return

        self.shotgun = shotgun_api3.Shotgun(server, login=login, password=password)

        if sg_show_name:
            self._get_current_project(sg_show_name)
        else:
            self._get_shotgun_show_name_from_db(db_show_name)

    def _get_shotgun_show_name_from_db(self, db_show_name):
        fields = ['cached_display_name', 'tank_name']
        filters = [
            ['tank_name', 'is', db_show_name]
        ]

        self.sg_project = self.shotgun.find_one('Project', filters, fields)

    def _get_current_project(self, sg_show_name):
        self.sg_project = self.shotgun.find_one('Project', [['name', 'is', sg_show_name]])

    def get_assets(self, fields=[], filters=[]):
        fields += ['id', 'code', 'name', 'sg_asset_type']  # , 'tags'
        filters += [
            ['project', 'is', self.sg_project],
            # ['sg_asset_type', 'is', 'Set'],
            # ['code', 'is', 'BillboardGroup'],
        ]

        assets = self.shotgun.find('Asset', filters, fields)
        return assets


def test():
    from pprint import pprint

    server = 'https://moonshine.shotgunstudio.com/'
    login = 'artist'
    password = 'Artist1234'
    shotgun_show_name = 'ChimelongPreshow'
    db_show_name = r'201912_ChimelongPreshow'

    shotgun = shotgun_api3.Shotgun(server, login=login, password=password)

    # Get project
    fields = []
    for i in shotgun.schema_field_read('Project'):
        fields.append(i)

    fields = ['cached_display_name', 'tank_name']
    filters = [
        ['tank_name', 'is', db_show_name]
    ]

    sg_project = shotgun.find_one('Project', filters, fields)
    pprint(sg_project)

    # Get all fields
    # fields = []
    # for i in shotgun.schema_field_read('Asset'):
    #     fields.append(i)
    #
    # fields = ['id', 'code', 'name', 'sg_asset_type', 'tags', 'assets']
    # filters = [
    #     ['project', 'is', sg_project],
    #     ['sg_asset_type', 'is', 'Set'],
    #     # ['code', 'is', 'BillboardGroup'],
    # ]
    # assets = shotgun.find('Asset', filters, fields)
    # pprint(assets)

    # End
    print('Done')


# test()

# from avalon import io

# show_name = 'ChimelongPreshow'
# db_show_name = r'201912_ChimelongPreshow'
# shotgun_io = ShotgunIO(sg_show_name=show_name)

# set_asset = shotgun_io.get_assets(fields=['tags', 'assets'], filters=[['sg_asset_type', 'is', 'Set']])
# pprint(set_asset)

#

# set_asset = shotgun_io.get_assets(fields=['tags', 'assets'], filters=[['sg_asset_type', 'is', 'Set']])
# pprint(set_asset)
