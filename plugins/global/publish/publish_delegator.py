
import pyblish.api

from reveries.vendor.six import string_types
from reveries.plugins import find_contractor


class PublishDelegator(pyblish.api.ContextPlugin):
    """Delegate publish integration
    """

    label = "Publish Delegator"
    order = pyblish.api.IntegratorOrder + 0.49

    def process(self, context):

        if context.data.get("contractorAccepted"):
            # Already in contractor's hand.
            return

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        active_contractors = dict()
        instances_group = dict()

        for instance in context:
            if instance.data.get("publish") is False:
                continue

            if instance.data.get("useContractor") is False:
                continue

            contractor_name = instance.data.get("publishContractor")
            if contractor_name is None:
                continue

            if not isinstance(contractor_name, string_types):
                raise TypeError("`publishContractor` should be a string, "
                                "not {}.".format(type(contractor_name)))

            # Find contractor
            if contractor_name not in active_contractors:
                Contractor = find_contractor(contractor_name)
                if Contractor is None:
                    msg = "Undefined Contractor: {!r}".format(contractor_name)
                    raise NotImplementedError(msg)

                active_contractors[contractor_name] = Contractor()
                instances_group[contractor_name] = list()

            instances_group[contractor_name].append(instance)

            self.log.info("Delegating {0!r} publishment to {1!r} ..."
                          "".format(instance, contractor_name))

        if len(active_contractors) == 0:
            self.log.info("No instance require delegation.")
            return

        # Delegate!
        for name, contractor in active_contractors.items():
            contractor.fulfill(context, instances_group[name])
