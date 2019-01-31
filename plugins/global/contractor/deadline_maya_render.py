
import os
import getpass
import platform
import json

import avalon.api
from avalon.vendor import requests
from reveries.plugins import BaseContractor


def parse_output_paths(instance):
    output_paths = dict()

    for count, outpath in enumerate(instance.data["outputPaths"].values()):
        head, tail = os.path.split(outpath)
        output_paths["OutputDirectory%d" % count] = head
        output_paths["OutputFilename%d" % count] = tail

    return output_paths


class ContractorDeadlineMayaRender(BaseContractor):
    """Publish via rendering Maya renderlayers on Deadline

    Submitting jobs per renderlayer(instance) to deadline.

    """

    name = "deadline.maya.render"

    def fulfill(self, context):

        assert "AVALON_DEADLINE" in avalon.api.Session, (
            "Environment variable missing: 'AVALON_DEADLINE'"
        )

        AVALON_DEADLINE = avalon.api.Session["AVALON_DEADLINE"]

        workspace = context.data["workspaceDir"]
        fpath = context.data["currentMaking"]
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        comment = context.data.get("comment", "")

        output_dir = context.data["outputDir"].replace("\\", "/")

        batch_name = "avalon: " + fname

        has_renderlayer = context.data["hasRenderLayers"]
        use_rendersetup = context.data["usingRenderSetup"]

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

        for instance in context:

            payload = {
                "JobInfo": {
                    "Plugin": "MayaBatch",
                    "BatchName": batch_name,  # Top-level group name
                    "Name": "%s - %s" % (batch_name,
                                         instance.data["renderlayer"]),
                    "UserName": getpass.getuser(),
                    "MachineName": platform.node(),
                    "Comment": comment,
                    "Pool": instance.data["deadlinePool"],
                    "Group": instance.data["deadlineGroup"],
                    "Priority": instance.data["deadlinePriority"],
                    "Frames": "{start}-{end}x{step}".format(
                        start=int(instance.data["startFrame"]),
                        end=int(instance.data["endFrame"]),
                        step=int(instance.data["byFrameStep"]),
                    ),
                },
                "PluginInfo": {
                    # Input
                    "SceneFile": fpath,
                    # Resolve relative references
                    "ProjectPath": workspace,
                    # Mandatory for Deadline
                    "Version": context.data["mayaVersion"],
                    # Output directory and filename
                    "OutputFilePath": output_dir,
                    "OutputFilePrefix": instance.data["fileNamePrefix"],

                    "UsingRenderLayers": has_renderlayer,
                    "UseLegacyRenderLayers": not use_rendersetup,
                    "RenderLayer": instance.data["renderlayer"],
                    "Renderer": instance.data["renderer"],
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": [],
                "IdOnly": True
            }

            payload["JobInfo"].update(parse_output_paths(instance))

            environment = self.assemble_environment(instance)
            parsed_environment = {
                "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                    key=key,
                    value=environment[key]
                ) for index, key in enumerate(environment)
            }

            payload["JobInfo"].update(parsed_environment)

            self.log.info("Submitting.. %s" % instance.data["renderlayer"])
            self.log.info(json.dumps(
                payload, indent=4, sort_keys=True)
            )
            response = requests.post(url, json=payload, auth=tuple(auth))

            if response.ok:
                jobid = eval(response.text)["_id"]
                self.log.info("Success. JobID: %s" % jobid)
                self.submit_publish_script(payload, jobid, url, auth)
            else:
                msg = response.text
                self.log.error(msg)
                raise Exception(msg)

        self.log.info("Completed.")

    def submit_publish_script(self, payload, jobid, url, auth):
        # Clean up
        for key in list(payload["JobInfo"].keys()):
            if (key.startswith("OutputDirectory") or
                    key.startswith("OutputFilename")):
                payload["JobInfo"].pop(key)

        payload["JobInfo"].pop("Frames")
        payload["PluginInfo"].pop("OutputFilePath")
        payload["PluginInfo"].pop("OutputFilePrefix")

        # Update
        payload["JobInfo"].update({
            "Name": "_intergrate " + payload["JobInfo"]["Name"],
            "Priority": 99,
            "JobDependencies": jobid,
        })
        payload["PluginInfo"].update({
            "ScriptJob": True,
            "ScriptFilename": os.path.join(os.path.dirname(__file__),
                                           "scripts",
                                           "avalon_contractor_publish.py"),
        })

        response = requests.post(url, json=payload, auth=tuple(auth))

        if response.ok:
            jobid = eval(response.text)["_id"]
            self.log.info("Success. JobID: %s" % jobid)
        else:
            msg = response.text
            self.log.error(msg)
            raise Exception(msg)
