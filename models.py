from django.contrib.gis.db import models
from django.forms.models import model_to_dict
from peevee.managers import ParcelManager
import decimal
import json

class County(models.Model):
    class Meta:
        db_table = 'pv"."counties'
        managed = False
    
    objects = models.GeoManager()
    
    fips = models.CharField(max_length = 5, primary_key = True)
    geom = models.MultiPolygonField(srid = 4269)
    name = models.CharField(max_length = 100)

class Parcel(models.Model):
    county = models.ForeignKey(County, db_column = 'source_fips')
    apn = models.BigIntegerField(primary_key=True) #this could blow up!
    geom = models.MultiPolygonField(srid = 4269)
    source_fips = models.CharField(max_length=255)
    source_id = models.IntegerField()
    land_value = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    improvement_value = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    other_value = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    use_code = models.CharField(max_length=255, null=True)
    use_description = models.CharField(max_length=255, null=True)
    right_of_way = models.BooleanField()
    acres = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    owner = models.CharField(max_length=255, null=True)
    saddr1 = models.CharField(max_length=255, null=True)
    saddr2 = models.CharField(max_length=255, null=True)
    maddr1 = models.CharField(max_length=255, null=True)
    maddr2 = models.CharField(max_length=255, null=True)

    objects = ParcelManager()

    class Meta:
        managed = False
        db_table = 'parcels"."master'
    
    def saddr(self, format=None):
        if format == 'html':
            return "%s<br>%s" % (self.saddr1, self.saddr2)
        if format == 'plain':
            return "%s\n%s" % (self.saddr1, self.saddr2)
        return "%s %s" % (self.saddr1, self.saddr2)

    def maddr(self, format=None):
        if format == 'html':
            return "%s<br>%s" % (self.maddr1, self.maddr2)
        if format == 'plain':
            return "%s\n%s" % (self.maddr1, self.maddr2)
        return "%s %s" % (self.maddr1, self.maddr2)
        
    def pretty_apn(self):
        return "%03i-%03i-%03i-%03i" % (
            self.apn / 1000000000,
            self.apn / 1000000 % 1000,
            self.apn / 1000 % 1000,
            self.apn % 1000
        )

    def to_dict(self, **kwargs):
        result = {
            'apn':    self.pretty_apn(),
            'county': self.county.name,
            'fips':   self.source_fips,
            'id':     self.source_id,
            'owner':  self.owner,
            'saddr1': self.saddr1,
            'saddr2': self.saddr2
        }
        
        if kwargs.get('match'):
            result['match'] = kwargs['match']
        if kwargs.get('authenticated'):
            result['pro'] = {
                'maddr1': self.maddr1,
                'maddr2': self.maddr2
            }
        
        return result
    
    def to_pygeojson(self, **kwargs):
        ''' returns geojson as python objects '''
        result = {
            'type':       'Feature',
            'properties': self.to_dict(**kwargs),
            'geometry':   json.loads(self.geom.json)
        }
        
        # Pick a pretty display point
        if self.geom.contains(self.geom.centroid) :
            result['properties']['marker'] = {
                'lat': self.geom.centroid.y,
                'lon': self.geom.centroid.x
            }
        elif kwargs.get('clickpoint'):
            point = kwargs.get('clickpoint')
            result['properties']['marker'] = {
                'lat': point.y,
                'lon': point.x
            }
        else:
            result['properties']['marker'] = {
                'lat': self.geom.point_on_surface.y,
                'lon': self.geom.point_on_surface.x
            }
        
        return result
        
    def to_pyjson(self, **kwargs):
        '''Return this model as a Typeahead response.'''
        result = self.to_dict(**kwargs)
        result['tokens'] = [self.pretty_apn()]
        result['value']  = "%s - %s - %s %s" % (
            self.pretty_apn(),
            self.county.name,
            self.saddr1 or '[no address]',
            self.saddr2 or ''
        )
        
        return result
        
class GenericZone(models.Model):
    geom = models.GeometryField()
    name = models.CharField(max_length=255)
    description = models.TextField()
    objects = models.GeoManager()

    class Meta:
        managed = False
        db_table = ''

class ZoneLookup(models.Model):
    #geom = models.MultiPolygonField()
    table = models.CharField(max_length=100)
    id_field = models.CharField(max_length=100)
    name_field = models.CharField(max_length=100)
    description_field = models.CharField(max_length=100)
    geom_field = models.CharField(max_length=100)
    srid = models.IntegerField()
    priority = models.IntegerField()

