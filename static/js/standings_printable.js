//
// DOM-ready
//
$(function(){
  // form controls
  $('#new_unit')
    .click(
      function () {
        $(this).fadeOut();
        $('#unit_form').slideDown();
      });

  $('#unit_cancel')
    .click(
      function () {
        $('#unit_form').slideUp();
        $('#new_unit').fadeIn();
      });

  $('[id^=delete_unit]')
    .click(
      function () {
      var answer = confirm('Really delete this unit?');
      if (answer){
        var unit_id = $(this).attr('id').split('_').slice(2);
        $.post('/gentlemens_gt/armylist/units/delete/' + unit_id, {},
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

  $('[id^=printable_armylist]')
    .click(
      function () {
        var armylist_id = $(this).attr('id').split('_').slice(2);
        window.open('/gentlemens_gt/armylist/' + armylist_id + '/printable',
                    'PrintableArmyList',
                    'width=600,height=600,scrollbars=yes,left=200,top=200');
      });
});
