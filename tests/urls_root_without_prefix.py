from restosaur.contrib.django import JsonAPI

api = JsonAPI()
root = api.resource('/')


@root.get()
def root_view(ctx):
    return ctx.Response({'root': 'ok'})


urlpatterns = api.urlpatterns()
