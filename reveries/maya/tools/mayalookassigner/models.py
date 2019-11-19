from collections import defaultdict
from avalon.tools import models

from avalon.vendor.Qt import QtCore
from avalon.vendor import qtawesome
from avalon.style import colors


UNDEFINED_SUBSET = "(Unknown)"


class AssetModel(models.TreeModel):

    Columns = ["label", "subset"]

    def add_items(self, items, by_selection=False):
        """
        Add items to model with needed data
        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        child_icon = "mouse-pointer" if by_selection else "file-o"

        # Add the items sorted by label
        sorter = (lambda x: x["label"])

        for item in sorted(items, key=sorter):

            asset_item = models.Item()
            asset_item.update(item)
            asset_item["icon"] = "folder"

            # Add namespace children
            namespaces = item["namespaces"]
            namespace_nodes = item["nodesByNamespace"]
            namespace_selection = item["selectByNamespace"]

            for namespace in sorted(namespaces):
                child = models.Item()
                child.update(item)
                child.update({
                    "label": (namespace if namespace != ":"
                              else "(no namespace)"),
                    "subset": item["subsets"][namespace],
                    "namespace": namespace,
                    "looks": item["looks"],
                    "nodes": namespace_nodes[namespace],
                    "selectBack": namespace_selection[namespace],
                    "icon": child_icon
                })
                asset_item.add_child(child)

            self.add_child(asset_item)

        self.endResetModel()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == self.ItemRole:
            node = index.internalPointer()
            return node

        # Add icon
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                node = index.internalPointer()
                icon = node.get("icon")
                if icon:
                    return qtawesome.icon("fa.{0}".format(icon),
                                          color=colors.default)
            if index.column() == 1:
                node = index.internalPointer()
                if "subset" in node:
                    if node["subset"] == UNDEFINED_SUBSET:
                        return qtawesome.icon("fa.question-circle",
                                              color="#BD2D2D")
                    else:
                        return qtawesome.icon("fa.bookmark", color="#BBC0C6")

        return super(AssetModel, self).data(index, role)

    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if section == self.Columns.index("label"):
                return "asset"

        return super(AssetModel, self).headerData(section,
                                                  orientation,
                                                  role)


class _LookModel(models.TreeModel):

    def data(self, index, role):

        if not index.isValid():
            return

        # Add icon
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return qtawesome.icon("fa.paint-brush", color="#BBC0C6")

        return super(_LookModel, self).data(index, role)

    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if section == self.Columns.index("label"):
                return "subset"

        return super(_LookModel, self).headerData(section,
                                                  orientation,
                                                  role)


class LookModel(_LookModel):
    """Model displaying a list of looks and matches for assets"""

    Columns = ["label", "match"]

    def add_items(self, items):
        """Add items to model with needed data

        An item exists of:
            {
                "subset": 'name of subset',
                "asset": asset_document
            }

        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        # Collect the assets per look name (from the items of the AssetModel)
        look_subsets = defaultdict(list)
        for asset_item in items:
            asset = asset_item["asset"]
            for look in asset_item["looks"]:
                key = look["name"]
                look_subsets[key].append(asset)

        for subset, assets in sorted(look_subsets.iteritems()):

            # Define nice label without "look" prefix for readability
            label = subset if not subset.startswith("look") else subset[4:]

            item_node = models.Item()
            item_node["label"] = label
            item_node["subset"] = subset

            # Amount of matching assets for this look
            item_node["match"] = len(assets)

            # Store the assets that have this subset available
            item_node["assets"] = assets

            self.add_child(item_node)

        self.endResetModel()


class LoadedLookModel(_LookModel):
    """Model displaying a list of loaded looks and matches for assets"""

    Columns = ["label", "ident"]

    def add_items(self, items):

        self.beginResetModel()

        # Collect the assets per look name (from the items of the AssetModel)
        look_subsets = defaultdict(list)
        for asset_item in items:
            asset = asset_item["asset"]
            for look in asset_item["loadedLooks"]:
                key = (look["name"], look["ident"])
                look_subsets[key].append(asset)

        for (subset, ident), assets in sorted(look_subsets.iteritems()):

            # Define nice label without "look" prefix for readability
            label = subset if not subset.startswith("look") else subset[4:]

            item_node = models.Item()
            item_node["label"] = label
            item_node["subset"] = subset
            item_node["ident"] = ident

            # Store the assets that have this subset available
            item_node["assets"] = assets

            self.add_child(item_node)

        self.endResetModel()
