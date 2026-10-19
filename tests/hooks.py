def object_label(instance):
    return getattr(instance, "phone", "") or ""
