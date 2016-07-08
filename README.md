# restosaur

![TravisBadge](https://travis-ci.org/marcinn/restosaur.svg?branch=master)


RESTful library for Django


## Why next REST framework?

Restosaur is not a framework. It is a library.
You get a set of tools to build your real RESTful service.


## What is the difference between Restosaur and other frameworks?

  * Can be decoupled from Django. This is a primary goal.
  * Resources aren't splitted into `list` and `detail` - everything (every URL) is a resource.
  * Provides unified way for handling HTTP headers using normalized keys
  * Provides content negotiation and multiple representations of entities
  * It's flexible - callbacks are simple functions and can be registered anywhere
  * It's simple - does not require knoweldge about metaclasses, mixins nor complex inheritance.
  * Can be easily adapted to any HTTP framework


## Quickstart

### Install library

```pip install restosaur```

### Make core module for your API, for example:

Create file `<myproject>/webapi.py` which will contain base objects:

```python
import restosaur

# import handy shortcuts
from django.shortcuts import get_object_or_404  # NOQA

api = restosaur.API('api')  # url prefix will be set to `/api/`
```

### Configure Django project

  * Add `restosaur` to `INSTALLED_APPS` in your `settings` module.
  * Add to your `urls.py` API patterns:
    ```python
    from django.conf.urls import url
    from webapi import api
    
    urlpatterns = [...]
    urlpatterns += api.urlpatterns()
    ```

### Create module in one of yours Django application

Let's assume you're creating an another Blog project and the app name is called `blog`.
So create a file called `blog/restapi.py`:

```python

from webapi import api, get_object_or_404
from .models import Post

# register resources

post_list = api.resource('posts')
post_detail = api.resource('posts/:pk')


# register methods callbacks 

@post_list.get()
def post_list_view(context):
    return context.OK(Post.objects.all())  # 200 OK response


@post_detail.get()
def post_detail_view(context, pk):
    return context.OK(get_object_or_404(Post, pk=pk))


# register representation factories

@post_list.representation()
@post_detail.representation()
def simple_post_to_dict(post, context):
    return {
        'id': post.pk,
        'href': context.url_for(post_detail, pk=post.pk),
        'title': post.title,
        'content': post.content
        }
```

### Start your server

```python manage.py runserver``

And browse your posts via http://localhost:8000/api/posts

### What's happened?

* You've just created simple API with two resources (blog post collection and blog post detail)
* Your API talks using `application/json` content type (the default)
* You've defined simple representation of blog post model
* You've created minimal dependencies to Django by encapsulating it's helpers in one module `webapi.py` (it is a good strategy to embed API-related tools within this base module)

## License

BSD
