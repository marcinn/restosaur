from restosaur.contrib.django import API

api = API("api")
root = api.resource("/")
some = api.resource("some")
subsome = api.resource("some/sub")


@root.get()
def root_view(ctx):
    return ctx.Response({"root": "ok"})


@some.get()
def some_view(ctx):
    return ctx.Response({"some": "ok"})


@subsome.get()
def subsome_view(ctx):
    return ctx.Response({"some/sub": "ok"})


urlpatterns = api.urlpatterns()
