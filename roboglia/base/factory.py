
__registered_classes = {}


def register_class(cls):
    if cls.__name__ not in __registered_classes:
        __registered_classes[cls.__name__] = cls

def unregister_class(class_name):
    if class_name not in __registered_classes:
        raise KeyError(f'class {class_name} not registered with the factory')
    else:
        del __registered_classes[class_name]

def get_registered_class(class_name):
    if class_name in __registered_classes:
        return __registered_classes[class_name]
    else:
        raise KeyError(f'class {class_name} not registered with the factory')

def registered_classes():
    return __registered_classes