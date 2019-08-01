
import os
import getpass
import platform
import json
import re
import subprocess

import avalon.api
from avalon.vendor import requests
from reveries.plugins import BaseContractor
from reveries.utils import temp_dir


def parse_output_paths(instance):
    output_paths = dict()

    for count, outpath in enumerate(instance.data["outputPaths"].values()):
        head, tail = os.path.split(outpath)
        output_paths["OutputDirectory%d" % count] = head
        output_paths["OutputFilename%d" % count] = tail

    return output_paths


def add_envvars(environment):
    add_vars = [
        "MAYA_MODULE_PATH",
        "ARNOLD_PLUGIN_PATH",
    ]

    for var in add_vars:
        environment[var] = os.getenv(var, "")


class ContractorDeadlineMayaRender(BaseContractor):
    """Publish via rendering Maya renderlayers on Deadline

    Submitting jobs per renderlayer(instance) to deadline.

    """

    name = "deadline.maya.render"

    def fulfill(self, context, instances):

        cmd = None
        url = None
        auth = None

        if context.data.get("USE_DEADLINE_APP"):
            AVALON_DEADLINE_APP = avalon.api.Session["AVALON_DEADLINE_APP"]

            # E.g. C:/Program Files/Thinkbox/Deadline10/bin/deadlinecommand.exe
            cmd = AVALON_DEADLINE_APP

        else:
            AVALON_DEADLINE = avalon.api.Session["AVALON_DEADLINE"]

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

        workspace = context.data["workspaceDir"]
        fpath = context.data["currentMaking"]
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)
        comment = context.data.get("comment", "")

        project = context.data["projectDoc"]

        project_id = str(project["_id"])[-4:].upper()
        project_code = project["data"].get("codename", project_id)

        asset = context.data["assetDoc"]["name"]

        output_dir = context.data["outputDir"].replace("\\", "/")

        batch_name = "({projcode}): [{asset}] {filename}"
        batch_name = batch_name.format(projcode=project_code,
                                       asset=asset,
                                       filename=fname)

        has_renderlayer = context.data["hasRenderLayers"]
        use_rendersetup = context.data["usingRenderSetup"]

        for instance in instances:

            job_name = "{subset} v{version:0>3}".format(
                subset=instance.data["subset"],
                version=instance.data["versionNext"],
            )

            payload = {
                "JobInfo": {
                    "Plugin": "MayaBatch",
                    "BatchName": batch_name,  # Top-level group name
                    "Name": job_name,
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
                    "ChunkSize": instance.data["deadlineFramesPerTask"],

                    "ExtraInfo0": project["name"],
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
                    "Camera": instance.data["renderCam"][0],
                },
                # Mandatory for Deadline, may be empty
                "AuxFiles": [],
                "IdOnly": True
            }

            payload["JobInfo"].update(parse_output_paths(instance))

            environment = self.assemble_environment(instance)

            add_envvars(environment)

            if instance.data.get("hasAtomsCrowds"):
                # Change Deadline group for AtomsCrowd
                payload["JobInfo"]["Group"] = "atomscrowd"
            else:
                # AtomsCrowd module path is available for every machine by
                # default, so we must remove it if this renderLayer does
                # not require AtomsCrowd plugin. Or the license will not
                # be enough for other job that require Atoms.
                module_path = environment["MAYA_MODULE_PATH"]
                filtered = list()
                for path in module_path.split(";"):
                    if "AtomsMaya" not in path:
                        filtered.append(path)
                environment["MAYA_MODULE_PATH"] = ";".join(filtered)

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

            if cmd:
                jobid = self.via_command(cmd, payload)
            else:
                jobid = self.via_web_service(url, payload, auth)

            self.submit_publish_script(project, payload, jobid, cmd, url, auth)

        self.log.info("Completed.")

    def submit_publish_script(self, project, payload, jobid, cmd, url, auth):
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
            "UserName": project["data"]["deadline"]["publishUser"],
            "Priority": 99,
            "JobDependencies": jobid,
        })
        payload["PluginInfo"].update({
            "ScriptJob": True,
            "ScriptFilename": os.path.join(os.path.dirname(__file__),
                                           "scripts",
                                           "avalon_contractor_publish.py"),
        })

        if cmd:
            self.via_command(cmd, payload)
        else:
            self.via_web_service(url, payload, auth)

    def via_web_service(self, url, payload, auth):
        response = requests.post(url, json=payload, auth=tuple(auth))

        if not response.ok:
            msg = response.text
            self.log.error(msg)
            raise Exception("Submission failed...")
        else:
            jobid = eval(response.text)["_id"]
            self.log.info("Success. JobID: %s" % jobid)
            return jobid

    def via_command(self, cmd, payload):

        def to_txt(document, out):
            # Write dict to key-value txt file
            with open(out, "w") as fp:
                for key, val in document.items():
                    fp.write("{key}={val}\n".format(key=key, val=val))

        job_info = payload["JobInfo"]
        plugin_info = payload["PluginInfo"]

        info_dir = temp_dir(prefix="deadline_")
        job_info_file = os.path.join(info_dir, "job_info.job")
        plugin_info_file = os.path.join(info_dir, "plugin_info.job")

        to_txt(job_info, job_info_file)
        to_txt(plugin_info, plugin_info_file)

        cmd += " %s %s" % (job_info_file, plugin_info_file)
        output = subprocess.check_output(cmd)

        output = output.decode("utf-8")
        if "Result=Success" not in output.split():
            raise Exception("Submission failed...")
        else:
            parts = re.split("[=\n\r]", output)
            jobid = parts[parts.index("JobID") + 1]
            self.log.info("Success. JobID: %s" % jobid)
            return jobid
