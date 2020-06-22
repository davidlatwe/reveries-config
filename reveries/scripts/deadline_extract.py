
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
            Plugin = P
            break

    assert Plugin, "Pyblish plugin not found."

    return Plugin


def deadline_extract():
    dumps = os.environ["PYBLISH_EXTRACTOR_DUMPS"].split(";")
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

        if (classname == "ExtractArnoldStandIn"
                and "maya" in Plugin.hosts):
            # Set frame range from Deadline task (Maya Only)
            from maya import mel
            start = int(mel.eval("DeadlineValue(\"StartFrame\")"))
            end = int(mel.eval("DeadlineValue(\"EndFrame\")"))
            kwargs["start"] = start
            kwargs["end"] = end

        extractor = getattr(plugin, function)
        extractor(*args, **kwargs)


if __name__ == "__main__":
    log = logging.getLogger("Pyblish")
    Plugin = None
    try:
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
