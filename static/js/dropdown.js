function makeTR(datum)
{
	var tr = $('<tr></tr>').attr('class', 'match-' + datum.match);
	tr.append($('<td class="hint-apn"></td>').text(datum.apn));
	tr.append($('<td class="hint-addr"></td>').text(datum.saddr1 || undefined));
	tr.append($('<td class="hint-addr"></td>').text(datum.saddr2 || undefined));
	tr.append($('<td class="hint-county"></td>').text(datum.county));
	
	if(datum.pro)
	{
		//Attach pro stuff.
		tr.append($('<td class="hint-owner"></td>').text(datum.pro.owner));
	}
	
	tr.data('datum', datum);
	return tr;
}

function display(json, status, xhr)
{
	var data = json.results;
	var tb = $('#dropdown-container');
	tb.children().remove();
	
	if(data.length > 0)
	{
		for(var i in data)
		{
			tb.append(makeTR(data[i]));
		}
		
		tb.children().eq(0).addClass('current');
		$('#dropdown').attr('class', 'status-display');
	}
	else
	{
		$('#dropdown').attr('class', 'status-nothing');
	}
	
}

function error()
{
	$('#dropdown').attr('class', 'status-problem');
}

function select(tr)
{
	var d = tr.data('datum');
	$('#searchbox').val(d.saddr1? d.saddr1 + ' ' + (d.saddr2 || '') : d.apn);
	getParcel({fips: d.fips, id: d.id}, {zoom: true});
	$('#dropdown').removeAttr('class');
	$('#searchbox').blur();
	
	var m = 'Unknown';
	if(tr.hasClass('match-apn')) m = 'By APN';
	if(tr.hasClass('match-address')) m = 'By Address';
	_gaq.push(['_trackEvent', 'Select', m, d.fips + ':' + d.id]);
}

var lastText;
var lastTime = new Date();

$('#searchbox').on('keyup', function(event) {
	// Hotkeys
	switch(event.keyCode)
	{
	case 40: // Down Arrow
		var curr = $('#dropdown-container').children('.current');
		var next = curr.next();
		if(next.length > 0)
		{
			curr.removeClass('current');
			next.addClass('current');
		}
		return;
	case 38: // Up Arrow
		var curr = $('#dropdown-container').children('.current');
		var prev = curr.prev();
		if(prev.length > 0)
		{
			curr.removeClass('current');
			prev.addClass('current');
		}
		return;
	case 13: // Enter
		var curr = $('#dropdown-container').children('.current');
		select(curr);
		return;
	};
	
	var text = $(this).val();
	if(text.length < 3 || text == lastText) return;
	
	$('#dropdown').attr('class', 'status-working');
	var time = new Date();
	lastTime = time;
	lastText = text;
	
	setTimeout(function() {
		if(lastTime != time) return;
		jQuery.ajax('api/search/', {
			data: {q: text},
			dataType: 'json',
			error: error,
			success: display,
		});
	}, 300);
});

$('body').on('click', function(event) {
	if($(this).closest('#dropdown').length == 0)
	{
		$('#dropdown').removeAttr('class');
	}
});

$('#dropdown-display').on('mouseover', 'tr', function(event) {
	$('#dropdown-display tr').removeClass('current');
	$(this).addClass('current');
});

$('#dropdown-display').on('click', 'tr', function(event) {
	event.stopPropagation();
	select($(this));
});

$('#searchbox').on('click', function(event) {
	$(this).select();
});

