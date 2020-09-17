from avalon import io


def publish(asset_id, subset_name, families):
    """
    Publish subset.
    :param asset_id: (object)
    :param subset_name: (str)
    :param families: (list)
    :return:
    """

    subset_context = {
        'name': subset_name,
        'parent': asset_id,
        'type': 'subset',
        'data': {
            'families': families,
            'subsetGroup': ''
        },
        'schema': 'avalon-core:subset-3.0'}
    # print('subset_context: ', subset_context)

    _filter = {"parent": asset_id, "name": subset_name}
    subset_data = io.find_one(_filter)

    if subset_data is None:
        subset_id = io.insert_one(subset_context).inserted_id
    else:
        subset_id = subset_data['_id']

    return subset_id
