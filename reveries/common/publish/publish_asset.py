from avalon import io

from avalon.tools.projectmanager import lib


def publish(asset_name, silo_name):
    data = {
        "name": asset_name,
        "label": asset_name,
        "silo": silo_name
    }

    _filter = {"type": "asset", "name": asset_name}
    if not io.find_one(_filter):
        lib.create_asset(data, True)
    else:
        print("Asset \"{}\" already published.".format(asset_name))
