
import os
import getpass
import platform
import json

import avalon.api
import avalon.io

from avalon.vendor import requests
from reveries.plugins import BaseContractor


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
        group = deadline_job["maya_cache_group"]
        priority = deadline_job["maya_cache_priority"]

        script_file = os.path.join(os.path.dirname(__file__),
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
                "Group": group,
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
