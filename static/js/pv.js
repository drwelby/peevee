var parcels = {};
var map;

var infotemplate = Hogan.compile($('#tabcontent').html(), {delimiters: '[[ ]]'});

$('input#searchbox').typeahead({
    name: 'pv',
    remote: 'api/search/?q=%QUERY',
    limit: 20,
    engine: Hogan,
    template: "{{{show}}}"
});

function resizeSearch() {
    $('.tt-dropdown-menu').width($('.twitter-typeahead').width()-3);
}

$(window).resize(resizeSearch).resize();

$('#searchbox').bind('typeahead:selected', function(obj, datum, name) { 
    addParcel({apn:datum.apn, county:datum.county});
});

$('#searchbox').bind('typeahead:autocompleted', function(obj, datum, name) { 
    setTimeout( function(){ $('#searchbox').val('foo');}, 100);
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
    var mapOptions = {
        center: new google.maps.LatLng(40.5, -122.5),
        zoom: 12,
        mapTypeId: google.maps.MapTypeId.HYBRID
    };
    var pvLayer = new google.maps.ImageMapType({
        getTileUrl: function(ll, z) {
            return "http://www.geonotice.net:8888/geoserver/gwc/service/gmaps?layers=pv:master&zoom="
                    + z + "&x=" + ll.x + "&y=" + ll.y + "&format=image/png";
          },
          tileSize: new google.maps.Size(256, 256),
          isPng: true,
          maxZoom: 20,
          name: "Parcels",
          alt: "Parcel Layer"
    });

    map = new google.maps.Map(document.getElementById("map"),mapOptions);
    map.overlayMapTypes.push(pvLayer);
    google.maps.event.addListener(map, 'click', addParcel);
}
google.maps.event.addDomListener(window, 'load', initialize);

function addParcel(event) {
    url = 'api/parcel/';
    if (event.latLng) {
        data = {
            lat: event.latLng.lat(),
            lon: event.latLng.lng()
        };
    } else if (event.apn) {
        data = {
            apn: event.apn,
            county: event.county
        };
    } else return;

    $.ajax(
        url,  {
        data : data,
        success : function(resp, status, xhr) {
            drawParcel(resp);
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
    if (source=='shastaco') { return 'Extra Shasta Stuff'}
}

function drawParcel(data) {
    props = data.properties
    var apn = props.apn;
    var center  = data.properties.marker;
    if (parcels[apn]) {return}
    parcels[apn] = {};
    var myLatlng = new google.maps.LatLng(center.lat, center.lon);
    var marker = new google.maps.Marker({
            position: myLatlng,
            title: "" + apn
    });
    marker.setMap(map);
    var infowindow = new google.maps.InfoWindow({
        content: infotemplate.render({data:props, extra:getExtra(props.source_name)})
    });
    google.maps.event.addListener(marker, 'click', function() {
        infowindow.open(map, marker);
    });
    parcels[apn][0] = marker;
    polys = new GeoJSON(data, parcelOptions);
    $.each(polys, function(index, poly){
        parcels[apn][index+1] = poly;
        poly.setMap(map);
    });
    if (data.properties.zoom) {
        map.fitBounds(parcels[apn][1].getBounds());
        map.setZoom(Math.min(17, map.getZoom()-1));
    }
}

function removeParcel(apn) {
    $.each(parcels[apn], function(index,obj) {
        obj.setMap(null);
    });
    delete(parcels[apn]);
}
