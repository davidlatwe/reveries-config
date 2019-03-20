
import os
import getpass
import platform
import json

import avalon.api
import avalon.io

from avalon.vendor import requests
from reveries.plugins import BaseContractor


class ContractorDeadlineMayaScript(BaseContractor):
    """Publish via running script on Deadline

    Grouping instances via their Deadline Pool, Group, Priority settings, then
    submitting jobs per instance group.

    """

    name = "deadline.maya.script"

    def fulfill(self, context, instances):

        assert "AVALON_DEADLINE" in avalon.api.Session, (
            "Environment variable missing: 'AVALON_DEADLINE'"
        )

        AVALON_DEADLINE = avalon.api.Session["AVALON_DEADLINE"]

        workspace = context.data["workspaceDir"]
        fpath = context.data["currentMaking"]
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        comment = context.data.get("comment", "")

        asset = context.data["assetDoc"]["name"]

        project = context.data["projectDoc"]

        batch_name = "avalon.script: [{asset}] {filename}"
        batch_name = batch_name.format(asset=asset, filename=fname)

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

        auth = os.environ["AVALON_DEADLINE_AUTH"].split(":")

        # Grouping instances

        dl_group = project["data"]["deadline"]["publishGroup"]

        instance_group = dict()
        for instance in instances:
            dl_pool = instance.data["deadlinePool"]
            dl_priority = instance.data["deadlinePriority"]

            group_key = (dl_pool, dl_group, dl_priority)

            if group_key not in instance_group:
                instance_group[group_key] = list()

            instance_group[group_key].append(instance)

        for settings, group in instance_group.items():
            dl_pool, dl_group, dl_priority = settings

            if len(group) == 1:
                instance = group[0]
                job_name = "{subset} v{version:0>3}".format(
                    subset=instance.data["subset"],
                    version=instance.data["versionNext"],
                )
            else:
                job_name = "queued %d subsets" % len(group)

            environment = dict()
            for instance in group:
                self.log.info("Adding instance: %s" % instance.data["subset"])
                environment.update(self.assemble_environment(instance))

            payload = {
                "JobInfo": {
                    "Plugin": "MayaBatch",
                    "BatchName": batch_name,  # Top-level group name
                    "Name": job_name,
                    "UserName": getpass.getuser(),
                    "MachineName": platform.node(),
                    "Comment": comment,
                    "Pool": dl_pool,
                    "Group": dl_group,
                    "Priority": dl_priority,
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

            response = requests.post(url, json=payload, auth=tuple(auth))

            if response.ok:
                jobid = eval(response.text)["_id"]
                self.log.info("Success. JobID: %s" % jobid)
            else:
                msg = response.text
                self.log.error(msg)
                raise Exception(msg)

        self.log.info("Completed.")
