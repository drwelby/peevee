from django.conf.urls import patterns, include, url
#from django.contrib.staticfiles.urls import staticfiles_urlpatterns
#from django.views.generic.simple import direct_to_template
from django.views.generic import TemplateView

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'peevee.views.index', name='index'),
    url(r'^api/parcel/(?P<county>.+)/(?P<apn>\d+)/$', 'peevee.views.parcel_request', name='getparcel'),
    url(r'^api/parcel/$', 'peevee.views.parcel_request', name='getparcel'),
    url(r'^api/zoning/$', 'peevee.views.zoning_request', name='getzoning'),
    url(r'^api/search/$', 'peevee.views.search_request', name='search'),
    url(r'^api/bench/$', 'peevee.views.bench', name='bench'),
    # url(r'^masterblaster/', include('masterblaster.foo.urls')),

)

#urlpatterns += staticfiles_urlpatterns()
