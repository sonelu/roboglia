# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

logger = logging.getLogger(__name__)

__registered_classes = {}


def register_class(class_obj):
    """Registers a class with the class factory dictionary. If the class is
    already registered the function does not replace it. In the factory
    the class is represented by name.

    Args:
        cls (class object): is the class to be registerd.

    Raises:
        ValueError: if the parameter passed is not a Class object.
    """
    if classmethod.__name__ not in __registered_classes:
        if not isinstance(class_obj, type):
            mess = f'{class_obj} is not a Class object. ' + \
                   'You must pass a Class not an instance.'
            logger.critical(mess)
            raise ValueError(mess)
        __registered_classes[class_obj.__name__] = class_obj


def unregister_class(class_name):
    """Removes a class from the class factory dictionary thus making it
    unavaialble for dynamic instantiation.

    Args:
        class_name (str): the name of the class to be removed.

    Raises:
        KeyError: if the class name is not in the class factory dictionary.
    """
    if class_name not in __registered_classes:
        mess = f'class {class_name} not registered with the factory'
        logger.critical(mess)
        raise KeyError(mess)
    else:
        del __registered_classes[class_name]


def get_registered_class(class_name):
    """Retrieves a class object from the class factory by name.

    Args:
        class_name (str): the name of the class to be retrieved.

    Returns:
        class type: the class requested

    Raises:
        KeyError: if the class name is not in the class factory dictionary.

    Example:
        The way the `get_regstered_class` is to be used is by first retrieving
        the needed class object and then instantiating it according to the
        rules for that class::

            bus_class = get_registered_class('DynamixelBus')
            bus = bus_class(init_dict)
    """
    if class_name in __registered_classes:
        return __registered_classes[class_name]
    else:
        mess = f'class {class_name} not registered with the factory'
        logger.critical(mess)
        raise KeyError(mess)


def registered_classes():
    """Convenience function to inspect the dictionary of registered classes.

    Returns:
        dict: the registered class dictionary in format {class_name: class_ref}
    """
    return __registered_classes
