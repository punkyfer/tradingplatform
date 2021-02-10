from django.shortcuts import render

# Create your views here.
from .models import Book, BookInstance, Author, Genre

def index(request):
  """
  View function for homepage of site
  """
  # Generate counts of some of the main objects
  num_books = Book.objects.all().count()
  num_instances = BookInstance.objects.all().count()
  # Available books (status = 'a')
  num_instances_available = BookInstance.objects.filter(status__exact='a').count()
  num_authors = Author.objects.count()
  num_genres = Genre.objects.count()
  num_books_with_word = Book.objects.filter(title__icontains="book").count()

  # Render the HTML template index.html with the data in the context variable
  return render(
    request, 
    'index.html',
    context = {'num_books':num_books, 'num_instances':num_instances, 
      'num_instances_available':num_instances_available, 'num_authors':num_authors, 
      'num_genres':num_genres, 'num_books_with_word': num_books_with_word }
  )


from django.views import generic

class BookListView(generic.ListView):
  model = Book

  def get_context_data(self, **kwargs):
    # Call the base implementation first to get the context
    context = super(BookListView, self).get_context_data(**kwargs)
    # Create any data and add it to the context
    context['some_data'] = "This is just some data"
    return context

  context_object_name = "my_book_list"
  queryset = Book.objects.filter(title__icontains="book")[:3] # Get 3 books containing the title 'book'
  template_name = 'books/my_arbitrary_template_name_list.html' # Maybe change this name


class BookDetailView(generic.DetailView):
  model = Book