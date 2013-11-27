from django.test.simple import DjangoTestSuiteRunner
from django.contrib.gis.geos import Point

testpoint = Point(-122.5, 40.5, srid=4326)

def hasKeys(dic, keys):
    return all (k in dic for k in keys)

def dashit(original, positions):
    for pos in positions:
        if len(original) > pos:
            original = original[:pos] + '-' + original[pos:]
    return original

def apn_queries(apn):
    #returns a list of apn queries to try
    # shasta: NNN-NNN-NNN-NNN
    # sisjkiyou: NNN-NNN-NNN-???
    # tehama: NNN-NNN-NN-N-??
    # butte: NNN-NNN-NNN-???

    # ZERO PADDING ISN'T DIALED YET but you'll get the idea

    queries = []
    if not '-' in apn:
        #insert dashes where they make sense
        queries = [dashit(apn,(3,7,11))]
        if len(apn) > 5:
            queries.append( dashit(apn,(3,6,10)) )
        return queries
    groups = apn.split('-')
    groups+=[None]*(4-len(groups))
    # first group is always 3 chars
    queries = (groups[0].zfill(3) + '-',)

    # second group can be 2 or 3 chars

    if groups[1]:
        t = groups[1]
        # 0 chars, aka '123-' , we're done
        if len(t) == 0:
            substrings = ('',)
        # 1 char given, can be N** or 0N or 0*N
        elif len(t) == 1:
            if groups[2] is not None: #trailing slash
                substrings = (t.zfill(2) + '-', t.zfill(3) + '-')
            else:
                substrings = (t, t.zfill(2), t.zfill(3))
        # 2 chars given, can be NN* or 0NN
        elif len(t) == 2:
            if groups[2] is not None: #trailing slash
                substrings = (t + '-', t.zfill(3) + '-')
            else:
                substrings = (t, t.zfill(3))
        # 3 chars given, can only b NNN
        elif len(t) == 3:
            substrings = (t + '-',)
        # 4+ chars given, invalid so pass on the full query 
        else:
            return (apn,)

        prevquery = queries[0] # only one
        queries = []
        for string in substrings: 
            queries.append( '%s%s' % (prevquery, string))
     
    # third group is 3 chars
    # some apns end at 3rd group so no trailing dashes

    if groups[2]:
        t = groups[2]
        # 0 chars, aka '123-' , we're done
        if len(t) == 0:
            return queries
        # 1 or 2 chars given, can be N(N)*  or 0(N)N
        elif len(t) < 3:
            if groups[3] is not None: #trailing slash
                substrings = (t.zfill(3),)
            else:
                substrings = (t, t.zfill(3))
        # 3 chars given, must be NNN 
        elif len(t) == 3:
            substrings = (t, )
        # 4+ chars given, invalid so pass on the full query 
        else:
            return (apn,)

        prevqueries = queries[:] #copy 
        queries = []
        for string in substrings: 
            for prevquery in prevqueries:
                queries.append('%s%s' % (prevquery, string))
            
    # fourth group is 3 chars

    if groups[3]:
        t = groups[3]
        # 0 chars, aka '123-' , we're done
        if len(t) == 0:
            return queries
        # 1 or 2 chars given, can be N(N)*  or 0(N)N
        elif len(t) < 3:
            substrings = (t, t.zfill(3))
        # 3 chars given, must be NNN 
        elif len(t) == 3:
            substrings = (t, )
        # 4+ chars given, invalid so pass on the full query 
        else:
            return (apn,)

        prevqueries = queries[:] #copy 
        queries = []
        for string in substrings: 
            for prevquery in prevqueries:
                queries.append('%s-%s' % (prevquery, string))

    return queries

class ManagedModelTestRunner(DjangoTestSuiteRunner):
    """
    Test runner that automatically makes all unmanaged models in your Django
    project managed for the duration of the test run, so that one doesn't need
    to execute the SQL manually to create them.
    """
    def setup_test_environment(self, *args, **kwargs):
        from django.db.models.loading import get_models
        self.unmanaged_models = [m for m in get_models()
                                 if not m._meta.managed]
        for m in self.unmanaged_models:
            m._meta.managed = True
        super(ManagedModelTestRunner, self).setup_test_environment(*args,
                                                                   **kwargs)

    def teardown_test_environment(self, *args, **kwargs):
        super(ManagedModelTestRunner, self).teardown_test_environment(*args,
                                                                      **kwargs)
        # reset unmanaged models
        for m in self.unmanaged_models:
            m._meta.managed = False
