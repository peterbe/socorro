from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url('^$',
        views.home,
        name='home'),
    url('^featured-versions/$',
        views.featured_versions,
        name='featured_versions'),
    url('^featured-versions/update/$',
        views.update_featured_versions,
        name='update_featured_versions'),
    url('^fields/$',
        views.fields,
        name='fields'),
    url('^fields/lookup/$',
        views.field_lookup,
        name='field_lookup'),
    url('^skiplist/$',
        views.skiplist,
        name='skiplist'),
    url('^skiplist/add/$',
        views.skiplist_add,
        name='skiplist_add'),
    url('^skiplist/data/$',
        views.skiplist_data,
        name='skiplist_data'),
    url('^skiplist/delete/$',
        views.skiplist_delete,
        name='skiplist_delete'),
)
