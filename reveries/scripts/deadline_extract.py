
import os
import json
import pyblish.api


def get_extractor(classname, function):
    # Find extractor plugin
    Plugin = None
    for P in pyblish.api.discover():
        if P.__name__ == classname:
            Plugin = P
            break

    assert Plugin, "Pyblish plugin not found."

    return getattr(Plugin(), function)


if __name__ == "__main__":

    dumps = os.environ["PYBLISH_EXTRACTOR_DUMPS"].split(";")
    for path in dumps:
        with open(path, "r") as file:
            data = json.load(file)

        args = data["args"]
        kwargs = data["kwargs"]
        classname = data["class"]
        function = data["func"]

        if data["eachFrame"]:
            # Frame range (Maya Only)
            from maya import mel
            start = int(mel.eval("DeadlineValue(\"StartFrame\")"))
            end = int(mel.eval("DeadlineValue(\"EndFrame\")"))
            kwargs["start"] = start
            kwargs["end"] = end

        # Export
        extractor = get_extractor(classname, function)
        extractor(*args, **kwargs)
