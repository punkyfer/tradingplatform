from django.contrib import admin

# Register your models here.
from .models import Author, Genre, Book, BookInstance

#admin.site.register(Book)
#admin.site.register(Author)
admin.site.register(Genre)
#admin.site.register(BookInstance)
class BookInline(admin.TabularInline):
  model = Book

# Define admin class
class AuthorAdmin(admin.ModelAdmin):
  list_display = ('last_name', 'first_name', 'date_of_birth', 'date_of_death')
  fields = ['first_name', 'last_name', ('date_of_birth', 'date_of_death')]
  inlines = [BookInline]


class BookInstanceInline(admin.TabularInline):
  model = BookInstance

# Register the admin classes for books using the decorator
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
  list_display = ('title', 'author', 'display_genre')
  inlines = [BookInstanceInline]

@admin.register(BookInstance)
class BookInstanceAdmin(admin.ModelAdmin):
  list_display = ('book', 'status', 'due_back', 'id')
  list_filter = ('status', 'due_back')

  fieldsets = (
    (None, {
      'fields':('book', 'imprint', 'id')
      }),
    ('Availability', {
      'fields':('status', 'due_back')
      }),
    )

# Register the admin class with the associated model
admin.site.register(Author, AuthorAdmin)