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
  $('#new_blackmark')
    .click(
      function () {
        $(this).fadeOut();
        $('#blackmark_form').slideDown();
      });

  $('#cancel_button')
    .click(
      function () {
        $('#blackmark_form').slideUp();
        $('#new_blackmark').fadeIn();
      });

  var edit_refresh = function (value, settings) {
    var blackmark_id = $(this).attr('id').split('_')[2];
    $('#blackmark_' + blackmark_id).flash().flash();
  }

  $('.editable_textarea')
    .editable('/gentlemens_gt/sports/blackmarks/update',
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

  // other
  $('[id^=delete_blackmark]')
    .click(
      function () {
      var answer = confirm('Really delete this Black Mark?');
      if (answer){
        var id = $(this).attr('id').split('_').slice(2);
        $.post('/gentlemens_gt/sports/blackmarks/delete/' + id, {},
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
