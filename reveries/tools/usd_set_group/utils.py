from avalon import io
from reveries.common.shotgun_io import ShotgunIO


def get_set_assets():
    show_data = io.find_one({'type': 'project'}, projection={"name": True})
    shotgun_io = ShotgunIO(db_show_name=show_data['name'])

    # Check shotgun project exists
    if not shotgun_io.sg_project:
        return False, ''

    asset_data = {
        'BillboardGroup': ['BillboardA', 'BillboardB']
    }
    # _filter = {"type": "asset"}
    # set_data = io.find_one(_filter)
    # print('set_data: ', set_data)

    return True, asset_data
