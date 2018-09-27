
import pyblish.api
import avalon.api


PROJECT_REPORT_TEMPLATE = """
Project: {project}
Silo: {silo}
Asset: {asset}
"""


SUBSET_REPORT_TEMPLATE = """

Instance: {instance}
Subset: {subset}
Version: {version}

Representations:
{representations}

"""

REPRESENTATION_REPORT_TEMPLATE = """

    * {representation}
        - Contractor: {contractor}
        - Contract Info:
            {contractInfo}

"""


def copy_reports():
    pass


class PublishReports(pyblish.api.ContextPlugin):
    """Report publish process results
    """

    label = "Reports (Please READ)"
    order = pyblish.api.IntegratorOrder + 0.49999

    def process(self, context):
        project_data = {
            "project": avalon.api.Session["AVALON_PROJECT"],
            "silo": avalon.api.Session["AVALON_SILO"],
            "asset": avalon.api.Session["AVALON_ASSET"],
        }
        self.log.info(PROJECT_REPORT_TEMPLATE.format(**project_data))

        for instance in context:
            repr_reports = ""
            for package in instance.data["packages"]:
                repr_data = {
                    "representation": package,
                    "contractor": "",
                    "contractInfo": "",
                }
                report = REPRESENTATION_REPORT_TEMPLATE.format(**repr_data)
                repr_reports += report

            subset_data = {
                "instance": instance.data["name"],
                "subset": instance.data["subset"],
                "version": instance.data["version_next"],
                "representations": repr_reports,
            }
            self.log.info(SUBSET_REPORT_TEMPLATE.format(**subset_data))
