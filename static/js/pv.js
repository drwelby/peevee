var parcels = {};
var ctrlKey = false;
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

// Google Maps events don't have key info...
document.onkeyup   = function(event) {if(event.keyCode == 17) ctrlKey = false;}
document.onkeydown = function(event) {if(event.keyCode == 17) ctrlKey = true;}
window.onblur      = function(event) {ctrlKey = false;}

// Print the center of the map.
// Seems unreasinably complicated...
function resizeMap() {
	var w = $('#printwrap').width();
	var h = $('#printwrap').height();
	$('#map').css({
		'width':       '' + w + 'px',
		'height':      '' + h + 'px',
		'margin-top':  '-' + h/2 + 'px',
		'margin-left': '-' + w/2 + 'px'
	});
}

window.onresize = resizeMap;

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

function urlParam(n) {
	// http://stackoverflow.com/a/12254019/589985
	var half = location.search.split(n+'=')[1];
	return half? decodeURIComponent(half.split('&')[0]) : null;
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
    
    resizeMap();
    
    map = new google.maps.Map(document.getElementById("map"), {
        draggableCursor: 'default',
        mapTypeControl: false,
        mapTypeId: google.maps.MapTypeId.HYBRID,
        tilt: 0
    });
    
    map.overlayMapTypes.push(new google.maps.ImageMapType({
        getTileUrl: genTileUrl('enplan:parcels'),
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
    
    $('#find-tool').on('click', function(event) {
    	$('#searchbox').focus();
    	event.preventDefault();
    });
    
    $('#help-tool').on('click', function(event) {
    	$('#overlay').show();
    	$('#info-window').show();
    	event.preventDefault();
    });
    
    $('#zoom-tool').on('click', function(event) {
    	zoomToSelection();
    	event.preventDefault();
    });
    
    $('#share-tool').on('click', function(event) {
    	event.preventDefault();
    	share();
    });
    
    $('.close-window').on('click', function(event) {
        $('#overlay').hide();
        $(this).closest('.window').hide();
    	event.preventDefault();
    });
    
    $('body').on('keyup', function(event) {
    	// You're typing?  Sorry!  Never mind...
    	if($(event.target).is('input')) return;
    	
    	switch(event.keyCode)
    	{
    	case 27: // Escape
    		closeAllPopups();
    		return;
    	case 46: // Delete
    		removeAllParcels();
    		return;
    	case 70: // F
    		$('#searchbox').select();
    		return;
    	case 83: // S
    		share();
			return;
    	case 90: // Z
    		zoomToSelection();
    		return;
    	}
    });
    
    var z = parseInt(urlParam('z'));
    var x = parseFloat(urlParam('x'));
    var y = parseFloat(urlParam('y'));
    
    if(z && x && y) {
    	map.setZoom(z);
		map.panTo(new google.maps.LatLng(y, x));
    }
    else {
		// Zoom to maximum extent
		var bounds = new google.maps.LatLngBounds();
		bounds.extend(new google.maps.LatLng(extent[1], extent[0]));
		bounds.extend(new google.maps.LatLng(extent[3], extent[2]));
		map.fitBounds(bounds);
    }
    
    var p = urlParam('p');
    if(p) {
    	var all = p.split('|');
    	for(var i = 0; i < all.length; ++i) {
    		var pid = {
    			fips: all[i].slice(0, 5),
    			id:   all[i].slice(6)
    		};
    		
    		getParcel(pid, {
    			popup: (all[i][5] == '+'),
    			clear: false
    		});
    	}
    }
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
        content:  $(infotemplate.render({data:props, extra:getExtra(props.source_name)}))[0],
        position: new google.maps.LatLng(center.lat, center.lon)
    });
    
    if(ctrlKey || options.close == true) {
    	closeAllPopups();
    }
    else if(options.clear != false) {
		removeAllParcels();
    }
    
    if(options.popup != false) {
	    infowindow.open(map);
	}
    
    parcels[apn] = new GeoJSON(data, parcelOptions);
    parcels[apn].popup = infowindow;
    parcels[apn].attrs = props;
    
    $.each(parcels[apn], function(index, poly) {
        poly.setMap(map);
        google.maps.event.addListener(poly, 'click', function() {
        	if(ctrlKey)
        	{
        		removeParcel(apn);
        	}
        	else
        	{
		        // Undocumented hack to check if the window is already open.
		        // Needed, unfortunately, to prevent flickering.
		        if(!infowindow.getMap()) infowindow.open(map);
            }
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
	for(var apn in parcels) {
		removeParcel(apn);
	}
}

function closeAllPopups() {
	for(var apn in parcels) {
		parcels[apn].popup.close();
	}
}

function zoomToSelection() {
	var found  = false;
	var bounds = new google.maps.LatLngBounds();
	
	for(var apn in parcels) {
		found = true;
		var parcel = parcels[apn];
		for(var i = 0; i < parcel.length; ++i) {
			bounds.union(parcel[i].getBounds());
		}
	}
	
	if(found) {
		map.fitBounds(bounds);
	}
}

function share() {
	var selected = [];
	for(var apn in parcels)
	{
		var parcel = parcels[apn];
		var fips   = parcel.attrs.fips;
		var id     = parcel.attrs.id;
		var sep    = parcel.popup.getMap()? '+' : '-';
		selected.push(fips + sep + id);
	}
	
	var base = window.location.protocol + '//' + window.location.host;
	var params = [
		'z=' + map.zoom,
		'x=' + map.getCenter().lng(),
		'y=' + map.getCenter().lat(),
		'p=' + selected.join('|')
	];
	
	var url = base + '?' + params.join('&');
	$('#share-url').text(url);
	$('#share-url').attr('href', url);
	
	$('#overlay').show();
	$('#share-window').show();
}
