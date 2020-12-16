import avalon

import pyblish.api


class ValidateLookDevHasDependency(pyblish.api.InstancePlugin):
    """Validate Lookdev Has Dependency

    在 USD 中 lookdev 與 model 之間必須要有 dependency

    你的 Subset Set 需要看起來像這樣(以 Asset Robot 舉例):

    - lookDefault
        L Robot_model_01_:ROOT

    也就是你的 model 必須是reference, 如果不是, 也請重新 reference 一個新的進來
    詳情請參考 KnowHow 上關於 lookdev publish 的相關內容

    """

    order = pyblish.api.ValidatorOrder + 0.491

    label = "Validate Lookdev Dependency"
    hosts = ["maya"]
    families = [
        "reveries.look"
    ]

    def process(self, instance):
        import maya.cmds as cmds
        from reveries.maya import lib, pipeline

        if not instance.data.get("publishUSD", True):
            return

        subset_name = instance.data["subset"]
        for _member in cmds.sets(subset_name, q=True):
            namespace = _member.split(":")[0] if len(_member.split(":"))>1 else None
            if namespace:
                print("namespace: ", namespace)
                container = pipeline.get_container_from_namespace(namespace)

                if cmds.getAttr("{}.loader".format(container)) == "ModelLoader":
                    subset_id = cmds.getAttr("{}.subsetId".format(container))
                    instance.data["model_subset_id"] = subset_id

        if not instance.data.get("model_subset_id", None):
            raise RuntimeError("{}: Get model dependency failed".format(instance))

        # subset_id = ""
        # root_container_data = instance.context.data.get(
        #     "RootContainers")
        # for container_name, container_data in root_container_data.items():
        #     if container_data["loader"] == "ModelLoader":
        #         subset_id = container_data.get("subsetId", "")
        # instance.data["model_subset_id"] = subset_id
