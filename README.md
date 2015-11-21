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

```pip install restosaur```


## License

BSD
