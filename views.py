from peevee.models import County, Parcel, GenericZone, ZoneLookup
#from coverages.views import get_coverage_geo
from django.forms.models import model_to_dict
from django.contrib.gis.geos import Point
from django.http import HttpResponse, HttpResponseNotModified, HttpResponseServerError, Http404, HttpResponseBadRequest
from django.shortcuts import render_to_response, render
from django.views.decorators.gzip import gzip_page
from peevee.utils import hasKeys
import json
import re

RE_APN = re.compile('^(\d{1,3}-?){1,4}$')

class Benchmark_ADDRSEARCH():
	def setUp(self):
		self.queries = list('' + (random() % 1000) + ' ' + chr(random() % 26 + 65) for x in range(1000))
		
	def test_icontains(self):
		for q in query:
			parcel = Parcel.objects.filter(saddr1__contains = q).get()
	
	def test_startswith(self):
		for q in query:
			parcel = Parcel.objects.filter(saddr1__startswith = q).get()
	
	def fulltext(self):
		idx = "to_tsvector('english', saddr1 || ' ' || saddr2)"
		for q in query:
			parcel = Parcel.objects.extra(
				select   = {'rank': 'ts_rank_cd(' + idx + ', plainto_tsquery(%s))'},
				where    = [idx + ' @@ plainto_tsquery(%s)'],
				order_by = '-rank',
				params   = [q]
			)

def bench(request):
	benchmark.main(Benchmark_ADDRSEARCH)

def index(request):
    extent = County.objects.transform(4326).extent()
    return render(request, 'pv/index.html', {
        'extent': list(extent)
    })

def parcel_request(request):
    # Find the parcel in question
    get = request.GET
    if hasKeys(get, ('lat', 'lon')):
        point  = Point(float(get['lon']), float(get['lat']), srid = 4326)
        parcel = Parcel.objects.by_point(point)[:1].get()
    elif hasKeys(get, ('fips', 'id')):
        parcel = Parcel.objects.by_unique(get['fips'], get['id'])[:1].get()
    else:
        return HttpResponseBadRequest('Bad Request')
    
    if not parcel:
        # Couldn't find it.  Sorry!
        return HttpResponse(json.dumps({}), mimetype="application/json")
    
    # Get it in PyGeoJSON
    obj = parcel.to_pygeojson(
        authenticated = request.user.is_authenticated(),
        clickpoint    = vars().get('point')
    )
    
    return HttpResponse(json.dumps(obj), mimetype="application/json")

def zoning_request(request):
    obj = {}
    zone = None
    get = request.GET
    if hasKeys(get, ('lat', 'lon')):
        pt = Point(float(get['lon']), float(get['lat']), srid=4326)
        zone = getzoning(pt)
    elif hasKeys(get, ('apn', 'county')):
        parcel = getparcelgeo(get['apn'], get['county'])
        if parcel:
            zone = getzoning(parcel.geom.centroid)
    else:
        return HttpResponseBadRequest('Bad Request')
    if zone:
        obj = {'zone': {'name':zone.name, 'desc':zone.description}}
    return HttpResponse(json.dumps(obj), mimetype="application/json")

def getzoning(point):
    sources = ZoneLookup.objects.all().order_by("priority")
    for source in sources:
        setzoningto(source)
        if GenericZone.objects.filter(geom__contains = point):
            return GenericZone.objects.filter(geom__contains = point)[0]

def setzoningto(source):
    GenericZone._meta.db_table = source.table
    GenericZone._meta.get_field('id').column = source.id_field
    GenericZone._meta.get_field('name').column = source.name_field
    GenericZone._meta.get_field('description').column = source.description_field
    GenericZone._meta.get_field('geom').column = source.geom_field
    GenericZone._meta.get_field('geom').srid = source.srid
    
@gzip_page
def search_request(request):
    try:
        q = request.GET['q']
    except KeyError:
        return HttpResponseBadRequest()
    if len(q) < 3 :
        return HttpResponse(json.dumps({}), mimetype="application/json")
    
    results = search(q, auth=request.user.is_authenticated())
    datums = []
    
    for key in results.keys():
        for parcel in results[key]:
            datums.append(parcel.to_pyjson(
                authenticated = request.user.is_authenticated(),
                match         = key
            ))
    
    return HttpResponse(json.dumps(datums), mimetype="application/json")


def search(q, auth=False):
    # Search by address
    addresses = Parcel.objects.filter(saddr1__icontains = q)[:20]
    
    # And by APN, if we think it is one
    if re.search(RE_APN, q):
        apns = Parcel.objects.by_apn(q)[:20]
    else:
        apns = []
    
    # And by name, if you're a Pro
    if auth:
        names = Parcel.objects.filter(owner__icontains = q)[:20]
    else:
        names = []
    
    # Limit it to twenty results tops
    hits = len(apns) + len(addresses) + len(names)
    if hits > 20:
        scale = 20.0/hits
        apns = apns[:(int(scale*len(apns)))]
        addresses = addresses[:(int(scale*len(addresses)))]
        names = names[:(int(scale*len(names)))]
    
    return {
        'apn':     apns,
        'address': addresses,
        'name':    names
    }
