import os

from pxr import Usd, Sdf, UsdGeom
from avalon import io


class ParentPointcacheExporter(object):
    def __init__(self, shot_name, parent_subset_name, frame_range=[]):
        from reveries.common import get_frame_range

        self.output_path = ""
        self.children_data = []
        self.shot_name = shot_name
        self.parent_subset_name = parent_subset_name

        # Check frame range
        if frame_range:
            self.frame_in, self.frame_out = frame_range
        else:
            self.frame_in, self.frame_out = get_frame_range.get(self.shot_name)

    def _get_shot_id(self):
        _filter = {"type": "asset", "name": self.shot_name}
        self.shot_data = io.find_one(_filter)

    def get_children_data(self):
        self._get_shot_id()

        _filter = {
            "type": "subset",
            "data.families": "reveries.pointcache.child.usd",
            "parent": self.shot_data["_id"],
            "data.parent_pointcache_name": self.parent_subset_name
        }
        self.children_data = [s for s in io.find(_filter)]
        return self.children_data

    def export(self, output_dir):
        from reveries.common import get_publish_files, get_fps
        from reveries.common.usd.utils import get_UpAxis

        if not self.children_data:
            self.get_children_data()

        stage = Usd.Stage.CreateInMemory()

        UsdGeom.Xform.Define(stage, "/ROOT")
        root_prim = stage.GetPrimAtPath('/ROOT')

        # Set parent prim
        parent_prim_name = "/ROOT/main"
        UsdGeom.Xform.Define(stage, parent_prim_name)
        main_prim = stage.GetPrimAtPath(parent_prim_name)
        main_prim.GetReferences().SetReferences(
            [Sdf.Reference("parent_pointcache_prim.usda")]
        )

        for child_data in self.children_data:
            prim_name = "/ROOT/{}".format(child_data["name"].split(".")[-1])
            UsdGeom.Xform.Define(stage, prim_name)
            _prim = stage.GetPrimAtPath(prim_name)

            _file = get_publish_files.get_files(
                child_data["_id"], key="entryFileName").get('USD', "")

            if _file:
                _prim.GetReferences().SetReferences([Sdf.Reference(_file)])

        # Set metadata
        stage.SetDefaultPrim(root_prim)
        stage.SetStartTimeCode(self.frame_in)
        stage.SetEndTimeCode(self.frame_out)

        stage.SetFramesPerSecond(get_fps())
        stage.SetTimeCodesPerSecond(get_fps())
        UsdGeom.SetStageUpAxis(stage, get_UpAxis(host="Maya"))

        self.output_path = os.path.join(
            output_dir, "pointcache_prim_tmp.usda").replace('\\', '/')

        stage.GetRootLayer().Export(self.output_path)
        # print stage.GetRootLayer().ExportToString()

        print("Parent usd done: {}".format(self.output_path))
