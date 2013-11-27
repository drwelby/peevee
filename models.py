from django.contrib.gis.db import models
from django.forms.models import model_to_dict
import decimal
import json

class Parcels(models.Model):
    apn = models.BigIntegerField(primary_key=True) #this could blow up!
    apn_text = models.CharField(max_length=25)
    apn_index = models.CharField(max_length=50)
    geom = models.MultiPolygonField()
    source_name = models.CharField(max_length=255)
    source_id = models.IntegerField()
    land_value = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    improvement_value = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    use_code = models.CharField(max_length=255, null=True)
    use_description = models.CharField(max_length=255, null=True)
    right_of_way = models.BooleanField()
    community = models.CharField(max_length=255, null=True)
    owner = models.CharField(max_length=255, null=True)
    saddr1 = models.CharField(max_length=255, null=True)
    saddr2 = models.CharField(max_length=255, null=True)
    maddr1 = models.CharField(max_length=255, null=True)
    maddr2 = models.CharField(max_length=255, null=True)

    objects = models.GeoManager()

    class Meta:
        managed = False
        db_table = 'merged'

    def scrub(self):
        #might be handy to anonymize a result?
        del self.owner
        del self.maddr1
        del self.maddr2
        
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

    def to_dict(self):
        ''' converts model object to dict with better values for nulls '''
        d = model_to_dict(self)
        del d['geom']
        del d['source_id']
        for k in d:
            if not d[k]:
                d[k] = "No Data"
            if isinstance(d[k], decimal.Decimal):
                d[k] = str(d[k])
        return d

    def to_pygeojson(self):
        ''' returns geojson as python objects '''
        return {'type':'Feature', 'properties':self.to_dict(), 'geometry':json.loads(self.geom.json)}
    
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

