from common.models import UserSettings


def get_or_create_settings(*, user) -> UserSettings:
    settings_obj, _ = UserSettings.objects.get_or_create(user=user)
    return settings_obj


def update_settings(*, user, **fields) -> UserSettings:
    settings_obj, _ = UserSettings.objects.get_or_create(user=user)
    if fields:
        for field, value in fields.items():
            setattr(settings_obj, field, value)
        settings_obj.save(update_fields=list(fields.keys()))
    return settings_obj
