import os
import json
import Deadline.Events


def GetDeadlineEventListener():
    return AvalonJobProgressDelete()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class AvalonJobProgressDelete(Deadline.Events.DeadlineEventListener):

    def __init__(self):
        self.OnJobDeletedCallback += self.OnJobDeleted

    def Cleanup(self):
        del self.OnJobDeletedCallback

    def OnJobDeleted(self, job):

        required_env = [
            "PYTHONPATH",
            "AVALON_DB",
            "AVALON_MONGO",
            "AVALON_PROJECT",
            "PYBLISH_DUMP_FILE",
        ]

        job_environ = job.GetJobEnvironmentKeys()
        if not all(key in job_environ for key in required_env):
            # Not a valid Avalon job
            return

        post = job.GetJobEnvironmentKeyValue("AVALON_POST_TASK_SCRIPTS")
        if "publish_by_task" not in post:
            # Not a Avalon progressive publish job
            return

        print("Avalon progressive publish job found, clearing progress..")

        dumpfile = job.GetJobEnvironmentKeyValue("PYBLISH_DUMP_FILE")

        # Check and load dumps
        if not os.path.isfile(dumpfile):
            raise Exception("Instance dump file not found: %s" % dumpfile)

        with open(dumpfile, "r") as file:
            instance_dump = json.load(file)

        dumpfile = instance_dump["contextDump"]

        if not os.path.isfile(dumpfile):
            raise Exception("Context dump file not found: %s" % dumpfile)

        with open(dumpfile, "r") as file:
            context_dump = json.load(file)

        for instance in context_dump["instances"]:
            if instance["id"] == instance_dump["id"]:
                data = {
                    "asset": instance["asset"],
                    "subset": instance["subset"],
                    "version": instance["version"],
                }
                self.load_environment(job)
                self.clear_progress(data)
                break
        else:
            raise Exception("No instance been matched in context.")

        print("Avalon progressive publish job completed.")

    def clear_progress(self, data):
        import avalon.io

        avalon.io.install()

        asset = avalon.io.find_one({"type": "asset",
                                    "name": data["asset"]})
        subset = avalon.io.find_one({"type": "subset",
                                     "name": data["subset"],
                                     "parent": asset["_id"]})
        version = avalon.io.find_one({"type": "version",
                                      "name": data["version"],
                                      "parent": subset["_id"]})
        avalon.io.update_many({"_id": version["_id"]},
                              {"$unset": {"data.progress": "",
                                          "data.deadlineJobId": ""}})

    def load_environment(self, job):
        import os
        import sys

        for key in job.GetJobEnvironmentKeys():
            if key.startswith("AVALON"):
                os.environ[key] = job.GetJobEnvironmentKeyValue(key)

        for path in job.GetJobEnvironmentKeyValue("PYTHONPATH").split(";"):
            sys.path.append(path)
