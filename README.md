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

api = restosaur.API()
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

For Django <1.7 you must call `autodiscover` explicitely, for example in `urls.py`:

```python
from django.conf.urls import url
from webapi import api
 
import restosaur
restosaur.autodiscover()

# ... rest of urls.py file...
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
    return context.Response(Post.objects.all())  # 200 OK response


@post_detail.get()
def post_detail_view(context, pk):
    return context.Response(get_object_or_404(Post, pk=pk))


# register representation factories

@post_detail.representation()
def post_as_dict(post, context):
    return {
            'id': post.pk,
            'title': post.title,
            'content': post.content,
            # create link (URI) to this object
            'href': context.url_for(post_detail, pk=post.pk),
            }


@post_list.representation()
def posts_list_as_dict(posts, context):
    return {
            'posts': [post_as_dict(post, context) for post in posts]
        }
```

### Start your server

```python manage.py runserver``

And browse your posts via http://localhost:8000/posts

### What's happened?

* You've just created simple API with two resources (blog post collection and blog post detail)
* Your API talks using `application/json` content type (the default)
* You've defined simple representation of blog post model (`restosaur` can work with any object - it depends on your needs)
* You've created minimal dependencies to Django by encapsulating it's helpers in one module `webapi.py` (it is a good strategy to embed API-related tools within this base module)
* You've created no dependencies (!) to `restosaur` in your app module


## Compatibility

* Django 1.6
* Django 1.7
* Django 1.8
* Django 1.9
* Django 1.10 (beta 1)
* Python 2.7

## Roadmap

* 0.7 (beta) - stabilize representations and services API, remove obsolete code; better test coverage
* 0.8 (beta) - add wsgi interface and move django adapter to `restosaur.contrib`
* 0.9 (beta) - [proposal/idea] support for predicates
* 0.10 (beta) - Python 3.x support
* 1.0 (final) - stable API, ~100% test coverage, adapters for common web frameworks, Py2/Py3, complete documentation

## Changelog

0.6.5:
 * support for Django 1.10b1

0.6.4: 
 * fix registering API to root path ("/")
 * make API`s path optional
 * run autodisovery automatically via Django` AppConfig (Django 1.7+)
 * add settings for enabling or disabling autodiscovery and autodiscovery module name
 
0.6.3:
 (INVALID RELEASE)
 
0.6.2:
 * (contrib.apiroot) add possibiliy to autoregister apiroot view to specified resource
 
0.6.1:
 * fix loading modules
 
0.6.0:
 * add `contrib.apiroot` module
 * Resource `expose` and `name` arguments deprecation 

0.5.6:
 * fix double slashes problem
 
0.5.5:
 * add internal error messages

0.5.0 and ealier are too old to mention them here.

## License

BSD
