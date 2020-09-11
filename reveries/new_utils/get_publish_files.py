import os
from avalon import io, api


def get_files(subset_id, version=None, key=None):
    """
    Get publish files from subset id.

    :param subset_id: (str) Subset id
    :param version: (int) Get publish file by version, default will get the latest version.
    :param key: (str) Get publish file from key value. eg. key='entryFileName'
    :return:
    """
    assert subset_id, "Please provide subset id."

    _filter = {"type": "subset", "_id": io.ObjectId(subset_id)}
    subset_data = io.find_one(_filter)

    # Get latest version
    _filter = {
        "type": "version",
        "parent": io.ObjectId(subset_id)
    }
    if version:
        _filter["name"] = int(version)
    version_data = io.find_one(_filter, sort=[("name", -1)])

    if not version_data:
        print('No version data found.')
        return {}

    # Get representation data
    _filter = {"type": "representation", "parent": io.ObjectId(version_data['_id'])}
    representation_data = io.find(_filter)

    # Get asset
    _filter = {"type": "asset", "_id": subset_data['parent']}
    asset_data = io.find_one(_filter)

    #
    project = io.find_one({"name": api.Session["AVALON_PROJECT"],
                           "type": "project"})
    publish_template = project["config"]["template"]["publish"]

    _pub_file = {}
    for _rep in representation_data:
        representation_name = _rep['name']

        _dir = publish_template.format(**{
            "root": api.registered_root(),
            "project": project["name"],
            "asset": asset_data["name"],
            "silo": asset_data["silo"],
            "subset": subset_data["name"],
            "version": version_data["name"],
            "representation": representation_name,
        })

        _pub_file[representation_name] = []

        if key:
            files_data = _rep.get('data', {}).get(key, '')
            if isinstance(files_data, (list)):
                for _path in files_data:
                    _pub_file[representation_name].append(os.path.join(_dir, _path).replace('\\', '/'))
            if isinstance(files_data, (str, unicode)):
                _pub_file[representation_name] = os.path.join(_dir, files_data).replace('\\', '/')

            return _pub_file

        files = os.listdir(_dir)
        if files:
            for _file in files:
                _file_path = os.path.join(_dir, _file).replace('\\', '/')
                _pub_file[representation_name].append(_file_path)
        else:
            print('No files found in publish dir: {}.'.format(_dir))
            # TODO: Texture publish files has different format, will add it later

    return _pub_file
