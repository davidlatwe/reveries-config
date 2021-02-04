import os
import sys
import traceback


class EditFxPrimitive(object):
    def __init__(self, shot_name, tmp_dir):

        self.shot_name = shot_name
        self.tmp_dir = tmp_dir

        self._export()

    def _export(self):
        from avalon import io
        from reveries.common.usd.pipeline import fx_prim_export

        io.install()
        print("Project: ", os.environ["AVALON_PROJECT"])

        print("Publish Fx Primitive ... ...")

        usd_path = os.path.join(self.tmp_dir, "fx_prim.usda")
        try:
            fx_prim_export.FxPrimExport.export(usd_path, self.shot_name)
        except Exception as e:
            trace_error = traceback.format_exc()
            print("Function error: {}\n {}".format(e, trace_error))

        print('Publish Fx Primitive Done.')


def run():
    arg_dict = {}
    for arg_pair in sys.argv[1:]:
        [key, val] = arg_pair.split('=', 1)
        arg_dict[key] = val
    try:
        EditFxPrimitive(
            arg_dict['shot_name'],
            arg_dict['tmp_dir']
        )
    except Exception as e:
        trace_error = traceback.format_exc()
        print("Republish error: {}\n {}".format(e, trace_error))


if __name__ == "__main__":
    run()
