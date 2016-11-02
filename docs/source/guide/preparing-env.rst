Preparing the environment
=========================

Initializing the API instance
-----------------------------

Restosaur is designed to support multi-apps project, so at least one API
instance is required to start working with the library.

There is no special place nor style to do it, but a common practice is
to create a decicated module or package with your's API internals. The
typical name is just ``webapi.py``. The only one requirement is that your
module/package must be importable.

The ``restosaur`` package contains common objects imported to it's
namespace. This is a top level interface of a package. In most cases you'll
need just one import, or just few flat-style imports
directly from ``restosaur``. A rare exceptions are related to a contrib
packages.

.. note::

    It is very handy to make your ``webapi`` module/package a top-level
    interface of the API. Just import there common objects from a ``restosaur``
    namespace and define or import custom helpers. 
    
    The common rule of thumb is to avoid direct imports from a
    ``restosaur`` namespace in a rest of your code.


Let's make an API instance by importing adequate class. For Django it
will be ``restosaur.contrib.django.API``::

    from restosaur.contrib.django import API

    webapi = API('api')


The ``webapi`` object holds now API instance, which is responsible
mostly for managing the API resources, serializers registry,
models and their views registry, and configured middlewares.

The interface of an API initializer is::

    restosaur.api.API.__init__(
        path=None, middlewares=None, context_class=None,
        default_charset=None, debug=False)

path
    An URL prefix of your API instance (relative).

    Leave it empty if you want to bind the API instance
    as a root resource.

middlewares
    iterable of instantiated middlewares

context_class
    a class used by internal context factory

default_charset
    the default charset of the text/html output (default: ``utf-8``)
    
debug
    a flag that turns on debug mode


.. note::

    API instance holds no resources by default. If you want
    to make an API root view, you must create a resource
    explicitely::

        root = webapi.resource('/')


Creating a resources
--------------------


To create a resource you'll need to use a factory method::

    webapi.resource(path, *args, **kwargs)


This is a factory of the ``restosaur.resource.Resource`` class.
Resource class holds callbacks for HTTP methods and representations
registry. It describes how to read and manage the resource's state,
and how to build the state representation understandable for clients.

path
    required resource's path, relative to the API's path.

Let's create two resources, one for a list (collection) and second for
a details view::

    car_list = webapi.resource('cars')
    car_detail = webapi.resource('cars/:plate_number')


As a result a two endpoints will be available as a URL patterns (Django
example):

    * /api/cars
    * /api/cars/(?P<plate_number>\w+)

Note that no trailing slash is generated. If you need to be compatible
with Django's APPEND_SLASH setting, you must:

    * append trailing slashes explicitely in resource paths,
    * instantiate ``restosaur.contrib.django.API`` with ``append_slash``
      set to ``True``.


.. code-block:: python

    API.view(resource, view_name=None)(model_class)

A decorator which binds a model_class to the resource as a named view.
If view_name is not specified, the resource is linked to the model as
a default one.

An example::

    car_detail = webapi.resource('cars/:plate_number')

    @webapi.view(car_detail)
    class Car(object):
        def __init__(self, plate_number, name):
            self.plate_number = plate_number
            self.name = name
        

The above example creates a default :ref:`link <guide/linking>`
between ``car_detail`` resource and ``Car`` class. 

This will allow you to generate an URLs to the Car resources
in a DRY approach. Anytime you'll need to change a resource`s URI, the
linking to the model will not require a change::

    @car_detail.representation('application/json')
    def car_json(car, ctx):
        return {
            'plate_number': car.plate_number,
            'name': car.name,
            '@id': ctx.link_model(car),
        }


Handling HTTP methods
---------------------


Middlewares
-----------


