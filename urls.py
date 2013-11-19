from django.conf.urls import patterns, include, url
#from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.simple import direct_to_template


urlpatterns = patterns('',
    # Examples:
    url(r'^$', direct_to_template, {
        'template': 'pv/index.html'
        },name='index'),
    url(r'^api/parcel/(?P<county>.+)/(?P<apn>\d+)/$', 'peevee.views.parcel_request', name='getparcel'),
    url(r'^api/parcel/$', 'peevee.views.parcel_request', name='getparcel'),
    url(r'^api/zoning/$', 'peevee.views.zoning_request', name='getzoning'),
    url(r'^api/search/$', 'peevee.views.search_request', name='search'),

    # url(r'^masterblaster/', include('masterblaster.foo.urls')),

)

#urlpatterns += staticfiles_urlpatterns()
