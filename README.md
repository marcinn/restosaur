# restosaur

![Tests](https://github.com/restosaur/restosaur/actions/workflows/django.yml/badge.svg?branch=0.7)
![WheelBadge](https://img.shields.io/pypi/wheel/restosaur.svg)
![PythonBadge](https://img.shields.io/pypi/pyversions/restosaur.svg)
![StatusBadge](https://img.shields.io/pypi/status/restosaur.svg)
![LicenseBadge](https://img.shields.io/pypi/l/restosaur.svg)


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

## Documentation & development

* RTD: http://restosaur.readthedocs.io/en/0.7/
* Support & community: https://groups.google.com/forum/#!forum/restosaur-users 
* Development: https://restosaur.slack.com/

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

  * Add `restosaur.contrib.django` to `INSTALLED_APPS` in your `settings` module.
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

@post_list.get()  # GET-only callback
def post_list_view(context):
    return context.OK(Post.objects.all())  # 200 OK response


@post_detail.get()  # POST-only callback
def post_detail_view(context, pk):
    return context.OK(get_object_or_404(Post, pk=pk))
```

Callbacks are returing objects (models) and Restosaur will automatically
create their representations dependend on negotiated content type.

The conversion must be defined explicitely per content type. This can be
done depending on your needs:

* as a resource-only related representation,
* as an API wide representation,
* as a default representation for a content type (independent from object/model).

The order of conversion is as follows:

* model/object representation defined for the resource (incl.
  model's MRO),
* model/object representation defined for the API (incl. model's MRO),
* default representation for the resource,
* default representation for the API.

In this short example the model/object representation for the API was
used. The code can be placed near API initialization, and should look like:

```python

# register API-wide representation factories

from django.db.models import Model
from django.db.models.query import QuerySet
from django.forms import model_to_dict as django_model_to_dict


def queryset_to_dict(qs, ctx):
    return {
        'items': list(map(ctx.transform, qs)),
    }


def model_to_dict(instance, ctx):
    return django_model_to_dict(instance)


api.add_model_representation(
    Model, model_to_dict, 'application/json')
    
api.add_model_representation(
    QuerySet, queryset_to_json, 'application/json') 
```

### Start your server

```python manage.py runserver```

And browse your posts via http://localhost:8000/posts

### What's happened?

* You've just created simple API with two resources (blog post collection and blog post detail)
* Your API talks using `application/json` content type (the default)
* You've defined simple representation of blog post model (`restosaur` can work with any object - it depends on your needs)
* You've created minimal dependencies to Django by encapsulating it's helpers in one module `webapi.py` (it is a good strategy to embed API-related tools within this base module)
* You've created no dependencies (!) to `restosaur` in your app module


## Compatibility

* Django 1.x (deprecated)
* Django 2.x
* Django 3.x
* Django 4.x

* Python 2.7 (deprecated)
* Python 3.4
* Python 3.5
* Python 3.6
* Python 3.7
* Python 3.8
* Python 3.9

## Roadmap

* 0.7 (beta) - stabilize representations and services API, remove obsolete code; better test coverage, **Python 3.x**, **Django as an optional adapter**, **Flask adapter**
* 0.8 (beta) - add wsgi interface, code cleanup, `contrib.apibrowser`, ~move django adapter to `restosaur.contrib`~
* 0.9 (beta) - [proposal/idea] support for predicates
* ~0.10 (beta) - Python 3.x support~
* 1.0 (final) - stable API, ~100% test coverage, adapters for common web frameworks, Py2/Py3, complete documentation

## Changelog

0.7.0:
  * Python 3.x support
  * Django support - `restosaur.contrib.django` (optional)
  * Flask support - `restosaur.contrib.flask` (optional)
  * Added simple conditions to `restosaur.contrib.apiroot`
  * Extended interface for URLs generation
  * Introduced API-wide representations registry
  * Content negotiation fixes
  * Support for qvalue in content-negotiation
  * Media-type based negotiation for services (controllers)
  * New model<->resource linking interface
  
0.6.7:
 * make QueryDict more dict-like object

0.6.6:
 * support for multivalued GET parameters

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
