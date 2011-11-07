var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
    $('.delete_column').css('background-color','black');
}

//
// DOM-ready
//
$(function(){
  // set page appearance
  zebra_stripe_tables();

  // form controls
  $('#new_note')
    .click(
      function () {
        $(this).fadeOut();
        $('#notes_form').slideDown();
      });

  $('#id_effective_date')
    .datepicker();

  $('#note_cancel')
    .click(
      function () {
        $('#notes_form').slideUp();
        $('#new_note').fadeIn();
      });

  // activate jeditable
  var valid_chars = new Array('0','1','2','3','4','5','6','7','8','9');
  var verify_date = function (dfval) {
      var dash_re = new RegExp("-","g"); //regular expression object for finding dashes in dates
      var dfval;          //user-input value of date input field
      var srchmod;        //search modifier, one of: "<","<=",">",">="
      var dtval;          //the date portion of the search string
      var date;           //javascript Date object
      var dtstr;          //date string created from date
      var dtpieces;       //the mm, dd, and yyyy pieces of the dfval
      var year;           //the year dtpiece
      var foundyear;      //test for a 4-digit year
      var minyear = 1900; //the earliest year allowed
      var maxyear = 2038; //the latest year allowed
      var c;              //a character
      var verified;       //test for date verification

      if (dfval != "") {
          //dashes don't seem to be recognized as date separators
          dfval = dfval.replace(dash_re,"/");
          //find and remember any srchmod character(s)
          if (dfval.search("<=") > -1 || dfval.search(">=") > -1) {
              srchmod = dfval.slice(0,2);
              dtval = dfval.slice(2);
          } else if (dfval.search("<") > -1 || dfval.search(">") > -1) {
              srchmod = dfval.slice(0,1);
              dtval = dfval.slice(1);
          } else {
              srchmod = "";
              dtval = dfval;
          }
          
          //confirm that a four-digit year was input
          //(too easy for a date out of the acceptible python/db range
          //of valid dates to be input unless the 4-digit year is enforced)
          dtpieces = dtval.split("/");
          if (dtpieces.length != 3) {
              return false;
          }
          foundyear = false;
          if (dtpieces[2].length == 4) {
              year = parseInt(dtpieces[i]);
              foundyear = true;
          }
          if (foundyear) {
              //confirm that the year is within acceptable bounds
              if (year < minyear) {
                  return false;
              } else if (year > maxyear) {
                  return false;
              }
          } else {
              return false;
          }
          //finally, we can officially verify the date!
          date = new Date(dtval);
          var mm = (date.getMonth()+1) + ''; //month numbering appears to start at 0!
          while (mm.length < 2) {
              mm = '0' + mm;
          }
          var dd = date.getDate() + '';
          while (dd.length < 2) {
              dd = '0' + dd;
          }
          var yyyy = date.getFullYear();
          dtstr = new String(srchmod + mm + "/" + dd + "/" + yyyy);
          c = dtstr.charAt(0);
          verified = false;
          for (var i=0; i<valid_chars.length; i++) {
              if (c == valid_chars[i]) {
                  verified = true;
                  break;
              }
          }
          if (!verified) {
              return false;
          }
      }
      return true;
  }

  var edit_refresh = function (value, settings) {
    var idnote = $(this).attr('id').split('_')[2];
    $('#note_' + idnote).flash().flash();
  }

  $('.editable_textarea')
    .editable('/gentlemens_gt/note/update/note',
        {type: 'autogrow',
         tooltip: 'Click to edit',
         placeholder: '[edit]',
         data: function(value, settings) {
                 return deentify_text(value);
               },
         submit: 'OK',
         cancel: 'Cancel',
         onblur: 'ignore',
         width: '40em',
         style: 'inherit',
         onsubmit: function(){
                     return jeditable_validate(this, null, '', 1);
                   }//,
         //callback: edit_refresh
        });

  $('.editable_date')
    .editable('/gentlemens_gt/note/update/effective_date',
        {type: 'datepicker',
         tooltip: 'Click to edit',
         placeholder: '',
         width: '8em',
         submit: 'OK',
         cancel: 'Cancel',
         onblur: 'ignore',
         onsubmit: function(){
                     return jeditable_validate(
                       this, verify_date,
                       'Please enter a valid date.'
                     );
                   },
         callback: edit_refresh
        });

  // other
  $('[id^=delete_note]')
    .click(
      function () {
      var answer = confirm('Really delete this note?');
      if (answer){
        var id = $(this).attr('id').split('_').slice(2);
        $.post('/gentlemens_gt/note/delete/' + id, {},
            function(data, textStatus){
              if (data.response == 'success'){
                window.location.reload();
              } else {
                alert(data.data.msg);
              }
            }, 'json'
          );
        }
      });

});
