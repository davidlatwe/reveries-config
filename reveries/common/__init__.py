import sys
from avalon import io


def str_to_objectid(obj_id):
    if sys.version_info.major == 3:
        string_types = str,
    else:
        string_types = (str, unicode)

    if isinstance(obj_id, string_types):
        return io.ObjectId(obj_id)
    return obj_id


def skip_instance(context, family_name):
    """
    Skip process if instance exists.
    :param context: (obj) Instance context
    :param family_name: (str/list) F
    :return: bool
    """
    if not isinstance(family_name, list):
        family_name = [family_name]

    _exists = False
    for instance in context:
        if instance.data["family"] in family_name:
            _exists = True
            break
    return _exists


def asset_type_mapping(asset_type):

    patterns = ["chr", "char", "prp", "prop"]
    lower = asset_type.lower()
    if any(pattern in lower for pattern in patterns):
        return asset_type

    return False


def check_asset_type_from_ns(ns):
    # Get asset type casting
    asset_casting = {}
    if not asset_casting:
        _filter = {"type": "asset"}

        asset_datas = io.find(_filter)
        for asset_data in asset_datas:
            silo = asset_data.get('silo')
            if asset_type_mapping(silo):
                asset_type = asset_type_mapping(silo)
                asset_casting.setdefault(asset_type, list()).append(asset_data['name'])

    for asset_type in asset_casting.keys():
        for _as in asset_casting[asset_type]:
            if _as in ns:
                return asset_type


def timing(func):
    def wrapper(*arg, **kw):
        import time
        t1 = time.time()
        res = func(*arg, **kw)
        t2 = time.time()
        string = '| %s took %2.4f sec |' % (func.func_name, (t2-t1))
        print("\n{0}\n{1}\n{0}\n".format(
            '-' * len(string),
            string
        ))
        return res
    return wrapper
