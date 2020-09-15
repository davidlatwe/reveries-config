import sys
sys.path.append(r'Q:\Resource\python_modules')

import shotgun_api3


class ShotgunIO(object):
    """

    [Shotgun query]

        # You can going to bfx_layout.tools.shot_splitter.shotgun ShotgunIO get more help

        #   Get shotgun object
        from bfx.pipeline.taskstarter.models import get_entity_from_environ
        ple_entity = get_entity_from_environ()
        sg_task = ple_entity.shotgun_model
        with shotgun_api(SCRIPT_PLE):
            sg_version = sg_task.module_context.Version()
            shotgun = sg_version._get_current_connection()
        # --------------------------------------
        pprint.pprint(shotgun.schema_field_read('Project').keys())
        get all keys about Project

        # --------------------------------------
        # Find Project by name
        # --------------------------------------
        result = shotgun.find('Project', [['name', 'is', 'WHD']])

        #   result
        [{u'type': u'Project', u'id': 68}]


        # --------------------------------------
        # Find assets in a Shot
        # --------------------------------------
        filters = [['project', 'is', sg_project],
                    ['code', 'is', 'zzz01']]
        fields = ['assets']
        result = shotgun.find('Shot', filters, fields)

        #   result
        [{u'type': u'Shot', u'id': 1197, u'assets': [{u'type': u'Asset', u'id': 829, u'name': u'dinapartment'}]}]



    [ShotgunIO]
        #   Get shotgunio object
        shotgunio = ShotgunIO()

        # --------------------------------------
        # Find current project
        # --------------------------------------
        result = shotgunio._get_current_project()

        #   result
        [{u'type': u'Project', u'id': 68}]


        # --------------------------------------
        # Find assets in a Shot
        # --------------------------------------
        result = shotgunio.get_shot_asset_names(shot_name='zzz01')

        #   result
        [u'dinapartment']

    """
    def __init__(self, server='https://moonshine.shotgunstudio.com/', login='artist', password='Artist1234',
                 show_name=None):
        if not show_name:
            return

        self.sg_project = None

        self.shotgun = shotgun_api3.Shotgun(server, login=login, password=password)

        self.show_name = show_name
        self._get_current_project()

    def _get_current_project(self):
        self.sg_project = self.shotgun.find_one('Project', [['name', 'is', self.show_name]])

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
    show_name = 'ChimelongPreshow'

    shotgun = shotgun_api3.Shotgun(server, login=login, password=password)

    # fields = ['id', 'name']
    # projs = shotgun.find('Project', [], fields)
    # print projs

    sg_project = shotgun.find_one('Project', [['name', 'is', show_name]])

    # Get all fields
    fields = []
    for i in shotgun.schema_field_read('Asset'):
        fields.append(i)

    fields = ['id', 'code', 'name', 'sg_asset_type', 'tags']
    filters = [
        ['project', 'is', sg_project],
        ['sg_asset_type', 'is', 'Set'],
        # ['code', 'is', 'BillboardGroup'],
        # ['tags', 'is', {'name': 'USD_SetGroup', 'type': 'Tag'}],
    ]

    assets = shotgun.find('Asset', filters, fields)

    pprint(assets)

    print 'Done'


# test()

from pprint import pprint
show_name = 'ChimelongPreshow'
shotgun_io = ShotgunIO(show_name=show_name)

set_asset = shotgun_io.get_assets(fields=['tags'], filters=[['sg_asset_type', 'is', 'Set']])
pprint(set_asset)
