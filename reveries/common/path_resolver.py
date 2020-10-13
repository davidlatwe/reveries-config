import os
from avalon import io, api

import get_publish_files


class PathResolver(object):
    def __init__(self, file_path=None):
        self.is_publish = False
        self.silo_name = ''
        self.asset_name = ''
        self.subset_name = ''
        self.representation_name = ''

        self.asset_id = ''
        self.subset_id = ''
        self.subset_data = {}
        self.latest_version_name = ''

        if file_path:
            self.file_path = file_path.replace('\\', '/')
            self.analysis_path()

    def analysis_path(self, file_path=None):
        if file_path:
            self.file_path = file_path.replace('\\', '/')

        project = io.find_one({"name": api.Session["AVALON_PROJECT"],
                               "type": "project"})
        publish_template_path = project["config"]["template"]["publish"]

        project_template_path = r'{root}/{project}/Avalon/'
        project_root = project_template_path.format(**{
            "root": api.registered_root(),
            "project": project["name"]
        })
        # print('project_root: ', project_root)

        # Get silo name
        _silo_tmp = self.file_path.split(project_root)
        if not len(_silo_tmp) == 2:
            return

        self.silo_name = _silo_tmp[1].split('/')[0]
        self.asset_name = _silo_tmp[1].split('/')[1]

        if _silo_tmp[1].split('/')[2] == 'publish':
            self.is_publish = True

        if self.is_publish:
            self.subset_name = _silo_tmp[1].split('/')[3]
            self.current_version_name = _silo_tmp[1].split('/')[4]
            self.representation_name = _silo_tmp[1].split('/')[5]

            # pub_dir = publish_template_path.format(**{
            #     "root": api.registered_root(),
            #     "project": project["name"],
            #     "silo": self.silo_name,
            #     "asset": self.asset_name,
            #     "subset": self.subset_name,
            #     "version": self.current_version_name,
            #     "representation": self.representation_name,
            # })

        # print('_silo_name: ', self.silo_name)

    def is_publish_file(self):
        return self.is_publish

    def _get_asset_id(self):
        _filter = {"type": "asset",
                   "name": self.asset_name}
        asset_data = io.find_one(_filter)
        self.asset_id = asset_data["_id"]

    def get_subset_id(self):
        if not self.asset_id:
            self._get_asset_id()

        _filter = {"type": "subset",
                   "name": self.subset_name,
                   "parent": io.ObjectId(self.asset_id)}
        self.subset_data = io.find_one(_filter)
        self.subset_id = self.subset_data["_id"]
        return self.subset_id

    def _get_version_id(self):
        if not self.subset_id:
            self.get_subset_id()

        _filter = {
            "type": "version",
            "parent": self.subset_id
        }
        version_data = io.find_one(_filter, sort=[("name", -1)])
        self.latest_version_name = "v{:03}".format(version_data["name"])

        return version_data

    def is_latest_version(self):
        self._get_version_id()

        if self.latest_version_name == self.current_version_name:
            return True

        return False

    def get_latest_version_name(self):
        if not self.latest_version_name:
            self._get_version_id()

        return self.latest_version_name

    def get_latest_file(self):
        if not self.subset_id:
            self.get_subset_id()

        publish_files = get_publish_files.get_files(self.subset_id)
        if self.representation_name in list(publish_files.keys()):
            publish_files = publish_files.get(self.representation_name)
            if len(publish_files) == 1:
                publish_files = publish_files[0]

        return publish_files

    def get_silo_name(self):
        return self.silo_name

    def get_asset_name(self):
        return self.asset_name

    def get_subset_name(self):
        if self.is_publish:
            return self.subset_name
        else:
            print("File path isn't from publish.")
            return False

    def get_current_version_name(self):
        if self.is_publish:
            return self.current_version_name
        else:
            print("File path isn't from publish.")
            return False

    def get_representation_name(self):
        if self.is_publish:
            return self.representation_name
        else:
            print("File path isn't from publish.")
            return False


if __name__ == "__main__":
    file_path = r'Q:/199909_AvalonPlay/Avalon/PropBox/BoxB/publish/assetPrim/v006/USD/asset_prim.usda'
    resolver = PathResolver(file_path=file_path)
