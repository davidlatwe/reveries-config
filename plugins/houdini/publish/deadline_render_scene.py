
import contextlib
import pyblish.api


class DeadlineRenderScene(pyblish.api.ContextPlugin):
    """Save current scene with a new name for Deadline submission

    This action will change all render output path to published path,
    and save the scene with a new name for rendering in Deadline.

    """

    order = pyblish.api.ExtractorOrder + 0.29
    hosts = ["houdini"]
    label = "Deadline Render Scene"

    targets = ["deadline"]

    def process(self, context):
        import os
        import hou

        current = hou.hipFile.path()
        dir, file = os.path.split(current)
        deadline_scene = dir + "/_deadline/" + file

        with self.swap_output(context):
            hou.hipFile.save(file_name=deadline_scene,
                             save_to_recent_files=False)
        # save back
        hou.hipFile.save(file_name=current,
                         save_to_recent_files=False)

    @contextlib.contextmanager
    def swap_output(self, context):
        import os
        from reveries.houdini import lib

        origin = list()
        change = list()

        for instance in context:
            for repr_data in instance.data["packages"].values():
                ropnode = repr_data.get("swapRenderOutput")
                if ropnode is not None:
                    continue

                repr_dir = repr_data["representationDir"]

                output_parm = lib.get_output_parameter(ropnode)
                raw_output = output_parm.rawValue()
                pub_output = repr_dir + "/" + os.path.basename(raw_output)

                origin.append((output_parm, raw_output))
                change.append((output_parm, pub_output))

        try:
            for parm, value in change:
                parm.set(value)

            yield

        finally:
            for parm, value in origin:
                parm.set(value)
