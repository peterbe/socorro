from django.contrib.auth.models import Permission, Group
from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
import django.contrib.auth.models
import django.contrib.contenttypes.models


PERMISSIONS = {
    'view_pii': 'View Personal Identifyable Information',
    'view_rawdump': 'View Raw Dumps',
    'view_exploitability': 'View Exploitability Results',
}

GROUPS = (
    ('Hackers', ('view_pii', 'view_rawdump', 'view_exploitability')),
)

# internal use to know when all interesting models have been synced
_senders_left = [
    django.contrib.auth.models,
    django.contrib.contenttypes.models
]


@receiver(post_syncdb)
def setup_custom_permissions_and_groups(sender, **kwargs):
    if _senders_left:
        if sender in _senders_left:
            _senders_left.remove(sender)

        if _senders_left:
            return
        # All the relevant senders have been sync'ed.
        # We can now use them
        appname = 'crashstats'
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label=appname,
            defaults={'name': appname}
        )
        for codename, name in PERMISSIONS.items():
            p, __ = Permission.objects.get_or_create(
                name=name,
                codename=codename,
                content_type=ct
            )

        for name, permissions in GROUPS:
            g, __ = Group.objects.get_or_create(
                name=name
            )
            for permission in permissions:
                # The add has a built-in for checking it isn't created
                # repeatedly.
                g.permissions.add(
                    Permission.objects.get(codename=permission)
                )


# double check that all groups are set up properly
for name, perms in GROUPS:
    for perm in perms:
        assert perm in PERMISSIONS, "%s not a known permission" % perm
