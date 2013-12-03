var parcels = {};
var map;

var infotemplate = Hogan.compile($('#tabcontent').html(), {delimiters: '[[ ]]'});
var linetemplate = '\
<div class="match-{{match}}">\
    <span class="hint-apn">{{apn}}</span>\
    -\
    <span class="hint-county">{{county}}</span>\
    -\
    {{#saddr1}}\
    <span class="hint-addr">{{saddr1}} {{saddr2}}</span>\
    {{/saddr1}}\
    {{^saddr1}}\
    <span class="hint-addr">[no address]</span>\
    {{/saddr1}}\
    {{#pro}}\
    -\
    <span class="hint-owner">{{owner}}</span>\
    {{/pro}}\
</div>\
';

$('input#searchbox').typeahead({
    engine: Hogan,
    limit: 20,
    minLength: 3,
    name: 'pv',
    remote: 'api/search/?q=%QUERY',
    template: linetemplate
});

$('#searchbox').on('typeahead:selected', function(obj, datum, name) {
    getParcel({id: datum.id, fips: datum.fips}, {zoom: true});
});

google.maps.Polygon.prototype.getBounds = function() {
    var bounds = new google.maps.LatLngBounds();
    var paths = this.getPaths();
    var path;        
    for (var i = 0; i < paths.getLength(); i++) {
        path = paths.getAt(i);
        for (var ii = 0; ii < path.getLength(); ii++) {
            bounds.extend(path.getAt(ii));
        }
    }
    return bounds;
}

function initialize () {
    // Why do we have to implement zoom limits manually?
    function genTileUrl(layer) {
        return function(ll, z) {
            if(z < this.minZoom || z > this.maxZoom) {
                return 'http://www.mapport.net/tiles/blank.png';
            }
            var s = ((ll.x + ll.y) % 4) + 1;
            return (
                "http://" + s +
                ".mapport.net:8888/geoserver/gwc/service/gmaps?layers=" + layer +
                "&zoom=" + z +
                "&x=" + ll.x +
                "&y=" + ll.y +
                "&format=image/png"
            );
        }
    }
    
    map = new google.maps.Map(document.getElementById("map"), {
        draggableCursor: 'default',
        mapTypeControl: false,
        mapTypeId: google.maps.MapTypeId.HYBRID,
        tilt: 0
    });
    
    map.overlayMapTypes.push(new google.maps.ImageMapType({
        getTileUrl: genTileUrl('pv:merged'),
        tileSize: new google.maps.Size(256, 256),
        isPng: true,
        minZoom: 15,
        maxZoom: 20,
        name: "Parcels",
        alt: "Parcel Layer"
    }));
    
    map.overlayMapTypes.push(new google.maps.ImageMapType({
        getTileUrl: genTileUrl('pv:counties'),
        tileSize: new google.maps.Size(256, 256),
        isPng: true,
        maxZoom: 20,
        name: "Counties",
        alt: "County Layer"
    }));
    
    map.overlayMapTypes.push(new google.maps.ImageMapType({
        getTileUrl: genTileUrl('pv:cities'),
        tileSize: new google.maps.Size(256, 256),
        isPng: true,
        minZoom: 10,
        maxZoom: 20,
        name: "Cities",
        alt: "City Layer"
    }));

    google.maps.event.addListener(map, 'click', function(event) {
        getParcel({
            lat: event.latLng.lat(),
            lon: event.latLng.lng()
        });
    });
    
    $('#searchbox').on('focus', function(event) {
    	$(this).select();
    });
    
    $('#find-tool').on('click', function(event) {
    	$('#searchbox').focus();
    	event.preventDefault();
    });
    
    $('#help-tool').on('click', function(event) {
    	$('#overlay').show();
    	$('#info-window').show();
    	event.preventDefault();
    });
    
    $('#info-close').on('click', function(event) {
        $('#overlay').hide();
    	$('#info-window').hide();
    	event.preventDefault();
    });
    
    // Zoom to maximum extent
    var bounds = new google.maps.LatLngBounds();
    bounds.extend(new google.maps.LatLng(extent[1], extent[0]));
    bounds.extend(new google.maps.LatLng(extent[3], extent[2]));
    map.fitBounds(bounds);
}
google.maps.event.addDomListener(window, 'load', initialize);

function getParcel(data, options) {
    $.ajax('api/parcel/', {
        data : data,
        success : function(resp, status, xhr) {
            addParcel(resp, options);
        }
    });
}
var parcelOptions = {
    "strokeColor": "#FF0000",
    "strokeOpacity": 1,
    "strokeWeight": 2,
    "fillOpacity": 0
}

function getExtra(source) {
	return '';
    //if (source=='shastaco') { return 'Extra Shasta Stuff'}
}

function addParcel(data, options) {
    
    options = options || {};
    
    var props  = data.properties;
    var apn    = data.properties.apn;
    var center = data.properties.marker;
    
    if(parcels[apn]) {
        //TODO: Zoom to it, too...
        var infowindow = parcels[apn].popup;
        if(!infowindow.getMap()) infowindow.open(map);
        return;
    }
    
    var infowindow = new google.maps.InfoWindow({
        content:  infotemplate.render({data:props, extra:getExtra(props.source_name)}),
        position: new google.maps.LatLng(center.lat, center.lon)
    });
    
    infowindow.open(map);
    
    removeAllParcels();
    parcels[apn] = new GeoJSON(data, parcelOptions);
    parcels[apn].popup = infowindow;
    
    $.each(parcels[apn], function(index, poly) {
        poly.setMap(map);
        google.maps.event.addListener(poly, 'click', function() {
            // Undocumented hack to check if the window is already open.
            // Needed, unfortunately, to prevent flickering.
            if(!infowindow.getMap()) infowindow.open(map);
        });
    });
    
    if(options.zoom) {
        map.fitBounds(parcels[apn][0].getBounds());
        map.setZoom(Math.min(17, map.getZoom()-1));
    }
}

function removeParcel(apn) {
	var parcel = parcels[apn];
    for(var i = 0; i < parcel.length; ++i) {
    	parcel[i].setMap(null);
    }
    
    parcel.popup.close();
    //TODO:  Does the popup need to be deleted?
    delete(parcels[apn]);
}

function removeAllParcels() {
	for(apn in parcels) {
		removeParcel(apn);
	}
}
