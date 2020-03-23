
import os
import json
import pyblish.api


def get_plugin(classname):
    # Find extractor plugin
    Plugin = None
    for P in pyblish.api.discover():
        if P.__name__ == classname:
            Plugin = P
            break

    assert Plugin, "Pyblish plugin not found."

    return Plugin


if __name__ == "__main__":

    dumps = os.environ["PYBLISH_EXTRACTOR_DUMPS"].split(";")
    for path in dumps:
        with open(path, "r") as file:
            data = json.load(file)

        args = data["args"]
        kwargs = data["kwargs"]
        classname = data["class"]
        function = data["func"]

        # Export
        Plugin = get_plugin(classname)
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
