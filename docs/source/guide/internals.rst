Restosaur's internals
=====================

Architecture
------------

Restosaur is a library which provides tools for implementing RESTful server
in a Python programming language. It also provides an Integration Layer
which connects Restosaur's internals to existing web frameworks through a
Web Framework Adapters.

The process of adaptation transforms original HTTP requests into
internal Context objects, and transforms internal Response objects
into web framework HTTP responses. Web Framework Adapter connetcs URLs
and HTTP callbacks to the framework's routing system (just once at the
startup stage).


.. image:: img/restosaur-architecture.png


The Context
-----------

A ``Context`` is a class which represents a HTTP request data. It is similar
to request objects of web frameworks, but may mutate during
dispatching. In such cases it may not be identical to a HTTP request.
That's why it is named differently.

A Context object holds an original request object, reference to the API
instance, matched resource object, normalized headers, normalized HTTP method
name, GET, POST and FILES parameters, and of course the payload of the request
(raw and deserialized).

The context instance is passed to every object during dispatch process, so
every part of a pipeline can access not only for request data, but also
for proper API and resource instances.

Context class defines handy response factories (shortcuts).

Resources
---------

Resource is an object, which manages one and the only one unique URI,
and allows clients to read and modify it's state.

A resource instance can handle GET, POST, PUT, PATCH, DELETE and OPTIONS
methods. By default there are no callbacks registered. If no callback is
registered for a requested method, the ``405 Method Not Allowed`` response
will be automatically generated.

A method callbacks are similar to controllers or views, known well from MVC
or MVT paradigms, and they must always return a Response instance.


Responses
---------

Responses are objects which holds information required to generate final
HTTP response. They holds a HTTP response code, context instance,
response HTTP headers, response content type and optional resource state
object.

Restosaur defines common types of responses:

=========================================== =========================== ====
              Class                         Context shortcut            Code
=========================================== =========================== ====
  responses.OKResponse                      ctx.OK()                    200
  responses.CreatedResponse                 ctx.Created()               201
  responses.NoContentResponse               ctx.NoContent()             204
  responses.SeeOtherResponse                ctx.SeeOther(uri)           303
  responses.NotModifiedResponse             ctx.NotModified()           304
  responses.BadRequestResponse              ctx.BadRequest()            400
  responses.UnauthorizedResponse            ctx.Unauthorized()          401
  responses.ForbiddenResponse               ctx.Forbidden()             403
  responses.NotFoundResponse                ctx.NotFound()              404
  responses.MethodNotAllowedResponse        ctx.MethodNotAllowed()      405
  responses.NotAcceptableResponse           ctx.NotAcceptable()         406
  responses.UnsupportedMediaTypeResponse    ctx.UnsupportedMediaType()  415
  responses.InternalServerErrorResponse     ctx.InternalServerError()   500
  responses.NotImplementedResponse          ctx.NotImplemented()        501
=========================================== =========================== ====


API objects
-----------


Web Framework Adapters
----------------------

Data flow
---------

.. note::
    The facts worth remembering:

    * HTTP callbacks are responsible for reading and changing a resource state.
    * Representation factories are responsible for transforming the state
      into transport structure.

Let's assume you have a ``Car`` class
and a ``car_detail`` resource, which is responsible for managing
a single car identitfied by ``plate_number``. A ``GET`` method callback
of the resource is responsible for reading a ``Car`` state from the database.
The resource has a registered representation for an
``application/json`` type and a ``Car`` class, which is responsible
for translating ``Car`` instance into pure Python's dict.

When client requests a details of a car, in a ``application/json`` format,
a ``GET`` callback is called. After handling a HTTP method Restosaur
begins a content negotiation procedure. The ``application/json``
callback is found as the best matching and ``Car`` translates into a dict.
Then a dict object is simply serialized for a streaming.


