def check_key(key, dict_info, context, context_id, logger, message=None):
    """Checks if a `key` is in a dictionary `dict_info` and raises a cusomized
    exception message with better context.

    Args:
        key (str): the key we are looking for
        dict_info (dict): the dictionary where we are looking
        context (str): a string indicating the context of the check, for
            example 'Bus' or 'Device'
        context_id (str or int): indicates the precise context (the name
            of the object or, in case the `key` we are searching is the name
            we will have to use the index of the item in the initialization
            dictionary)
        logger (logger object): where the logging will be written
        message (str): if this is provided the fuction will use this message
            for logging and raise instead of building a message specific
            for the context.

    Raises:
        KeyError: if the `key` is not found in the `dict_info`
    """
    if key not in dict_info:
        if message is None:
            message = f'"{key}" specification missing ' + \
                      f'for {context}: {context_id}'
        else:
            message = f'{message} for {context}: {context_id}'
        logger.critical(message)
        raise KeyError(message)


def check_type(value, to_type, context, context_id, logger, message=None):
    """Checks if a value is of a certain type and raises a cusomized
    exception message with better context.

    Args:
        value (any): a value to be checked
        to_type (type): the type to be checked against
        context (str): a string indicating the context of the check, for
            example 'Bus' or 'Device'
        context_id (str or int): indicates the precise context (the name
            of the object or, in case the `key` we are searching is the name
            we will have to use the index of the item in the initialization
            dictionary)
        logger (logger object): where the logging will be written
        message (str): if this is provided the fuction will use this message
            for logging and raise instead of building a message specific
            for the context.

    Raises:
        ValueError: if the value is not of the type indicated
    """
    if type(value) is not to_type:
        if message is None:
            message = f'value {value} should be of type {to_type} ' + \
                      f'for {context}: {context_id}'
        else:
            message = f'{message} for {context}: {context_id}'
        logger.critical(message)
        raise ValueError(message)


def check_options(value, options, context, context_id, logger, message=None):
    """Checks if a value is in a list of allowed options.

    Args:
        value (any): a value to be checked
        options (list): the allowed options for the vlue
        context (str): a string indicating the context of the check, for
            example 'Bus' or 'Device'
        context_id (str or int): indicates the precise context (the name
            of the object or, in case the `key` we are searching is the name
            we will have to use the index of the item in the initialization
            dictionary)
        logger (logger object): where the logging will be written
        message (str): if this is provided the fuction will use this message
            for logging and raise instead of building a message specific
            for the context.

    Raises:
        ValueError: if the value is not in the allowed options
    """
    if value not in options:
        if message is None:
            message = f'value {value} should be one of {options} ' + \
                      f'for {context}: {context_id}'
        else:
            message = f'{message} for {context}: {context_id}'
        logger.critical(message)
        raise ValueError(message)
