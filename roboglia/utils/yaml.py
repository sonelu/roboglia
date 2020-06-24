import yaml
import os
import collections


def load_yaml_with_include(file_name):
    """Loads a YAML file safely and returns a dictionary with the configuration
    data.
    Suppports ``include`` directive. If there is an ``include`` key at the top
    level in the source file, the files specified will be opened *in the given
    order* and data will be merged. Updates from a new file can create new
    keys in the merged dictionary or update the existing ones. At the end
    the content of the original file is merged in the same manner in the
    final dictionary. The ``include`` statements are removed from the final
    dictionary.
    """
    base_path = os.path.dirname(file_name)
    with open(file_name, 'r') as f:
        main_dict = yaml.safe_load(f)
    if 'include' not in main_dict:
        return main_dict
    else:
        full_dict = {}
        includes = main_dict['include']
        del main_dict['include']
        for include_file in includes:
            include_path = os.path.join(base_path, include_file)
            norm_include_path = os.path.normpath(include_path)
            with open(norm_include_path, 'r') as f:
                include_dict = yaml.safe_load(f)
                deep_update(source=full_dict, overrides=include_dict)
        return deep_update(source=full_dict, overrides=main_dict)


def deep_update(source, overrides):
    """
    Update a nested dictionary or similar mapping.
    Modify ``source`` in place.
    """
    for k, v in overrides.items():
        if isinstance(v, collections.Mapping) and v:
            returned = deep_update(source.get(k, {}), v)
            source[k] = returned
        else:
            source[k] = overrides[k]
    return source
