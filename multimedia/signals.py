from filecmp import cmp
import os

from django.conf import settings
from django.contrib.contenttypes.models import ContentType


def set_encode_profiles(sender, instance, **kwargs):
    """
    Signal: pre_save
    Sender: Video, Audio

    Prior to saving, store the currently configured encoding profiles
    so we can later detect if the file needs to be encoded. If a new
    file is being uploaded, force the re-encode.
    """
    # Store the currently configured encoding profiles
    # so we can compare against them post-save
    if instance.pk:
        instance._profiles = set(list(instance.profiles.values_list('pk', flat=True)))
    else:
        instance._profiles = set(list())

    # If a new file is being uploaded that is different
    # from the existing file, set it to be re-encoded
    if hasattr(instance.file.file, 'temporary_file_path'):
        try:
            current = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass
        else:
            current_file = os.path.join(settings.MEDIA_ROOT, current.file.name)
            new_file = os.path.join(settings.MEDIA_ROOT,
                                    instance.file.file.temporary_file_path())
            if not cmp(current_file, new_file):
                instance._reencode = True
            current.file.delete(save=False)


def encode_profiles_changed(sender, instance, action, **kwargs):
    """Handle changes in associated encoding profiles.

    If profiles are added, create an encoding task for each of the new
    profiles. If a re-encode is forced, create encoding tasks for all
    associated profiles.

    If profiles are removed, create a deletion task to remove the
    remotely stored media.

    Signal: m2m_changed
    Sender: MediaBase.profiles.through
    """
    if action in ['post_add']:
        added_profiles = list(kwargs['pk_set'].difference(instance._profiles))
        if added_profiles:
            instance.encode(profiles=added_profiles)
        elif hasattr(instance, '_reencode'):
            instance.encode()

        removed_profiles = list(instance._profiles.difference(kwargs['pk_set']))
        if removed_profiles:
            from .models import RemoteStorage
            from .tasks import delete_media
            media_type = ContentType.objects.get(app_label='multimedia',
                                                 model=instance.model_name)
            for profile_id in removed_profiles:
                try:
                    storage = RemoteStorage.objects.get(content_type__pk=media_type.id,
                                                        media_id=instance.id,
                                                        profile_id=profile_id)
                except RemoteStorage.DoesNotExist:
                    pass
                else:
                    delete_media.delay(storage.id)
