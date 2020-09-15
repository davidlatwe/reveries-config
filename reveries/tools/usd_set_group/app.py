import getpass

from avalon import io, api

from .utils import get_set_assets


def build():
    set_data = get_set_assets()
    if set_data:
        # Check set already in db:
        for set_name, chilren in set_data.items():
            print(set_name, chilren)
            _filter = {"type": "asset", "name": set_name}
            set_data = io.find_one(_filter)
            if not set_data:
                print('set {} not in db'.format(set_name))
    print('set_data: ', set_data)
    print('\n\n')

    #
    asset_name = 'BoxB'
    asset_data = io.find_one({
        "type": "asset",
        "name": asset_name
    })

    # Publish subset
    subset_name = 'setDefault'
    subset_context = {
        'name': subset_name,
        'parent': asset_data['_id'],
        'type': 'subset',
        'data': {
            'families': ['reveries.model'],
            'subsetGroup': ''
        },
        'schema': 'avalon-core:subset-3.0'}
    print('subset_context: ', subset_context)

    _filter = {"parent": asset_data['_id'], "name": subset_name}
    subset_data = io.find_one(_filter)
    if subset_data is None:
        subset_id = io.insert_one(subset_context).inserted_id
    else:
        subset_id = subset_data['_id']

    # Publish version
    version_context = {
        'name': 2,
        'parent': subset_id,
        'type': 'version',
        'locations': ['http://127.0.0.1'],
        'data': {
            'comment': 'pp',
            'source': r'{root}/199909_AvalonPlay/Avalon/PropBox/BoxB/work/modeling/maya/scenes/_published/modeling_v0007.published.mb',
            'task': 'modeling',
            'workDir': r'{root}/199909_AvalonPlay/Avalon/PropBox/BoxB/work/modeling/maya',
            'author': getpass.getuser(),
            'time': api.time(),
            'dependencies': {},
            'dependents': {}
        },
        'schema': 'avalon-core:version-3.0'
    }
    version_id = io.insert_one(version_context).inserted_id
    print('version id: ', version_id)

    # Publish representation
    representations_context = {
        'data': {
            'entryFileName': 'geom.usda'
        },
        'type': 'representation',
        'name': 'USD',
        'parent': version_id,
        'schema': 'avalon-core:representation-2.0'
    }
    reps_id = io.insert_one(representations_context).inserted_id
    print('reps_id :', reps_id)


def cli():
    print('\n\nStart running usd set group')

    io.install()
    build()
    print('\n\nDone')
