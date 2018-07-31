
import os
import sys
import inspect
import logging

import getpass
import platform
import json

import avalon.api
import avalon.io

from avalon.vendor import requests


class BaseContractor(object):

    def __init__(self):
        self.log = logging.getLogger(self.name)

    def assemble_environment(self, context):
        """Include critical variables with submission
        """
        environment = dict({
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),

            "AVALON_FFMPEG": os.getenv("AVALON_FFMPEG", ""),
        }, **avalon.api.Session)

        # Write instances' name and version
        for ind, instance in enumerate(context):
            if not instance.data.get("publish_contractor") == self.name:
                continue

            # instance subset name
            key = "AVALON_DELEGATED_SUBSET_%d" % ind
            environment[key] = instance.data["name"]
            # instance subset version next (for monitor eye debug)
            key = "AVALON_DELEGATED_VERSION_NUM_%d" % ind
            environment[key] = instance.data["version_next"]
            #
            # instance subset version object id
            #
            # This should prevent version bump when re-running publish with
            # same params.
            #
            key = "AVALON_DELEGATED_VERSION_ID_%d" % ind
            environment[key] = instance.data["version_id"]

        return environment


def find_contractor(name):
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for cls_name, cls in clsmembers:
        if (cls_name.startswith("Contractor") and
                hasattr(cls, "assemble_environment") and
                hasattr(cls, "fulfill") and
                hasattr(cls, "name")):
            if cls.name == name:
                return cls
    return None


"""TODO: Move all contractor to each .py file as plugin
"""


class ContractorDeadlineMayaScript(BaseContractor):

    name = "deadline.maya.script"

    def fulfill(self, context):

        assert "AVALON_DEADLINE" in avalon.api.Session, (
            "Environment variable missing: 'AVALON_DEADLINE'"
        )

        AVALON_DEADLINE = avalon.api.Session["AVALON_DEADLINE"]

        workspace = context.data["workspaceDir"]
        fpath = context.data["currentFile"]
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        comment = context.data.get("comment", "")
        time = context.data["time"]

        project = avalon.io.find_one({"type": "project"})
        deadline_job = project["data"]["deadline"]["job"]
        pool = deadline_job["maya_cache_pool"]
        priority = deadline_job["maya_cache_priority"]

        config_root = os.path.dirname(os.path.dirname(__file__))
        script_file = os.path.join(config_root,
                                   "scripts",
                                   "avalon_contractor_publish.py")

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(AVALON_DEADLINE)
        #
        # Documentation about RESTful api
        # https://docs.thinkboxsoftware.com/products/deadline/
        # 10.0/1_User%20Manual/manual/rest-jobs.html#rest-jobs-ref-label
        #
        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                "Plugin": "MayaBatch",
                "BatchName": fname,  # Top-level group name
                "Name": "%s - %s" % ("Publishing Context", time),
                "UserName": getpass.getuser(),
                "MachineName": platform.node(),
                "Comment": comment,
                "Pool": pool,
                "Priority": priority,
            },
            "PluginInfo": {
                # Input
                "SceneFile": fpath,
                # Resolve relative references
                "ProjectPath": workspace,
                # Mandatory for Deadline
                "Version": context.data["mayaVersion"],
                "ScriptJob": True,
                "ScriptFilename": script_file,
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
            "IdOnly": True
        }

        environment = self.assemble_environment(context)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        self.log.info("Submitting..")
        self.log.info(json.dumps(
            payload, indent=4, sort_keys=True)
        )

        auth = os.environ["AVALON_DEADLINE_AUTH"].split(":")
        response = requests.post(url, json=payload, auth=tuple(auth))

        if response.ok:
            self.log.info("Complete.")
        else:
            msg = response.text
            self.log.error(msg)
            raise Exception(msg)


class ContractorDeadlineMayaRender(BaseContractor):

    name = "deadline.maya.render"

    def fulfill(self, context):
        pass
