
import os
import sys
import logging
import json
import pyblish.api
import pyblish.lib


def get_plugin(classname):
    # Find extractor plugin
    Plugin = None
    for P in pyblish.api.discover():
        if P.__name__ == classname:
            print("Found Plugin: ", P)
            Plugin = P
            break

    assert Plugin, "Pyblish plugin not found."

    return Plugin


def _open_houdini_file(sys_args):
    import hou

    if sys_args.get("script_only", False):
        return False

    # Try to open houdini file
    hip_file = sys_args.get("houdini_file", None)

    if not hip_file:
        return False

    try:
        hou.hipFile.load(hip_file, ignore_load_warnings=True)
    except hou.LoadWarning as e:
        print("LoadWarning: {}".format(e))

    print("Open houdini file: ", hip_file)

    return True


def _get_sys_args():
    def check_bool(value):
        if value.lower() in ["false", "none"]:
            return False
        if value.lower() in ["true"]:
            return True
        return value

    sys_args = {}
    for _arg in sys.argv[1:]:
        _data = _arg.split("=")
        sys_args[_data[0]] = check_bool(_data[1])

    return sys_args


def deadline_extract():
    dumps = os.environ["PYBLISH_EXTRACTOR_DUMPS"].split(";")

    sys_args = _get_sys_args()

    for path in dumps:
        with open(path, "r") as file:
            data = json.load(file)

        args = data["args"]
        kwargs = data["kwargs"]
        classname = data["class"]
        function = data["func"]

        Plugin = get_plugin(classname)
        yield Plugin  # For debug/error message

        # Export
        plugin = Plugin()

        # Try to open houdini file
        _open_houdini_file(sys_args)

        extractor = getattr(plugin, function)
        extractor(*args, **kwargs)


if __name__ == "__main__":
    log = logging.getLogger("Pyblish")
    Plugin = None
    try:
        # Houdini install
        from reveries import houdini
        houdini.install()

        # Running plugin
        for Plugin in deadline_extract():
            pass

    except Exception as error:

        if Plugin is None:
            pyblish.lib.extract_traceback(error)
            message = "Failed: {e} -- {e.traceback}"
        else:
            pyblish.lib.extract_traceback(error, Plugin.__module__)
            message = "Failed {p.__name__}: {e} -- {e.traceback}"

        log.error(message.format(p=Plugin, e=error))
        log.error("Fatal Error: Errors occurred during extract, see log..")
        sys.exit(2)

    else:
        print("All good. Success!")
