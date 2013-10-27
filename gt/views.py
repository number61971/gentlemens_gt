import random

from django.conf import settings
from django.contrib.humanize.templatetags import humanize
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.shortcuts import get_list_or_404
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils import simplejson

from gt.models import *

#
# useful globals
#
def tournament_choice(req, tournament_id):
    if int(tournament_id):
        req.session['tournament_id'] = str(tournament_id)
    return TournamentChoice({'tournament':str(tournament_id)})

def common_page_data(req, tournament_id):
    if int(tournament_id):
        tournament = Tournament.objects.get(id=tournament_id)
        masthead = tournament.name
        tagline = tournament.tagline
        notes_count = Tournament.objects.get(id=tournament_id).notes.count()
    else:
        id = req.session.get('tournament_id')
        if id:
            tournament = Tournament.objects.get(id=id)
            masthead = tournament.name
            tagline = tournament.tagline
            notes_count = Tournament.objects.get(id=id).notes.count()
        else:
            masthead = "The Gentlemen's Grand Tournament"
            tagline = 'For one bloodsoaked weekend, there is only war!'
            notes_count = 0
    return {'tournament_choice': tournament_choice(req, tournament_id),
            'tournament_id': tournament_id,
            'tournament_notes_count': notes_count,
            'masthead': masthead,
            'tagline': tagline,
           }

#
# tournament
#
def tournament(req, tournament_id):
    if int(tournament_id):
        tournament = Tournament.objects.get(id=tournament_id)
        data = {'name':tournament.name,
                'tagline':tournament.tagline,
                'points_limit':tournament.points_limit,
                'description':tournament.description,
                'start_date':tournament.start_date,
                'end_date':tournament.end_date,
                'ranking_method':tournament.ranking_method,
                'opponent_pairing_method':tournament.opponent_pairing_method,
               }
        form = TournamentForm(data)
    else:
        tournament = None
        form = TournamentForm()
    data = common_page_data(req, tournament_id)
    data['tournament'] = tournament
    data['form'] = form
    return render_to_response('tournament.html', data)

def tournament_update(req):
    id = req.POST['id']
    form = TournamentForm(req.POST)
    if form.is_valid():
        d = form.cleaned_data
        if int(id):
            # update Tournament
            tournament = Tournament.objects.get(id=id)
            tournament.name = d['name']
            tournament.tagline = d['tagline']
            tournament.points_limit = d['points_limit']
            tournament.description = d['description']
            tournament.start_date = d['start_date']
            tournament.end_date = d['end_date']
            tournament.ranking_method = d['ranking_method']
            tournament.opponent_pairing_method = d['opponent_pairing_method']
        else:
            # create Case
            tournament = Tournament(
                           name=d['name'],
                           tagline=d['tagline'],
                           points_limit=d['points_limit'],
                           description=d['description'],
                           start_date=d['start_date'],
                           end_date=d['end_date'],
                           ranking_method=d['ranking_method'],
                           opponent_pairing_method=d['opponent_pairing_method'],
                         )
        tournament.save()
        # success redirect
        return redirect('/gentlemens_gt/players/%s' % tournament.id)
    else:
        # return edit form with errors
        if int(id):
            tournament = Tournament.objects.get(id=id)
        else:
            tournament = None
        data = common_page_data(req, tournament_id)
        data['tournament'] = tournament
        data['form'] = form
        return render_to_response('tournament.html', data)

def tournament_notes(req, tournament_id):
    tournament = Tournament.objects.get(id=tournament_id)
    notes = tournament.notes.all()
    data = common_page_data(req, tournament_id)
    data['notes'] = notes
    data['id'] = tournament_id
    data['title'] = tournament.name
    data['form'] = NoteForm()
    data['valid_form'] = True
    data['action'] = '/gentlemens_gt/tournament/%s/notes/new' % tournament_id
    return render_to_response('tournament_notes.html', data)

def create_tournament_note(req, tournament_id):
    form = NoteForm(req.POST)
    tournament = Tournament.objects.get(id=tournament_id)
    if form.is_valid():
        d = form.cleaned_data
        note = Note(note=d['note'], effective_date=d['effective_date'])
        note.save()
        tournament_note = TournamentNote(tournament=tournament, note=note)
        tournament_note.save()
        # success redirect
        return redirect ('/gentlemens_gt/tournament/%s/notes' % tournament_id)
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['notes'] = tournament.notes.all()
        data['id'] = tournament_id
        data['title'] = tournament.name
        data['form'] = form
        data['valid_form'] = False
        data['action'] = '/gentlemens_gt/tournament/%s/notes/new' % tournament_id
        return render_to_response('tournament_notes.html', data)

#
# players
#
def players(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    return redirect('/gentlemens_gt/players/%s' % tournament_id)

def players_list(req, tournament_id):
    tournament_players = TournamentPlayer.objects.filter(
            tournament__id=tournament_id).all()
    other_players = Player.objects.exclude(
            id__in=[tp.player.id for tp in tournament_players]
            ).all()
    data = common_page_data(req, tournament_id)
    data['tournament_players'] = tournament_players
    data['tournament_players_count' ] = len(tournament_players)
    data['other_players'] = other_players
    data['other_players_count'] = len(other_players)
    return render_to_response('players.html', data)

def player_add_to_tournament(req, tournament_id, player_id):
    armylist = ArmyList(race=Race.objects.get(name='Unknown'))
    armylist.save()
    tplayer = TournamentPlayer(
                tournament=Tournament.objects.get(id=tournament_id),
                player=Player.objects.get(id=player_id),
                armylist = armylist
                )
    tplayer.save()
    return redirect('/gentlemens_gt/players/%s' % tournament_id)

def player_remove_from_tournament(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    sql = "delete from gt_armylistunit where armylist_id=%s;" % tplayer.armylist.id
    execute_sql(sql)
    sql = "delete from gt_armylist where id=%s;" % tplayer.armylist.id
    execute_sql(sql)
    sql = "delete from gt_tournamentplayer where id=%s;" % tplayer.id
    execute_sql(sql)
    return redirect('/gentlemens_gt/players/%s' % tournament_id)

def player_toggle_active(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    if tplayer.active:
        tplayer.active = False
    else:
        tplayer.active = True
    tplayer.save()
    return redirect('/gentlemens_gt/players/%s' % tournament_id)

def player_toggle_ringer(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    if tplayer.ringer:
        tplayer.ringer = False
    else:
        tplayer.ringer = True
        tplayers = TournamentPlayer.objects.filter(
                    tournament__id=tournament_id
                ).exclude(
                        id=tplayer_id
                ).all()
        for tp in tplayers:
            tp.ringer = False
            tp.save()
    tplayer.save()
    return redirect('/gentlemens_gt/players/%s' % tournament_id)

def player_army_list(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    formdata = {'description': tplayer.armylist.description,
                'race': tplayer.armylist.race.id,
                'subrace': tplayer.armylist.subrace,
               }
    armylist_form = ArmyListForm(formdata)
    data = common_page_data(req, tournament_id)
    data['tplayer'] = tplayer
    data['armylist_form'] = armylist_form
    data['unit_form'] = UnitForm()
    data['valid_unit_form'] = True
    data['armylist'] = armylist_display(tplayer.armylist)
    return render_to_response('armylist.html', data)

def player_edit(req, tournament_id, player_id):
    if int(player_id):
        player = Player.objects.get(id=player_id)
        data = {'firstname': player.firstname,
                'midname': player.midname,
                'lastname': player.lastname,
                'suffix': player.suffix,
                'addr_number': player.addr_number,
                'addr_pre_dir': player.addr_pre_dir,
                'addr_street': player.addr_street,
                'addr_post_dir': player.addr_post_dir,
                'addr_secondary': player.addr_secondary,
                'city': player.city,
                'state': player.state,
                'zip5': player.zip5,
                'zip4': player.zip4,
                'phone': player.phone_pprint(),
                'email': player.email,
               }
        form = PlayerForm(data)
    else:
        player = None
        form = PlayerForm()
    data = common_page_data(req, tournament_id)
    data['player'] = player
    data['form'] = form
    data['player_id'] = str(player_id)
    return render_to_response('player.html', data)

def player_update(req):
    id = req.POST['id']
    tournament_id = req.POST['tournament_id']
    form = PlayerForm(req.POST)
    if form.is_valid():
        d = form.cleaned_data
        if int(id):
            # update Player
            player = Player.objects.get(id=id)
            player.firstname = d['firstname']
            player.midname = d['midname']
            player.lastname = d['lastname']
            player.suffix = d['suffix']
            player.addr_number = d['addr_number']
            player.addr_pre_dir = d['addr_pre_dir']
            player.addr_street = d['addr_street']
            player.addr_post_dir = d['addr_post_dir']
            player.city = d['city']
            player.state = d['state']
            player.zip5 = d['zip5']
            player.zip4 = d['zip4']
            player.phone = d['phone']
            player.email = d['email']
        else:
            # create Player
            player = Player(
                        firstname=d['firstname'],
                        midname=d['midname'],
                        lastname=d['lastname'],
                        suffix=d['suffix'],
                        addr_number=d['addr_number'],
                        addr_pre_dir=d['addr_pre_dir'],
                        addr_street=d['addr_street'],
                        addr_post_dir=d['addr_post_dir'],
                        addr_secondary=d['addr_secondary'],
                        city=d['city'],
                        state=d['state'],
                        zip5=d['zip5'],
                        zip4=d['zip4'],
                        phone=d['phone'],
                        email=d['email'],
                        )
        player.save()
        # success redirect
        return redirect('/gentlemens_gt/players/%s' % tournament_id)
    else:
        # return edit form with errors
        if int(id):
            player = Player.objects.get(id=id)
        else:
            player = None
        data = common_page_data(req, tournament_id)
        data['player'] = tournament
        data['form'] = form
        data['player_id'] = id
        return render_to_response('player.html', data)

def player_notes(req, tournament_id, player_id):
    player = Player.objects.get(id=player_id)
    notes = player.notes.all()
    data = common_page_data(req, tournament_id)
    data['notes'] = notes
    data['id'] = player_id
    data['title'] = player.fullname()
    data['form'] = NoteForm()
    data['valid_form'] = True
    data['action'] = '/gentlemens_gt/players/%s/%s/notes/new' % (
            tournament_id, player_id)
    return render_to_response('player_notes.html', data)

def create_player_note(req, tournament_id, player_id):
    form = NoteForm(req.POST)
    player = Player.objects.get(id=player_id)
    if form.is_valid():
        d = form.cleaned_data
        note = Note(note=d['note'], effective_date=d['effective_date'])
        note.save()
        player_note = PlayerNote(player=player, note=note)
        player_note.save()
        # success redirect
        return redirect ('/gentlemens_gt/players/%s/%s/notes' % (
            tournament_id, player_id))
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['notes'] = player.notes.all()
        data['id'] = player_id
        data['title'] = player.fullname()
        data['form'] = form
        data['valid_form'] = False
        data['action'] = '/gentlemens_gt/players/%s/%s/notes/new' % (
                tournament_id, player_id)
        return render_to_response('player_notes.html', data)

#
# army lists
#
def army_list_update(req):
    tplayer = TournamentPlayer.objects.get(id=req.POST['tplayer_id'])
    armylist = tplayer.armylist
    armylist_form = ArmyListForm(req.POST)
    if armylist_form.is_valid():
        d = armylist_form.cleaned_data
        armylist.description = d['description']
        armylist.race = Race.objects.get(id=d['race'])
        armylist.subrace = d['subrace']
        armylist.save()
        # success redirect
        return redirect('/gentlemens_gt/players/%s/%s/army_list' % (
                req.POST['tournament_id'], tplayer.id))
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['tplayer'] = tplayer
        data['armylist_form'] = armylist_form
        data['unit_form'] = UnitForm()
        data['valid_unit_form'] = True
        data['armylist'] = armylist_display(tplayer.armylist)
        return render_to_response('armylist.html', data)

def army_list_create_unit(req):
    tplayer = TournamentPlayer.objects.get(id=req.POST['tplayer_id'])
    armylist = tplayer.armylist
    unit_form = UnitForm(req.POST)
    if unit_form.is_valid():
        d = unit_form.cleaned_data
        unit = Unit(
                force_org_slot=d['force_org_slot'],
                occupies_slot=d['occupies_slot'],
                num_models=d['num_models'],
                type=d['type'],
                details=d['details'],
                points_cost=d['points_cost'],
                )
        unit.save()
        armylist_unit = ArmyListUnit(armylist=armylist, unit=unit)
        armylist_unit.save()
        # success redirect
        return redirect('/gentlemens_gt/players/%s/%s/army_list' % (
                req.POST['tournament_id'], tplayer.id))
    else:
        # return form with errors
        formdata = {'description': armylist.description,
                    'race': armylist.race.id,
                    'subrace': armylist.subrace,
                }
        armylist_form = ArmyListForm(formdata)
        data = common_page_data(req, req.POST['tournament_id'])
        data['tplayer'] = tplayer
        data['armylist_form'] = armylist_form
        data['unit_form'] = unit_form
        data['valid_unit_form'] = False
        data['armylist'] = armylist_display(tplayer.armylist)
        return render_to_response('armylist.html', data)

def army_list_delete_unit(req, unit_id):
    unit = Unit.objects.get(id=unit_id)
    unit.delete()
    response = {'response':'success',
                'data':{'msg':'Deleted Unit with id %s.' % unit_id,
                        'id':unit_id,}
               }
    return HttpResponse(simplejson.dumps(response), 'application/json')

def armylist_display(armylist, deletable_units=True):
    list_data = armylist.get_list()
    out = []
    for slot in [s[0] for s in force_org_slots]:
        if list_data[slot]:
            out.append('<h3 class="force_org_slot">%s</h3>' % slot)
            for unit in list_data[slot]:
                if unit['num_models'] > 1:
                    num_models = '%s ' % unit['num_models']
                else:
                    num_models = ''
                if unit['details']:
                    details = ': %s' % unit['details']
                else:
                    details = ''
                if deletable_units:
                    delete_action = '<img id="delete_unit_%s" class="action_delete" src="/gentlemens_gt/static/img/action_delete.png" alt="Delete" title="Delete"/> ' % unit['id']
                else:
                    delete_action = ''
                out.append('<p class="army_list_unit">%s<span class="points_cost">[%s pts]</span> %s%s%s</p>' % (
                        delete_action,unit['points_cost'],
                        num_models, unit['type'], details))
    if out:
        out.append('<p class="army_list_total"><b>Total:</b> %s pts</p>' % humanize.intcomma(
            armylist.points_total()))
    return '\n'.join(out)

def armylist_printable(req, list_id):
    armylist = ArmyList.objects.get(id=list_id)
    tplayer = TournamentPlayer.objects.get(armylist__id=list_id)
    data = {'tplayer': tplayer,
            'armylist': armylist_display(armylist, deletable_units=False)}
    return render_to_response('armylist_printable.html', data)

#
# games
#
def games(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    round_number = req.session.get(
            'tournament_id_%s_round_number' % tournament_id)
    if not round_number:
        try:
            round_number = list(Round.objects.filter(
                    tournament__id=tournament_id).all())[-1].round
        except IndexError:
            round_number = 0
    return redirect('/gentlemens_gt/games/%s/%s' % (tournament_id,round_number))

def games_list(req, tournament_id, round_number):
    req.session['tournament_id_%s_round_number'] = round_number

    games_data = []
    try:
        round_obj = Round.objects.get(
                        tournament__id=tournament_id, round=round_number)
        games = Game.objects.filter(round=round_obj).all()
        for g in games:
            try:
                p1_sports = Sportsmanship.objects.get(
                        player=g.player1, rated_by=g.player2)
            except Sportsmanship.DoesNotExist:
                p1_sports = Sportsmanship(player=g.player1, rated_by=g.player2)
                p1_sports.save()

            try:
                p2_sports = Sportsmanship.objects.get(
                        player=g.player2, rated_by=g.player1)
            except Sportsmanship.DoesNotExist:
                p2_sports = Sportsmanship(player=g.player2, rated_by=g.player1)
                p2_sports.save()

            data = {
              'game_id': g.id,
              'table': g.table,
              'tplayer1_id': g.player1.id,
              'player1_id': g.player1.player.id,
              'player1_name': g.player1.player.fullname(),
              'player1_rank': g.player1.rank(highest_round=int(round_number)-1),
              'player1_active': g.player1.active,
              'player1_ringer': g.player1.ringer,
              'player1_race': g.player1.armylist.race.abbrev,
              'player1_mission_points': g.player1_mission_points,
              'player1_sports': p1_sports.score,
              'tplayer2_id': g.player2.id,
              'player2_id': g.player2.player.id,
              'player2_name': g.player2.player.fullname(),
              'player2_active': g.player2.active,
              'player2_ringer': g.player2.ringer,
              'player2_race': g.player2.armylist.race.abbrev,
              'player2_rank': g.player2.rank(highest_round=int(round_number)-1),
              'player2_mission_points': g.player2_mission_points,
              'player2_sports': p2_sports.score,
              'notes': g.notes,
                   }
            games_data.append(data)
    except Round.DoesNotExist:
        pass

    data = common_page_data(req, tournament_id)
    form = RoundSelectForm(
            {'round_number':round_number, 'tournament_id':tournament_id})
    data['round'] = round_number
    data['round_select_form'] = form
    data['games_data'] = games_data
    data['player_count'] = len(
                             Tournament.objects.get(id=tournament_id).players())
    return render_to_response('games.html', data)

def games_printable(req, tournament_id, round_number):
    round_obj = Round.objects.get(
                    tournament__id=tournament_id, round=round_number)
    games = Game.objects.filter(round=round_obj).all()
    games_data = []
    for g in games:
        data = {
            'table': g.table,
            'player1_name': g.player1.player.fullname(),
            'player1_rank': g.player1.rank(highest_round=int(round_number)-1),
            'player1_active': g.player1.active,
            'player1_ringer': g.player1.ringer,
            'player1_race': g.player1.armylist.race.abbrev,
            'player1_mission_points': g.player1_mission_points,
            'player2_name': g.player2.player.fullname(),
            'player2_active': g.player2.active,
            'player2_ringer': g.player2.ringer,
            'player2_race': g.player2.armylist.race.abbrev,
            'player2_rank': g.player2.rank(highest_round=int(round_number)-1),
            'player2_mission_points': g.player2_mission_points,
                }
        games_data.append(data)
    data = {'games_data': games_data,
            'round_obj': round_obj,
           }
    return render_to_response('games_printable.html', data)

def games_new_round(req, tournament_id):
    tournament = Tournament.objects.get(id=tournament_id)
    latest_round = list(Round.objects.filter(tournament=tournament).all())
    if latest_round:
        round_number = latest_round[-1].round + 1
    else:
        round_number = 1
    new_round = Round(tournament=tournament, round=round_number)
    new_round.save()
    return redirect('/gentlemens_gt/games/%s/%s/pairings' % (
                        tournament_id,round_number))

def games_pairings(req, tournament_id, round_number):
    tournament = Tournament.objects.get(id=tournament_id)
    round_obj = Round.objects.get(tournament=tournament, round=round_number)
    games = Game.objects.filter(round=round_obj).all()

    if not games:
        # create initial pairings
        if tournament.opponent_pairing_method == 'swiss':
            pairing_method = opponent_pairing_swiss
            standings = tournament.standings()
        elif tournament.opponent_pairing_method == 'accelerated swiss':
            pairing_method = opponent_pairing_accelerated_swiss
            if int(round_number) < 2 or int(round_number) > 4:
                standings = tournament.standings()
            elif int(round_number) == 2:
                # set the accelerated pairing for the top half of the list
                standings = tournament.standings()
                standings_list = standings['list']
                split = int(len(standings_list)/2)
                for s in standings_list[:split]:
                    tplayer = s['tplayer']
                    tplayer.accelerated_swiss_pairing_bonus = True
                    tplayer.save()
                standings = tournament.standings(
                                            accelerated_swiss_weighted=True)
            elif int(round_number) == 3:
                standings = tournament.standings(
                                            accelerated_swiss_weighted=True)
            elif int(round_number) == 4:
                # remove the accelerated pairing
                tplayers = TournamentPlayer.objects.filter(
                        tournament=tournament,
                        accelerated_swiss_pairing_bonus=True
                        ).all()
                for tplayer in tplayers:
                    tplayer.accelerated_swiss_pairing_bonus = False
                    tplayer.save()
                standings = tournament.standings()
        elif tournament.opponent_pairing_method == 'random':
            pairing_method = opponent_pairing_random
            standings = tournament.standings()

        ranked_tplayers = [s['tplayer'] for s in standings['list']]
        pairings = pairing_method(ranked_tplayers, int(round_number))
        tables = [n+1 for n in range(len(pairings))]
        r = random.SystemRandom()
        r.shuffle(tables)
        games = []
        for p1, p2 in pairings:
            table = tables.pop()
            game = Game(round=round_obj, player1=p1, player2=p2, table=table)
            game.save()
            games.append(game)
        games.sort(sort_games_by_table)

    # record each player's previous opponents
    games_data = []
    highest_round = int(round_number) - 1
    for g in games:
        if highest_round:
            tplayer1_opponents = ', '.join(
                    [o.player.fullname()
                     for o in g.player1.opponents(highest_round=highest_round)]
                    )
            tplayer2_opponents = ', '.join(
                    [o.player.fullname()
                     for o in g.player2.opponents(highest_round=highest_round)]
                    )
            tplayer1_rank = g.player1.rank(highest_round=highest_round)
            tplayer2_rank = g.player2.rank(highest_round=highest_round)
        else:
            tplayer1_opponents = None
            tplayer2_opponents = None
            tplayer1_rank = '--'
            tplayer2_rank = '--'
        games_data.append(
        {'game':g,
      'tplayer1_opponents':tplayer1_opponents if tplayer1_opponents else 'none',
      'tplayer2_opponents':tplayer2_opponents if tplayer2_opponents else 'none',
      'tplayer1_rank':tplayer1_rank,
      'tplayer2_rank':tplayer2_rank,
        })

    # record each table's record of previous players
    games = Game.objects.filter(round__tournament=tournament,
                                round__round__lt=round_number).all()
    table_players = {}
    for g in games:
        players = table_players.get(g.table, [])
        tp1name = g.player1.player.fullname()
        tp2name = g.player2.player.fullname()
        if tp1name not in players:
            players.append(tp1name)
        if tp2name not in players:
            players.append(tp2name)
        table_players[g.table] = players

    for gd in games_data:
        players = table_players.get(gd['game'].table, [])
        players.sort()
        gd['table_players'] = ', '.join(players) if players else 'none'

    form = RoundSelectForm(
            {'round_number':round_number, 'tournament_id':tournament_id})
    data = common_page_data(req, tournament_id)
    data['games'] = games_data
    data['round'] = round_number
    data['round_select_form'] = form
    return render_to_response('pairings.html', data)

def sort_games_by_table(game1, game2):
    table1 = game1.table
    table2 = game2.table
    if table1 < table2:
        return -1
    elif table1 > table2:
        return 1
    else:
        return 0

def games_pairings_update(req, tournament_id, round_number):
    tournament = Tournament.objects.get(id=tournament_id)
    round_obj = Round.objects.get(tournament=tournament, round=round_number)
    games = Game.objects.filter(round=round_obj).all()
    pairings = [ p.split(':') for p in req.POST['pairings'].split(',') ]
    pairings = [ (t, p.split('v')) for t,p in pairings ]
    for i, g in enumerate(games):
        table, pairing = pairings[i]
        p1_id, p2_id = pairing
        g.table = table
        g.player1 = TournamentPlayer.objects.get(id=p1_id)
        g.player2 = TournamentPlayer.objects.get(id=p2_id)
        g.save()
    return redirect('/gentlemens_gt/games/%s/%s' % (tournament_id,round_number))

def game_update(req):
    element_id = req.POST['id']
    idgame = element_id.split('_')[1]
    player = int(element_id[-1])
    value = int(req.POST['value'].strip())
    if value in (PRIMARY, SECONDARY, TERTIARY, DEFAULT_VICTORY, 0,
                 (PRIMARY+SECONDARY), (PRIMARY+TERTIARY), (SECONDARY+TERTIARY),
                 (PRIMARY+SECONDARY+TERTIARY)):
        game = Game.objects.get(id=idgame)
        if player == 1:
            game.player1_mission_points = value
        elif player == 2:
            game.player2_mission_points = value
        game.save()
        return HttpResponse(str(value), 'text/plain')

def games_delete_round(req, tournament_id, round_number):
    tournament = Tournament.objects.get(id=tournament_id)
    round_obj = Round.objects.get(tournament=tournament, round=round_number)
    round_obj.delete()
    prev_round = int(round_number) - 1
    return redirect('/gentlemens_gt/games/%s/%s' % (tournament_id,prev_round))

def game_notes(req, tournament_id, game_id):
    game = Game.objects.get(id=game_id)
    notes = game.notes.all()
    data = common_page_data(req, tournament_id)
    data['notes'] = notes
    data['id'] = game_id
    data['title'] = '%s v %s (Round %s)' % (
                    game.player1.player.fullname(),
                    game.player2.player.fullname(),
                    game.round.round,
                    )
    data['round'] = game.round.round
    data['form'] = NoteForm()
    data['valid_form'] = True
    data['action'] = '/gentlemens_gt/games/%s/%s/notes/new' % (
            tournament_id, game_id)
    return render_to_response('game_notes.html', data)

def create_game_note(req, tournament_id, game_id):
    form = NoteForm(req.POST)
    game = Game.objects.get(id=game_id)
    if form.is_valid():
        d = form.cleaned_data
        note = Note(note=d['note'], effective_date=d['effective_date'])
        note.save()
        game_note = GameNote(game=game, note=note)
        game_note.save()
        # success redirect
        return redirect ('/gentlemens_gt/games/%s/%s/notes' % (
            tournament_id, game_id))
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['notes'] = player.notes.all()
        data['id'] = game_id
        data['title'] = '%s v %s (Round %s)' % (
                        game.player1.player.fullname(),
                        game.player2.player.fullname(),
                        game.round.round,
                        )
        data['round'] = game.round.round
        data['form'] = form
        data['valid_form'] = False
        data['action'] = '/gentlemens_gt/games/%s/%s/notes/new' % (
                tournament_id, game_id)
        return render_to_response('game_notes.html', data)

#
# standings
#
def standings(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    round_number = req.session.get(
            'tournament_id_%s_round_number' % tournament_id)
    if not round_number:
        try:
            round_number = list(Round.objects.filter(
                    tournament__id=tournament_id).all())[-1].round
        except IndexError:
            round_number = 0
    return redirect('/gentlemens_gt/standings/%s/%s' % (
        tournament_id, round_number))

def standings_list(req, tournament_id, round_number):
    req.session['tournament_id_%s_round_number'] = round_number
    tournament = Tournament.objects.get(id=tournament_id)

    if req.GET.get('include_inactives'):
        include_inactives=True
    else:
        include_inactives=False
    standings = tournament.standings(highest_round=round_number,
                                     include_inactives=include_inactives)
    tplayers = {}
    for s in standings['list']:
        tplayer = s['tplayer']
        tplayers[tplayer.id] = {
                'rank': s['rank'],
                'name': tplayer.player.fullname(),
                'player_id': tplayer.player.id,
                'tplayer_id': tplayer.id,
                'active': tplayer.active,
                'ringer': tplayer.ringer,
                'race': tplayer.armylist.race.name,
                'results': tplayer.results(highest_round=round_number),
                'games': tplayer.games(highest_round=round_number),
                }

    players = []
    notes_count = 0
    for s in standings['list']:
        tp_data = tplayers[s['tplayer'].id]
        games_data = tp_data['games']
        games = []
        for g in games_data:
            if g.round.round == int(round_number):
                notes_count = notes_count + g.notes.count()
            if g.player1.id == tp_data['tplayer_id']:
                opp = g.player2
                opp_mps = g.player2_mission_points
                mps = g.player1_mission_points
            else:
                opp = g.player1
                opp_mps = g.player1_mission_points
                mps = g.player2_mission_points
            if tournament.ranking_method in ('record','battle'):
                if mps > opp_mps:
                    result = 'W'
                elif mps < opp_mps:
                    result = 'L'
                else:
                    result = 'D'
                if tournament.ranking_method == 'battle':
                    if result == 'W':
                        bps = WIN
                    elif result == 'L':
                        bps = LOSS
                    else:
                        bps = DRAW
                    result = '%s pts (%s)' % (bps, result)
            elif tournament.ranking_method == ('mission'):
                result = '%s-%s' % (mps, opp_mps)
            games.append({
                'round': g.round.round,
                'table': g.table,
                'opponent': opp,
                'active': opp.active,
                'ringer': opp.ringer,
                'result': result,
                'notes': g.notes,
                'game_id': g.id,
                })

        #games.reverse()
        p = {'rank': tp_data['rank'],
             'name': tp_data['name'],
             'player_id': tp_data['player_id'],
             'tplayer_id': tp_data['tplayer_id'],
             'active': tp_data['active'],
             'ringer': tp_data['ringer'],
             'race': tp_data['race'],
             'results': tp_data['results'],
             'games': games,
            }
        players.append(p)

    if TournamentPlayer.objects.filter(
            tournament__id=tournament_id, active=False).count():
        inactive_players = True
    else:
        inactive_players = False

    notes_count = notes_count / 2.0 # usually, each game is accessed twice
    if notes_count % 2:
        # inactive players have notes associated with them
        notes_count = int(notes_count) + 1
    else:
        notes_count = int(notes_count)

    form = RoundSelectForm(
            {'round_number':round_number, 'tournament_id':tournament_id})
    data = common_page_data(req, tournament_id)
    data['round'] = round_number
    data['round_select_form'] = form
    data['players' ] = players
    data['player_count'] = len(tournament.players())
    data['ranking_method'] = tournament.ranking_method
    data['inactive_players'] = inactive_players
    data['include_inactives'] = include_inactives
    data['notes_count'] = notes_count
    return render_to_response('standings.html', data)

def standings_printable(req, tournament_id, round_number):
    tournament = Tournament.objects.get(id=tournament_id)
    if req.GET.get('include_inactives'):
        include_inactives=True
    else:
        include_inactives=False
    standings = tournament.standings(highest_round=round_number,
                                     include_inactives=include_inactives)
    players = []
    for s in standings['list']:
        tplayer = s['tplayer']
        players.append({
                'rank': s['rank'],
                'name': tplayer.player.fullname(),
                'active': tplayer.active,
                'ringer': tplayer.ringer,
                'race': tplayer.armylist.race.name,
                'results': tplayer.results(highest_round=round_number),
                })

    data = {'players': players,
            'ranking_method': tournament.ranking_method,
            'round_obj': Round.objects.get(
                        tournament=tournament, round=round_number)
           }
    return render_to_response('standings_printable.html', data)

#
# appearance
#
def appearance(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    return redirect('/gentlemens_gt/appearance/%s' % tournament_id)

def appearance_list(req, tournament_id, template='appearance.html'):
    req.session['tournament_id'] = tournament_id
    tournament = Tournament.objects.get(id=tournament_id)

    if req.GET.get('include_inactives'):
        include_inactives=True
    else:
        include_inactives=False
    results = tournament.appearance_standings(
                                            include_inactives=include_inactives)

    if TournamentPlayer.objects.filter(
            tournament__id=tournament_id, active=False).count():
        inactive_players = True
    else:
        inactive_players = False

    data = common_page_data(req, tournament_id)
    data['appearance_scores'] = results['list']
    data['unrated_players'] = results['unrated_players']
    data['inactive_players'] = inactive_players
    data['include_inactives'] = include_inactives
    return render_to_response(template, data)

def appearance_printable(req, tournament_id):
    return appearance_list(
            req, tournament_id, template='appearance_printable.html')

def appearance_edit(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    try:
        appearance = Appearance.objects.get(player=tplayer)
    except Appearance.DoesNotExist:
        appearance = Appearance(player=tplayer)
        appearance.save()
    data = {'army_basics': appearance.army_basics,
            'bases_basic': appearance.bases_basic,
            'bases_extra': appearance.bases_extra,
            'bases_highlighting_shading': appearance.bases_highlighting_shading,
            'bases_special': appearance.bases_special,
            'painting_basecoat': appearance.painting_basecoat,
            'painting_details': appearance.painting_details,
            'painting_details_quality': appearance.painting_details_quality,
            'painting_freehand': appearance.painting_freehand,
            'painting_highlighting_shading': appearance.painting_highlighting_shading,
            'painting_extra': appearance.painting_extra,
            'conversions': appearance.conversions,
            'objectives': appearance.objectives,
            'display_base': appearance.display_base,
            'something_special': appearance.something_special,
            'favorite_army_votes': appearance.favorite_army_votes,
            'tournament_id': tournament_id,
            }
    form = AppearanceForm(data)
    data = common_page_data(req, tournament_id)
    data['form'] = form
    data['tplayer'] = tplayer
    data['notes_count'] = appearance.notes.count()
    return render_to_response('appearance_edit.html', data)

def appearance_update(req):
    tplayer_id = req.POST['tplayer_id']
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    appearance = Appearance.objects.get(player=tplayer)
    form = AppearanceForm(req.POST)
    if form.is_valid():
        d = form.cleaned_data
        # update Appearance
        appearance.army_basics = d['army_basics']
        appearance.bases_basic = d['bases_basic']
        appearance.bases_extra = d['bases_extra']
        appearance.bases_highlighting_shading = d['bases_highlighting_shading']
        appearance.bases_special = d['bases_special']
        appearance.painting_basecoat = d['painting_basecoat']
        appearance.painting_details = d['painting_details']
        appearance.painting_details_quality = d['painting_details_quality']
        appearance.painting_freehand = d['painting_freehand']
        appearance.painting_highlighting_shading = d['painting_highlighting_shading']
        appearance.painting_extra = d['painting_extra']
        appearance.conversions = d['conversions']
        appearance.objectives = d['objectives']
        appearance.display_base = d['display_base']
        appearance.something_special = d['something_special']
        appearance.favorite_army_votes = d['favorite_army_votes']
        appearance.save()
        # success redirect
        return redirect('/gentlemens_gt/appearance/%s' % tplayer.tournament.id)
    else:
        # return edit form with errors
        data = common_page_data(req, tplayer.tournament.id)
        data['tournament'] = tournament
        data['form'] = form
        data['tplayer'] = tplayer
        data['notes_count'] = appearance.notes.count()
        return render_to_response('appearance_edit.html', data)

def appearance_notes(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    appearance = Appearance.objects.get(player=tplayer)
    notes = appearance.notes.all()
    if tplayer.armylist.description:
        descr = ' (%s)' % tplayer.armylist.description
    else:
        descr = ''
    data = common_page_data(req, tournament_id)
    data['tplayer_id'] = tplayer_id
    data['notes'] = notes
    data['id'] = appearance.id
    data['title'] = "%s's Appearance: %s%s" % (tplayer.player.fullname(),
            tplayer.armylist.race.name, descr)
    data['form'] = NoteForm()
    data['valid_form'] = True
    data['action'] = '/gentlemens_gt/appearance/%s/%s/notes/new' % (
            tournament_id, tplayer_id)
    return render_to_response('appearance_notes.html', data)

def create_appearance_note(req, tournament_id, tplayer_id):
    form = NoteForm(req.POST)
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    appearance = Appearance.objects.get(player=tplayer)
    if form.is_valid():
        d = form.cleaned_data
        note = Note(note=d['note'], effective_date=d['effective_date'])
        note.save()
        appearance_note = AppearanceNote(appearance=appearance, note=note)
        appearance_note.save()
        # success redirect
        return redirect ('/gentlemens_gt/appearance/%s/%s/notes' % (
            tournament_id, tplayer_id))
    else:
        # return form with errors
        if tplayer.armylist.description:
            descr = ' (%s)' % tplayer.armylist.description
        else:
            descr = ''
        data = common_page_data(req, tournament_id)
        data['notes'] = appearance.notes.all()
        data['id'] = appearance.id
        data['title'] = "%s's Appearance: %s%s" % (tplayer.player.fullname(),
                tplayer.armylist.race.name, desscr)
        data['form'] = form
        data['valid_form'] = False
        data['action'] = '/gentlemens_gt/appearance/%s/%s/notes/new' % (
            tournament_id, tplayer_id)
        return render_to_response('appearance_notes.html', data)

#
# sportsmanship
#
def sportsmanship(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    return redirect('/gentlemens_gt/sports/%s' % tournament_id)

def sportsmanship_list(req, tournament_id, template='sportsmanship.html'):
    req.session['tournament_id'] = tournament_id
    tournament = Tournament.objects.get(id=tournament_id)

    if req.GET.get('include_inactives'):
        include_inactives=True
    else:
        include_inactives=False
    results = tournament.sportsmanship_standings(
                                    include_inactives=include_inactives)['list']

    # add sportsmanship details
    base_sports = Sportsmanship.objects.filter(
                    player__tournament__id=tournament_id,
                    rated_by__tournament__id=tournament_id
                    ).all()
    base_sports_positive = {}
    base_sports_positive_rcvd = {}
    base_sports_negative = {}
    base_sports_negative_rcvd = {}
    for bs in base_sports:
        if bs.score > 0:
            players = base_sports_positive.get(bs.rated_by.id, [])
            players.append(bs.player.player.fullname())
            players.sort()
            base_sports_positive[bs.rated_by.id] = players
            players = base_sports_positive_rcvd.get(bs.player.id, [])
            players.append(bs.rated_by.player.fullname())
            players.sort()
            base_sports_positive_rcvd[bs.player.id] = players
        else:
            players = base_sports_negative.get(bs.rated_by.id, [])
            players.append(bs.player.player.fullname())
            players.sort()
            base_sports_negative[bs.rated_by.id] = players
            players = base_sports_negative_rcvd.get(bs.player.id, [])
            players.append(bs.rated_by.player.fullname())
            players.sort()
            base_sports_negative_rcvd[bs.player.id] = players

    black_marks_results = BlackMark.objects.filter(
                            player__tournament__id=tournament_id,
                            rated_by__tournament__id=tournament_id
                            ).all()
    black_marks = {}
    black_marks_rcvd = {}
    for bm in black_marks_results:
        players = black_marks.get(bm.rated_by.id, [])
        players.append(bm.player.player.fullname())
        players.sort()
        black_marks[bm.rated_by.id] = players
        players = black_marks_rcvd.get(bm.player.id, [])
        players.append(bm.rated_by.player.fullname())
        players.sort()
        black_marks_rcvd[bm.player.id] = players

    for r in results:
        tplayer_id = r['player'].id
        r['base_sports_positive'] = ', '.join(
                                    base_sports_positive.get(tplayer_id, []))
        r['base_sports_negative'] = ', '.join(
                                    base_sports_negative.get(tplayer_id, []))
        r['black_marks'] = ', '.join(black_marks.get(tplayer_id, []))
        r['base_sports_positive_rcvd'] = ', '.join(
                                base_sports_positive_rcvd.get(tplayer_id, []))
        r['base_sports_negative_rcvd'] = ', '.join(
                                base_sports_negative_rcvd.get(tplayer_id, []))
        r['black_marks_rcvd'] = ', '.join(black_marks_rcvd.get(tplayer_id, []))

    # ready to render page
    if TournamentPlayer.objects.filter(
            tournament__id=tournament_id, active=False).count():
        inactive_players = True
    else:
        inactive_players = False

    data = common_page_data(req, tournament_id)
    data['sports_scores'] = results
    data['inactive_players'] = inactive_players
    data['include_inactives'] = include_inactives
    return render_to_response(template, data)

def sportsmanship_printable(req, tournament_id):
    return sportsmanship_list(
            req, tournament_id, template='sportsmanship_printable.html')

def sportsmanship_update(req):
    element_id = req.POST['id']
    tplayer_id = element_id.split('_')[1]
    value = int(req.POST['value'].strip())
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    max_round = Round.objects.filter(
                    tournament__id=tplayer.tournament.id
                    ).order_by('-round').all()[0].round
    if value <= max_round:
        tplayer.favorite_opponent_votes = value
        tplayer.save()
        return HttpResponse(str(value), 'text/plain')

def sportsmanship_edit_base(req, player_id, rated_by_id):
    sports = Sportsmanship.objects.get(
                player__id=player_id, rated_by__id=rated_by_id)
    sports.score = req.POST['score']
    sports.save()
    response = {'response':'failure',
                'data':{'msg':('Set sportsmanship for TournamentPlayer %s '
                               'from TournamentPlayer %s to %s.') % (
                                   player_id, rated_by_id, sports.score)
                       }
                }
    return HttpResponse(simplejson.dumps(response), 'application/json')

def sportsmanship_edit_discretionary(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    data = {'judges_discretion_sportsmanship': tplayer.judges_discretion_sportsmanship,
            'judges_discretion_reason': tplayer.judges_discretion_reason,
            }
    form = SportsmanshipDiscretionary(data)
    data = common_page_data(req, tournament_id)
    data['form'] = form
    data['tplayer'] = tplayer
    return render_to_response('sportsmanship_discretionary.html', data)

def sportsmanship_update_discretionary(req):
    tplayer_id = req.POST['id']
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    form = SportsmanshipDiscretionary(req.POST)
    if form.is_valid():
        d = form.cleaned_data
        # update sportsmanship
        tplayer.judges_discretion_sportsmanship = d['judges_discretion_sportsmanship']
        tplayer.judges_discretion_reason = d['judges_discretion_reason']
        tplayer.save()
        # success redirect
        return redirect('/gentlemens_gt/sports/%s' % tplayer.tournament.id)
    else:
        # return edit form with errors
        data = common_page_data(req, tplayer.tournament.id)
        data['form'] = form
        data['tplayer'] = tplayer
        return render_to_response('sportsmanship_discretionary.html', data)

def sportsmanship_edit_blackmarks(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    formdata = {'player':tplayer_id, 'tournament_id':tournament_id}
    form = BlackMarkForm(formdata)
    data = common_page_data(req, tournament_id)
    data['tplayer'] = tplayer
    data['form'] = form
    data['valid_form'] = True
    data['black_marks'] = BlackMark.objects.filter(player=tplayer).all()
    return render_to_response('sportsmanship_blackmarks.html', data)

def sportsmanship_new_blackmark(req):
    tplayer = TournamentPlayer.objects.get(id=req.POST['player'])
    form_data = req.POST.copy()
    form_data['tournament_id'] = tplayer.tournament.id
    form = BlackMarkForm(form_data)
    if form.is_valid():
        d = form.cleaned_data
        rated_by_player = TournamentPlayer.objects.get(id=d['rated_by'])
        blackmark = BlackMark(
                player=tplayer, rated_by=rated_by_player, reason=d['reason'])
        blackmark.save()
        # success redirect
        return redirect('/gentlemens_gt/sports/%s/%s/blackmarks' % (
                                             tplayer.tournament.id, tplayer.id))
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['tplayer'] = tplayer
        data['form'] = form
        data['valid_form'] = False
        data['black_marks'] = BlackMark.objects.filter(player=tplayer).all()
        return render_to_response('sportsmanship_blackmarks.html', data)

def sportsmanship_update_blackmark(req):
    blackmark_id = req.POST['id'].split('_')[2]
    value = req.POST['value'].strip()
    blackmark = BlackMark.objects.get(id=blackmark_id)
    blackmark.reason = value
    blackmark.save()
    data = {'note':blackmark.reason}
    return render_to_response('edited_note_text.html', data)

def sportsmanship_delete_blackmark(req, id):
    try:
        blackmark = BlackMark.objects.get(id=id)
        blackmark.delete()
        response = {'response':'success',
                    'data':{'msg':'Deleted BlackMark with id %s.' % id,
                            'id':id,}
                }
    except:
        response = {'response':'failure',
                    'data':{'msg':'Failed to delete BlackMark with id %s.' % id,
                            'id':id,}
                }
    return HttpResponse(simplejson.dumps(response), 'application/json')


def sportsmanship_notes(req, tournament_id, tplayer_id):
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    data = common_page_data(req, tournament_id)
    data['tplayer_id'] = tplayer_id
    data['notes'] = tplayer.sports_notes().all()
    data['id'] = tplayer.player.id
    data['title'] = "%s's Sportsmanship" % tplayer.player.fullname()
    data['form'] = NoteForm()
    data['valid_form'] = True
    data['action'] = '/gentlemens_gt/sports/%s/%s/notes/new' % (
            tournament_id, tplayer_id)
    return render_to_response('sportsmanship_notes.html', data)

def create_sportsmanship_note(req, tournament_id, tplayer_id):
    form = NoteForm(req.POST)
    tplayer = TournamentPlayer.objects.get(id=tplayer_id)
    if form.is_valid():
        d = form.cleaned_data
        note = Note(note=d['note'], effective_date=d['effective_date'])
        note.save()
        player_note = PlayerNote(player=tplayer.player, note=note)
        player_note.save()
        # success redirect
        return redirect ('/gentlemens_gt/sports/%s/%s/notes' % (
            tournament_id, tplayer_id))
    else:
        # return form with errors
        data = common_page_data(req, tournament_id)
        data['notes'] = tplayer.sports_notes().all()
        data['id'] = tplayer.player.id
        data['title'] = "%s's Sportsmanship" % tplayer.player.fullname()
        data['form'] = form
        data['valid_form'] = False
        data['action'] = '/gentlemens_gt/sports/%s/%s/notes/new' % (
            tournament_id, tplayer_id)
        return render_to_response('sportsmanship_notes.html', data)

#
# overall
#
def overall(req):
    tournament_id = req.session.get('tournament_id')
    if not tournament_id:
        try:
            tournament_id = Tournament.objects.all()[0].id
        except IndexError:
            return redirect('/gentlemens_gt/tournament/0')
    return redirect('/gentlemens_gt/overall/%s' % tournament_id)

def overall_list(req, tournament_id, template='overall.html'):
    req.session['tournament_id'] = tournament_id
    tournament = Tournament.objects.get(id=tournament_id)

    if req.GET.get('include_inactives'):
        include_inactives=True
    else:
        include_inactives=False
    results = tournament.overall_standings(include_inactives=include_inactives)

    if TournamentPlayer.objects.filter(
            tournament__id=tournament_id, active=False).count():
        inactive_players = True
    else:
        inactive_players = False

    data = common_page_data(req, tournament_id)
    data['overall_scores'] = results['list']
    data['inactive_players'] = inactive_players
    data['include_inactives'] = include_inactives
    return render_to_response(template, data)

def overall_printable(req, tournament_id):
    return overall_list(
            req, tournament_id, template='overall_printable.html')

#
# notes
#
def note_update_effective_date(req):
    idnote = req.POST['id'].split('_')[2]
    value = req.POST['value'].strip()
    month, day, year = value.split('/')
    date = datetime.date(int(year), int(month), int(day))
    note = Note.objects.get(id=idnote)
    note.effective_date = date
    note.save()
    return HttpResponse(note.effective_date.strftime('%m/%d/%Y'), 'text/html')

def note_update_note(req):
    idnote = req.POST['id'].split('_')[2]
    value = req.POST['value'].strip()
    note = Note.objects.get(id=idnote)
    note.note = value
    note.save()
    data = {'note':note.note}
    return render_to_response('edited_note_text.html', data)

def note_delete(req, id):
    try:
        note = Note.objects.get(id=id)
        note.delete()
        response = {'response':'success',
                    'data':{'msg':'Deleted Note with id %s.' % id,
                            'id':id,}
                }
    except:
        response = {'response':'failure',
                    'data':{'msg':'Failed to delete Note with id %s.' % id,
                            'id':id,}
                }
    return HttpResponse(simplejson.dumps(response), 'application/json')

