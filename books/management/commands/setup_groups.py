from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from books.models import Book, Category


class Command(BaseCommand):
    help = 'Creates the default user groups: SuperAdmin, Admin, User'

    def handle(self, *args, **kwargs):
        book_ct = ContentType.objects.get_for_model(Book)
        category_ct = ContentType.objects.get_for_model(Category)

        # Permissions
        can_add    = Permission.objects.get(codename='add_book',    content_type=book_ct)
        can_change = Permission.objects.get(codename='change_book', content_type=book_ct)
        can_delete = Permission.objects.get(codename='delete_book', content_type=book_ct)
        can_view   = Permission.objects.get(codename='view_book',   content_type=book_ct)

        # SuperAdmin — full access
        superadmin_group, created = Group.objects.get_or_create(name='SuperAdmin')
        superadmin_group.permissions.set([can_add, can_change, can_delete, can_view])
        self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Found"} group: SuperAdmin'))

        # Admin — add / change / view only
        admin_group, created = Group.objects.get_or_create(name='Admin')
        admin_group.permissions.set([can_add, can_change, can_view])
        self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Found"} group: Admin'))

        # User — view only
        user_group, created = Group.objects.get_or_create(name='User')
        user_group.permissions.set([can_view])
        self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Found"} group: User'))

        self.stdout.write(self.style.SUCCESS('\nAll groups set up successfully!'))
        self.stdout.write('Next steps:')
        self.stdout.write('  python manage.py createsuperuser')
        self.stdout.write('  Log in at /admin/ and assign users to groups.')
