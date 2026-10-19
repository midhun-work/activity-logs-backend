"""Create / update / delete of any model, recorded when a signed-in user's request makes it.

Saves made by scripts, cron jobs or anonymous requests are not logged, and neither are the skipped
apps and models (see conf.py). Rows are written only after the change itself is committed, on the
database that holds the record (the signal's `using`), so a rolled-back change leaves no log.
Changes made with `queryset.update()` or `bulk_create()` send no signals and are not logged.
"""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from . import conf
from .context import current_user
from .recorder import build, object_label, write_after_commit
from .utils import auto_fields, model_label, secret_values, snapshot


def _tracked(model):
    meta = model._meta
    if meta.app_label.lower() in conf.skip_apps():
        return False
    return model_label(model).lower() not in conf.skip_models()


@receiver(pre_save, dispatch_uid="logs_pre_save")
def remember_old_values(sender, instance, raw=False, using=None, **kwargs):
    """Before an update, keep the record as it is in the database, to compare with after the save."""
    if raw or instance.pk is None or not _tracked(sender) or current_user() is None:
        return
    try:
        old = sender._base_manager.using(using).filter(pk=instance.pk).first()
    except Exception:
        old = None
    instance._logs_old = snapshot(old) if old is not None else None
    # Masked fields read "***" before and after; their real values tell whether they changed.
    instance._logs_old_secrets = secret_values(old) if old is not None else {}


@receiver(post_save, dispatch_uid="logs_post_save")
def record_save(sender, instance, created, raw=False, using=None, **kwargs):
    if raw or not _tracked(sender):
        return
    user = current_user()
    if user is None:
        return
    label = model_label(sender)
    name = sender._meta.verbose_name.capitalize()
    new = snapshot(instance)
    old = None if created else getattr(instance, "_logs_old", None)
    old_secrets = getattr(instance, "_logs_old_secrets", {})
    for attribute in ("_logs_old", "_logs_old_secrets"):
        if hasattr(instance, attribute):
            delattr(instance, attribute)

    if created or old is None:
        values = build(
            "create" if created else "update",
            user=user,
            model=label,
            object_id=instance.pk,
            label=object_label(instance),
            description=f"{name} {'created' if created else 'updated'}",
            new=new,
        )
    else:
        ignore = auto_fields(sender)
        changed = [key for key, value in new.items() if key not in ignore and old.get(key) != value]
        changed += [key for key, value in secret_values(instance).items() if old_secrets.get(key) != value and key not in changed]
        if not changed:
            return  # saved without changing anything
        values = build(
            "update",
            user=user,
            model=label,
            object_id=instance.pk,
            label=object_label(instance),
            description=f"{name} updated",
            old={key: old.get(key) for key in changed},
            new={key: new[key] for key in changed},
            changed=changed,
        )
    write_after_commit(values, using)


@receiver(post_delete, dispatch_uid="logs_post_delete")
def record_delete(sender, instance, using=None, **kwargs):
    if not _tracked(sender):
        return
    user = current_user()
    if user is None:
        return
    values = build(
        "delete",
        user=user,
        model=model_label(sender),
        object_id=instance.pk,
        label=object_label(instance),
        description=f"{sender._meta.verbose_name.capitalize()} deleted",
        old=snapshot(instance),
    )
    write_after_commit(values, using)
