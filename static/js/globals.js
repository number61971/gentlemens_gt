SITE_ROOT = 'gentlemens_gt';

//
// general-purpose functions
//
Array.prototype.contains = function (element) {
  for (var i=0; i < this.length; i++) {
    if (this[i] == element) {
      return true;
    }
  }
  return false;
};

Array.prototype.remove = function(s){
  for (var i=0; i < this.length; i++){
    if (s == this[i]) {this.splice(i, 1);}
  }
};

String.prototype.strip = function() {
  return this.replace(/^\s+|\s+$/g,"");
};
String.prototype.lstrip = function() {
  return this.replace(/^\s+/,"");
};
String.prototype.rstrip = function() {
  return this.replace(/\s+$/,"");
};

var getQS = function(as_list){
  var qs = location.search.substring(1);
  if (as_list){
    qs = qs.split('&');
  }
  return qs;
};

var getQSParam = function(key, default_val){
  // pull the parameter value out of the query string
  if (default_val === null){
    default_val = "";
  }
  key = key.replace(/[\[]/,"\\[").replace(/[\]]/,"\\]");
  var regex = new RegExp("[\\?&]"+key+"=([^&#]*)");
  var qs = regex.exec(window.location.href);
  if (qs === null) {
    return default_val;
  } else {
    return qs[1];
  }
};


// global datepicker settings
$.datepicker.setDefaults(
    {showOn: 'button',
     buttonImage: '/' + SITE_ROOT + '/static/img/calendar.png',
     buttonImageOnly: true
    }
  );

//
// string format functions
//
var format_phone = function(val){
    var nondigit = new RegExp('[^0-9]','g');
    var newval = val.replace(nondigit, '');
    if (newval) {
      var ext = newval.slice(10);
      newval = '(' + newval.slice(0,3) + ') ' + newval.slice(3,6) + '-' + newval.slice(6,10);
      if (ext != ''){
        newval += ' x' + ext;
      }
    }
    return newval;
};

var pprintNumber = function(x) {
  var x_str = x.toString();
  var i = x_str.indexOf(".");
  if (i<1) {
    i = x_str.length;
  }
  while (i>3) {
    i-=3;
    var j = x_str.charAt(i-1);
    if (j>="0" && j<="9") {
      x_str = x_str.substr(0,i) + "," + x_str.substr(i);
    }
  }
  return x_str;
};

// the following is from http://www.learningjquery.com/2007/08/clearing-form-data
$.fn.clearForm = function() {
  return this.each(function() {
    var type = this.type, tag = this.tagName.toLowerCase();
    if (tag == 'form')
      return $(':input',this).clearForm();
    if (type == 'text' || type == 'password' || tag == 'textarea')
      this.value = '';
    else if (type == 'checkbox' || type == 'radio')
      this.checked = false;
    else if (tag == 'select')
      this.selectedIndex = -1;
  });
};

//
// DOM-ready
//
$(function(){
  // set the current global location
  var currloc = $('#nav-global-location').val();
  $('#' + currloc).parent().addClass('current_page_item');

  // activate all clear form buttons
  $('.clearForm').click(function(){
    var form = $(this).parents('form');
    form.clearForm();
  });

  // page refresh based on selected tournament
  $('#id_tournament')
    .change(
      function () {
        var id = $(this).val();
        window.location.href = '/gentlemens_gt/tournament/' + id;
      });

  var tournament_id = $('#id_tournament').val();
  if (tournament_id) {
    $('#edit_selected_tournament').attr('href','/gentlemens_gt/tournament/' + tournament_id);
  } else {
    $('#edit_selected_tournament').hide();
  }
});
