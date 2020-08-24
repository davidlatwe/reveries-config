import json

from avalon import api


def export(usd_path, json_path, host="maya"):
    from reveries.common.usd.get_asset_info import GetAssetInfo

    asset_obj = GetAssetInfo(usd_file=usd_path)
    asset_info_data = asset_obj.asset_info

    asset_info_data["extra"] = {
        "host": host,
        "dept": api.Session["AVALON_TASK"],
        # "author": getpass.getuser()
    }

    with open(json_path, 'w') as f:
        json.dump(asset_info_data, f, ensure_ascii=False, indent=4)
