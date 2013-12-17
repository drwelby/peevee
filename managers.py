from django.contrib.gis.db import models
import math
import re

class ParcelManager(models.GeoManager):
    def by_address(self, address):
#        return self.get_query_set().objects.filter(saddr1__icontains = address)
        idx = "to_tsvector('usps', saddr1 || ' ' || saddr2)"
        return self.get_query_set().extra(
            where    = [idx + ' @@ plainto_tsquery(\'usps\', %s)', 'pv.counties.fips = parcels.master.source_fips'],
            tables   = ['pv"."counties'],
            params   = [address]
        )
        
    def by_apn(self, apn):
        power  = 1000000000000 # Multiplier for the current triplet
        known  = 0             # The unambiguous bit of the APN
        digits = 0             # The number of digits the last triplet
        latest = 0             # The last triplet as an integer
        
        # Read all the triplets
        for match in re.finditer('(\d{1,3})-?', apn):
            known  = known + latest * power
            power  = power / 1000
            digits = len(match.group(1))
            latest = int(match.group(1))
        
        if latest == 0:
            # Use the number of known leading zeros to limit the range
            span = 10 ** (3 - digits)
            q = models.Q(apn__range = (known, known + power * span - 1))
        elif digits == 3 or apn.endswith('-'):
            # The range is across the entire next (unseen) triplet
            known  = known + latest * power
            q = models.Q(apn__range = (known, known + power - 1))
        else:
            # Find all possible expansions of the last triplet
            q = models.Q()
            span = 1
            for i in range(4 - digits):
                flr = known + power * (latest)
                cel = known + power * (latest + span)
                q = q | models.Q(apn__range = (flr, cel - 1))
                latest = latest * 10
                span = span * 10
        
        return self.get_query_set().filter(q)
        
    def by_point(self, point):
        p = point.transform(4269, True)
        return self.get_query_set().filter(geom__contains = p)
        
    def by_unique(self, fips, id):
        return self.get_query_set().filter(source_fips = fips, source_id = id)
        
    def get_query_set(self):
        # Include the county by default - saves a bunch of queries later
        return super(ParcelManager, self).get_query_set().select_related('county')
        
    def raw(self):
        return super(ParcelManager, self).get_query_set()


