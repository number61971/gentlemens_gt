var zebra_stripe_tables = function () {
    $('.tablerow:even').addClass('highlight');
}

//
// DOM-ready
//
$(function(){
  // set page appearance
  zebra_stripe_tables();

  $('.remove_from_tournament')
    .click(
      function () {
        if (confirm('Really remove this player?')) {
          var ids = $(this).parent().attr('id').split('_');
          var tournament_id = ids[0];
          var tplayer_id = ids[1];
          window.location.href = '/gentlemens_gt/players/' + tournament_id + '/' + tplayer_id + '/remove_from_tournament';
        }
      });
});
