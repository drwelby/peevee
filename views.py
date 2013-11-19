from peevee.models import Parcels, GenericZone, ZoneLookup
from coverages.views import get_coverage_geo
from django.forms.models import model_to_dict
from django.contrib.gis.geos import Point
from django.http import HttpResponse, HttpResponseNotModified, HttpResponseServerError, Http404, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.views.decorators.gzip import gzip_page
from utils import hasKeys
import json
import re

sources = {
        'siskiyou': 'siskiyouco',
        'butte': 'butteco',
        'shasta': 'shastaco',
        'tehama': 'tehamaco',
        }

counties = {sources[key]:key for key in sources}

RE_APN = re.compile('^\d[\d-]*$')

def parcel_request(request, apn=None, county=None):
    parcel = None
    pt = None
    zoom = False
    get = request.GET
    if hasKeys(get, ('lat','lon')):
        pt = Point(float(get['lon']), float(get['lat']), srid=4326)
        parcels = getparcelsgeo(pt)
        if parcels:
            parcel = parcels[0]
    elif hasKeys(get, ('apn','county')):
        parcel = getparcelapn(get['apn'], get['county'])
        zoom = True
    elif (apn and county):
        parcel = getparcelapn(apn, county)
    else:
        return HttpResponseBadRequest('Bad Request')
    if parcel is None:
        return HttpResponse(json.dumps({}), mimetype="application/json")
    if not request.user.is_authenticated():
        obj = parcel.to_pygeojson()
        # maybe scrub out some fields we don't want to leak
        del obj['properties']['maddr1']
        del obj['properties']['maddr2']
        del obj['properties']['right_of_way']
    else:
        obj = parcel.to_pygeojson()
        del obj['properties']['right_of_way']
        #add any pro stuff here
    zone = getzoning(parcel.geom.centroid)
    if zone:
        obj['properties']['zone'] = zone.name
    else:
        obj['properties']['zone'] = 'No Data'
    coverages = get_coverage_geo(pt)
    obj['properties']['coverages'] = coverages
    if parcel.geom.contains(parcel.geom.centroid) :
        obj['properties']['marker'] = {
                'lat': parcel.geom.centroid.y,
                'lon': parcel.geom.centroid.x
                }
    elif pt:
        obj['properties']['marker'] = {
                'lat': pt.y,
                'lon': pt.x
                }
    else:
        obj['properties']['marker'] = {
                'lat': parcel.geom.point_on_surface.y,
                'lon': parcel.geom.point_on_surface.x
                }
    if zoom:
        obj['properties']['zoom'] = 'true'
    if apn and county:
        return render_to_response('pv/parcel.html', {'obj':obj})
        
    return HttpResponse(json.dumps(obj), mimetype="application/json")

def getparcelapn(apn, county):
    try:
        source = sources[county.lower()]
    except KeyError:
        return None
    parcels = Parcels.objects.filter(apn=apn).filter(source_name=source)
    if parcels:
        return parcels[0]

def getparcelsgeo(geom):
    parcels = Parcels.objects.filter(geom__contains = geom)
    return parcels

def zoning_request(request):
    obj = {}
    zone = None
    get = request.GET
    if hasKeys(get, ('lat','lon')):
        pt = Point(float(get['lon']), float(get['lat']), srid=4326)
        zone = getzoning(pt)
    elif hasKeys(get, ('apn','county')):
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
    for parcel in results['apn']:
        datum = {
            'value': "#%s (%s) - %s %s" % (
                parcel.apn,
                counties[parcel.source_name].title(),
                parcel.saddr1,
                parcel.saddr2
                ),
            'show': "<b>#%s</b> (%s) - %s %s" % (
                parcel.apn,
                counties[parcel.source_name].title(),
                parcel.saddr1,
                parcel.saddr2
                ),
            'apn': parcel.apn,
            'tokens': [q],
            'county': counties[parcel.source_name]
            }
        datums.append(datum)
    for parcel in results['address']:
        datum = {
            'value': "#%s (%s) - %s %s" % (
                parcel.apn,
                counties[parcel.source_name].title(),
                parcel.saddr1,
                parcel.saddr2
                ),
            'show': "#%s (%s) - <b>%s %s</b>" % (
                parcel.apn,
                counties[parcel.source_name].title(),
                parcel.saddr1,
                parcel.saddr2
                ),
            'tokens': [q],
            'apn': parcel.apn,
            'county': counties[parcel.source_name]
            }
        datums.append(datum)
    if 'name' in results:
        for parcel in results['address']:
            datum = {
                'value': parcel.owner,
                'tokens': [q],
                'apn': parcel.apn,
                'county': counties[parcel.source_name]
                }
            datums.append(datum)
    return HttpResponse(json.dumps(datums), mimetype="application/json")


def search(q, auth=False):
    results = {}
    names = []
    if re.search(RE_APN, q):
        if q[0] == '0':
            q = q[1:]
        if '-' in q:
            q = q.replace('-','')
        apns = Parcels.objects.filter(apn__startswith=q)[:20]
    else:
        apns = []
    q = q.lower()
    addresses = Parcels.objects.filter(saddr1__icontains=q)[:20]
    if auth:
        names = Parcels.objects.filter(owner__icontains=q)[:20]
    hits = len(apns) + len(addresses) + len(names)
    if hits > 20:
        scale = 20.0/hits
        apns = apns[:(int(scale*len(apns)))]
        addresses = addresses[:(int(scale*len(addresses)))]
        names = names[:(int(scale*len(names)))]
    results['apn'] = apns
    results['address'] = addresses
    if auth:
        results['name'] = names
    return results
