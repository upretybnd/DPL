from django.core.files.storage import storages


def private_storage():
    """Storage for sensitive uploads; resolved lazily so settings can switch between disk and R2."""
    return storages["private"]
