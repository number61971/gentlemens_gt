import datetime
import random
from decimal import Decimal, getcontext

getcontext().prec = 6

from django import forms
from django.contrib.humanize.templatetags import humanize
from django.db import connection
from django.db import models
from django.db import transaction

#
# useful globals
#
@transaction.commit_manually
def execute_sql(sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    try:
        results = cursor.fetchall()
    except ProgrammingError:
        # no results to fetch
        results = None
    cursor.close()
    transaction.commit()
    return results

_races = (
    (0, 'Unknown'),
    (1, 'Black Templars'),
    (2, 'Blood Angels'),
    (3, 'Chaos Daemons'),
    (4, 'Chaos Space Marines'),
    (5, 'Daemonhunters'),
    (6, 'Dark Angels'),
    (7, 'Dark Eldar'),
    (8, 'Eldar'),
    (18, 'Grey Knights'),
    (9, 'Imperial Guard'),
    (10, 'Necrons'),
    (11, 'Orks'),
    (17, 'Sisters of Battle'),
    (12, 'Space Marines'),
    (13, 'Space Wolves'),
    (14, 'Tau Empire'),
    (15, 'Tyranids'),
    (16, 'Witch Hunters'),
)

_race_abbrevs = (
    (0, '--'),
    (1, 'BT'),
    (2, 'BA'),
    (3, 'CD'),
    (4, 'CSM'),
    (5, 'DH'),
    (6, 'DA'),
    (7, 'DE'),
    (8, 'Eld'),
    (18, 'GK'),
    (9, 'IG'),
    (10, 'Nec'),
    (11, 'Ork'),
    (17, 'SoB'),
    (12, 'SM'),
    (13, 'SW'),
    (14, 'TE'),
    (15, 'Tyr'),
    (16, 'WH'),
)

force_org_slots = (
    ('HQ','HQ'),
    ('Elite','Elite'),
    ('Troop','Troop'),
    ('Fast Attack','Fast Attack'),
    ('Heavy Support','Heavy Support'),
    ('Allied HQ','Allied HQ'),
    ('Allied Elite','Allied Elite'),
    ('Allied Troop','Allied Troop'),
    ('Allied Fast Attack','Allied Fast Attack'),
    ('Allied Heavy Support','Allied Heavy Support'),
    ('Fortification','Fortification')
)

_ranking_methods = (
    ('record','W/L/D record'),
    ('battle','Battle points'),
    ('mission','Mission points'),
)

_opponent_pairing_methods = (
    ('swiss','Swiss'),
    ('accelerated swiss', 'Accelerated Swiss'),
    ('random', 'Random'),
)

# battle points
WIN = 3
LOSS = 0
DRAW = 1

# mission points
PRIMARY = 4
SECONDARY = 3
TERTIARY = 2
DEFAULT_VICTORY = 1

# black marks
BLACK_MARK_PENALTY = 2

#
# models
#
class Race(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField('Race', choices=_races, max_length=20)
    abbrev = models.CharField('Race Abbrev', choices=_race_abbrevs,
            max_length=4) 

    def __unicode__(self):
        return self.name


class Tournament(models.Model):
    class Meta:
        ordering = ['-start_date','-end_date','name']

    name = models.CharField('Tournament', max_length=30)
    tagline = models.CharField('Tournament', max_length=128, blank=True,
            default='For one bloodsoaked weekend, there is only war!')
    points_limit = models.IntegerField('Points Limit')
    description = models.TextField('Description', blank=True)
    start_date = models.DateField('Start Date', blank=True, null=True)
    end_date = models.DateField('End Date', blank=True, null=True)
    ranking_method = models.CharField('Ranking Method', default='record',
            choices=_ranking_methods, max_length=24)
    opponent_pairing_method = models.CharField('Opponent Pairing Method',
            default='swiss', choices=_opponent_pairing_methods, max_length=24)

    notes = models.ManyToManyField('Note', through='TournamentNote',
                                   symmetrical=False)

    def players(self):
        return TournamentPlayer.objects.filter(tournament__id=self.id).all()

    def rounds(self):
        return Round.objects.filter(tournament__id=self.id).all()

    def games(self):
        qs = Game.objects.filter(round__tournament__id=self.id)
        return qs.all()

    def standings(self, include_inactives=False, sort=None,
            accelerated_swiss_weighted=False, highest_round=None):
        qs = TournamentPlayer.objects.filter(tournament__id=self.id)
        if include_inactives:
            tplayers = list(qs.all())
        else:
            tplayers = list(qs.filter(active=True).all())

        results = [{'tplayer':tplayer,
                    'results':tplayer.results(
                        accelerated_swiss_weighted=accelerated_swiss_weighted,
                        highest_round=highest_round
                        ),
                   } for tplayer in tplayers]

        if not sort:
            sort = self.ranking_method
        if sort == 'record':
            sortfunc = standings_by_record
        elif sort == 'battle':
            sortfunc = standings_by_battle_points
        elif sort == 'mission':
            sortfunc = standings_by_mission_points
        else:
            raise Exception('"%s" is not a valid tournament standings sort' % sort)
        results.sort(sortfunc)
        rankings_list = []
        rankings_dict = {}
        rank = 1
        for i, r in enumerate(results):
            if highest_round in (0,'0'):
                rank_out = '--'
            else:
                try:
                    result_upper = sortfunc(r, results[i-1])
                except IndexError:
                    result_upper = True
                try:
                    result_lower = sortfunc(r, results[i+1])
                except IndexError:
                    result_lower = True

                if result_upper and result_lower:
                    rank_out = '%s' % rank
                else:
                    rank_out = '%s (tie)' % rank
            rankings_list.append( {'rank':rank_out, 'tplayer':r['tplayer']} )
            rankings_dict[r['tplayer'].id] = {'rank':rank_out,
                                              'ringer':r['tplayer'].ringer}
            if highest_round not in (0,'0') and result_lower:
                rank = i + 2

        return {'list':rankings_list, 'players':rankings_dict}

    def appearance_standings(self, include_inactives=False):
        appearance_scores = Appearance.objects.filter(
                                                 player__tournament__id=self.id)
        if include_inactives:
            appearance_scores = list(appearance_scores.all())
        else:
            appearance_scores = list(appearance_scores.filter(
                                                     player__active=True).all())
        appearance_tplayer_ids = [app.player.id for app in appearance_scores]
        unrated_players = TournamentPlayer.objects.filter(
                            tournament__id=self.id, active=True
                            ).exclude(id__in=appearance_tplayer_ids).all()

        appearance_scores.sort(appearance_ranking)
        rankings_list = []
        rankings_dict = {}
        rank = 1
        for i, a in enumerate(appearance_scores):
            try:
                result_upper = appearance_ranking(a, appearance_scores[i-1])
            except IndexError:
                result_upper = True
            try:
                result_lower = appearance_ranking(a, appearance_scores[i+1])
            except IndexError:
                result_lower = True

            if result_upper and result_lower:
                rank_out = '%s' % rank
            else:
                rank_out = '%s (tie)' % rank
            rankings_list.append( {'rank':rank_out, 'appearance':a} )
            rankings_dict[a.player.id] = {'rank':rank_out, 'appearance':a}
            if result_lower:
                rank = i + 2

        return {'list':rankings_list, 'players':rankings_dict,
                'unrated_players':unrated_players}

    def sportsmanship_standings(self, include_inactives=False):
        tplayers = TournamentPlayer.objects.filter(tournament__id=self.id)
        if include_inactives:
            tplayers = list(tplayers.all())
        else:
            tplayers = list(tplayers.filter(active=True).all())

        tplayers.sort(sportsmanship_ranking)
        rankings_list = []
        rankings_dict = {}
        rank = 1
        for i, p in enumerate(tplayers):
            try:
                result_upper = sportsmanship_ranking(p, tplayers[i-1])
            except IndexError:
                result_upper = True
            try:
                result_lower = sportsmanship_ranking(p, tplayers[i+1])
            except IndexError:
                result_lower = True

            if result_upper and result_lower:
                rank_out = '%s' % rank
            else:
                rank_out = '%s (tie)' % rank
            rankings_list.append( {'rank':rank_out, 'player':p} )
            rankings_dict[p.id] = {'rank':rank_out, 'player':p}
            if result_lower:
                rank = i + 2

        return {'list':rankings_list, 'players':rankings_dict}

    def overall_standings(self, include_inactives=False):
        """
        Simply, the highest overall rank among tournament standings,
        appearance scores, and sportsmanship scores. Equal weight is
        given to each aspect.
        """
        qs = TournamentPlayer.objects.filter(tournament__id=self.id)
        if include_inactives:
            tplayers = list(qs.all())
        else:
            tplayers = list(qs.filter(active=True).all())
        tournament_rankings = self.standings(
                            include_inactives=include_inactives)['players']
        appearance_rankings = self.appearance_standings(
                            include_inactives=include_inactives)['players']
        sports_rankings = self.sportsmanship_standings(
                            include_inactives=include_inactives)['players']

        overall = []
        for tp in tplayers:
            tournament_rank = tournament_rankings[tp.id]['rank']
            try:
                tournament_rank = int(tournament_rank)
            except ValueError: # it's a "(tie)"
                tournament_rank = int(tournament_rank.split(' ')[0])

            result = appearance_rankings.get(tp.id)
            if result:
                appearance_rank = result['rank']
                try:
                    appearance_rank = int(appearance_rank)
                except ValueError: # it's a "(tie)"
                    appearance_rank = int(appearance_rank.split(' ')[0])
            else:
                appearance_rank = len(tplayers)

            sports_rank = sports_rankings[tp.id]['rank']
            try:
                sports_rank = int(sports_rank)
            except ValueError: # it's a "(tie)"
                sports_rank = int(sports_rank.split(' ')[0])

            overall.append({
                       'tplayer':tp,
                       'tournament_rank': tournament_rank,
                       'appearance_rank': appearance_rank,
                       'sports_rank': sports_rank,
                       'ranks_sum':(tournament_rank+appearance_rank+sports_rank)
                           })

        overall.sort(overall_ranking)
        rankings_list = []
        rankings_dict = {}
        rank = 1
        for i, item in enumerate(overall):
            try:
                result_upper = overall_ranking(item, overall[i-1])
            except IndexError:
                result_upper = True
            try:
                result_lower = overall_ranking(item, overall[i+1])
            except IndexError:
                result_lower = True

            if result_upper and result_lower:
                rank_out = '%s' % rank
            else:
                rank_out = '%s (tie)' % rank
            rankings_list.append( {'rank':rank_out, 'player':item} )
            rankings_dict[item['tplayer'].id] = {'rank':rank_out, 'player':item}
            if result_lower:
                rank = i + 2

        return {'list':rankings_list, 'players':rankings_dict}

    def __unicode__(self):
        return '%s: %s players' % (self.name, len(self.players()))


class Player(models.Model):
    class Meta:
        ordering = ['lastname','firstname','midname','suffix']

    firstname = models.CharField('First Name', max_length=100, blank=True)
    midname = models.CharField('Middle Name', max_length=100, blank=True)
    lastname = models.CharField('Last Name', max_length=100, blank=True)
    suffix = models.CharField('Suffix', max_length=100, blank=True)
    addr_number = models.CharField('Address Number', max_length=24, blank=True)
    addr_pre_dir = models.CharField('Address Pre Direction', max_length=2,
            blank=True)
    addr_street = models.CharField('Street Address', max_length=255, blank=True)
    addr_post_dir = models.CharField('Address Post Direction', max_length=2,
            blank=True)
    addr_secondary = models.CharField('Secondary Address', max_length=255,
            blank=True)
    city = models.CharField('City', max_length=48, blank=True)
    state = models.CharField('State', max_length=2, blank=True)
    zip5 = models.CharField('ZIP Code', max_length=5, blank=True) 
    zip4 = models.CharField('ZIP+4', max_length=4, blank=True)
    phone = models.CharField('Phone', max_length=14, blank=True)
    email = models.TextField('Email', blank=True)

    notes = models.ManyToManyField('Note', through='PlayerNote',
                                   symmetrical=False)

    def fullname(self):
        name = []
        for namepiece in (self.firstname, self.midname, self.lastname):
            if namepiece:
                name.append(namepiece)
        name = ' '.join(name)
        if self.suffix:
            name += ', %s' % self.suffix
        return name

    def full_address(self):
        address = ' '.join(s for s in (self.addr_number, self.addr_pre_dir,
                                       self.addr_street, self.addr_post_dir)
                           if s)
        addr_secondary = self.addr_secondary if self.addr_secondary else ''
        zip9 = self.zip5 if not self.zip4 else '%s-%s' % (self.zip5, self.zip4)
        addr = ', '.join(s for s in (address, self.addr_secondary, self.city, 
                                     self.state)
                         if s)
        return '%s %s' % (addr, zip9)

    def phone_pprint(self):
        pn = self.phone
        if len(pn) == 10:
            number =  '(%s) %s-%s' % (pn[:3], pn[3:6], pn[6:])
        else:
            number = pn
        return number

    def tournaments(self):
        return Tournament.objects.filter(
                tournamentplayer__player__id=self.id).all()

    def __unicode__(self):
        return self.fullname()


class TournamentPlayer(models.Model):
    class Meta:
        ordering = ['-tournament__start_date', '-tournament__end_date',
                    'tournament__name', 'player__lastname', 'player__firstname',
                    'player__midname','player__suffix']

    tournament = models.ForeignKey('Tournament')
    player = models.ForeignKey('Player')
    armylist = models.ForeignKey('ArmyList')
    active = models.BooleanField('Active', default=True)
    ringer = models.BooleanField('Ringer', default=False)
    accelerated_swiss_pairing_bonus = models.BooleanField(
            'Accelerated Swiss Pairing Bonus', default=False)
    # sportsmanship fields
    favorite_opponent_votes = models.IntegerField('Favorite Opponent Votes',
            blank=False, default=0)
    judges_discretion_sportsmanship = models.IntegerField("Judge's Discretion",
            blank=False, default=0)
    judges_discretion_reason = models.TextField('Reason', blank=True,
            default='')

    def games(self, highest_round=None):
        qs1 = Game.objects.filter(
                round__tournament__id=self.tournament.id,
                player1__id=self.id
                )
        qs2 = Game.objects.filter(
                round__tournament__id=self.tournament.id,
                player2__id=self.id
                )
        if highest_round:
            qs1 = qs1.filter(round__round__lte=int(highest_round))
            qs2 = qs2.filter(round__round__lte=int(highest_round))
        qs_all = qs1 | qs2
        return qs_all.all()

    def opponents(self, highest_round=None):
        opponents = []
        for game in self.games(highest_round=highest_round):
            if game.player1.id != self.id:
                opponents.append(game.player1)
            else:
                opponents.append(game.player2)
        return opponents

    def results(self, accelerated_swiss_weighted=False, highest_round=None):
        record = {'W':0, 'L':0, 'D':0, 'battle_points':0, 'mission_points':0,
                  'primary_objectives':0, 'secondary_objectives':0,
                  'tertiary_objectives':0}
        for game in self.games(highest_round=highest_round):
            if game.player1.player.id == self.player.id:
                player_mps = game.player1_mission_points
                opp_mps = game.player2_mission_points
            elif game.player2.player.id == self.player.id:
                player_mps = game.player2_mission_points
                opp_mps = game.player1_mission_points
            else:
                raise Exception('ERROR: Wrong games returned for this player.')

            record['mission_points'] += player_mps
            if player_mps in (PRIMARY, (PRIMARY+TERTIARY), (PRIMARY+SECONDARY),
                    (PRIMARY+SECONDARY+TERTIARY)):
                record['primary_objectives'] += 1
            if player_mps in (SECONDARY, (SECONDARY+PRIMARY),
                    (SECONDARY+TERTIARY), (SECONDARY+PRIMARY+TERTIARY)):
                record['secondary_objectives'] += 1
            if player_mps in (TERTIARY, (TERTIARY+PRIMARY),
                    (TERTIARY+SECONDARY), (TERTIARY+PRIMARY+SECONDARY)):
                record['tertiary_objectives'] += 1

            if player_mps > opp_mps:
                record['W'] += 1
                record['battle_points'] += WIN
            elif player_mps < opp_mps:
                record['L'] += 1
                record['battle_points'] += LOSS
            else:
                record['D'] += 1
                record['battle_points'] += DRAW
        
        if accelerated_swiss_weighted and self.accelerated_swiss_pairing_bonus:
            if self.tournament.ranking_method == 'record':
                record['W'] += 1
            elif self.tournament.ranking_method == 'battle':
                record['battle_points'] += WIN
            elif self.tournament.ranking_method == 'mission':
                record['mission_points'] += (PRIMARY+SECONDARY+TERTIARY)

        return record

    def rank(self, highest_round=None):
        return self.tournament.standings(
                    highest_round=highest_round, include_inactives=True
                )['players'][self.id]['rank']

    def appearance_rank(self):
        tournament = Tournament.objects.get(id=self.tournament__id)
        if self.active:
            include_inactives = False
        else:
            include_inactives = True
        rankings = tournament.appearance_standings(
                include_inactives=include_inactives)['players']
        result = rankings.get(self.id)
        if result:
            return result['rank']
        else:
            return 'unrated'

    def base_sportsmanship(self):
        score = Sportsmanship.objects.filter(
                player__id=self.id
                ).aggregate(models.Sum('score'))['score__sum']
        if score is None:
            score = 0
        return score

    def black_marks(self):
        return BlackMark.objects.filter(player__id=self.id).count()

    def sportsmanship_score(self):
        return (self.base_sportsmanship()
                + self.favorite_opponent_votes
                - (self.black_marks() * BLACK_MARK_PENALTY)
                + self.judges_discretion_sportsmanship)

    def sportsmanship_rank(self):
        tournament = Tournament.objects.get(id=self.tournament__id)
        if self.active:
            include_inactives = False
        else:
            include_inactives = True
        return tournament.sportsmanship_standings(
                include_inactives=include_inactives)['players'][self.id]['rank']

    def sports_notes(self):
        qs1 = Note.objects.filter(playernote__player__id=self.player.id)
        qs2 = Note.objects.filter(gamenote__game__player1__id=self.player.id)
        qs3 = Note.objects.filter(gamenote__game__player2__id=self.player.id)
        all_notes = qs1 | qs2 | qs3
        return all_notes

    def __unicode__(self):
        return '%s is participating in %s' % (self.player, self.tournament)


class ArmyList(models.Model):
    description = models.TextField('Description', blank=True)
    race = models.ForeignKey('Race')
    subrace = models.CharField('Subrace', max_length=20, blank=True)

    units = models.ManyToManyField('Unit', through='ArmyListUnit',
                                   symmetrical=False)

    def validate(self):
        if self.race.name != 'Space Wolves':
            max_hq_count = 2
        else:
            max_hq_count = 4
        max_troop_count = 6
        max_elites_count = 3
        max_fast_count = 3
        max_heavy_count = 3
        max_fortification_count = 1

        max_allied_hq_count = 1
        max_allied_troop_count = 2
        max_allied_elites_count = 1
        max_allied_fast_count = 1
        max_allied_heavy_count = 1

        hq_count = self.units.filter(
                    force_org_slot='HQ', occupies_slot=True
                    ).count()
        troop_count = self.units.filter(
                    force_org_slot='Troop', occupies_slot=True
                    ).count() 
        elites_count = self.units.filter(
                    force_org_slot='Elite', occupies_slot=True
                    ).count() 
        fast_count = self.units.filter(
                    force_org_slot='Fast Attack', occupies_slot=True
                    ).count() 
        heavy_count = self.units.filter(
                    force_org_slot='Heavy Support', occupies_slot=True
                    ).count() 
        fortification_count = self.units.filter(
                    force_org_slot='Fortification', occupies_slot=True
                    ).count() 

        allied_hq_count = self.units.filter(
                    force_org_slot='Allied HQ', occupies_slot=True
                    ).count()
        allied_troop_count = self.units.filter(
                    force_org_slot='Allied Troop', occupies_slot=True
                    ).count() 
        allied_elites_count = self.units.filter(
                    force_org_slot='Allied Elite', occupies_slot=True
                    ).count() 
        allied_fast_count = self.units.filter(
                    force_org_slot='Allied Fast Attack', occupies_slot=True
                    ).count() 
        allied_heavy_count = self.units.filter(
                    force_org_slot='Allied Heavy Support', occupies_slot=True
                    ).count() 

        points_total = self.points_total()
        points_limit = self.points_limit()

        if points_limit >= 2000:
            max_hq_count *= 2
            max_troop_count *= 2
            max_elites_count *= 2
            max_fast_count *= 2
            max_heavy_count *= 2
            max_fortification_count *= 2

            max_allied_hq_count *= 2
            max_allied_troop_count *= 2
            max_allied_elites_count *= 2
            max_allied_fast_count *= 2
            max_allied_heavy_count *= 2

        hq_count_legal = hq_count >= 1 and hq_count <= max_hq_count
        troop_count_legal = troop_count >= 2 and troop_count <= max_troop_count
        elites_count_legal = elites_count <= max_elites_count
        fast_count_legal = fast_count <= max_fast_count
        heavy_count_legal = heavy_count <= max_heavy_count
        fortification_count_legal = fortification_count <= max_fortification_count

        allied_hq_count_legal = True
        allied_troop_count_legal = True
        allied_elites_count_legal = True
        allied_fast_count_legal = True
        allied_heavy_count_legal = True
        if allied_hq_count or allied_troop_count or allied_elites_count \
                or allied_fast_count or allied_heavy_count:
            if allied_hq_count > 0 and allied_troop_count == 0:
                allied_troop_count_legal = False
            elif allied_troop_count > 0 and allied_hq_count == 0:
                allied_hq_count_legal = False
            else:
                if allied_hq_count > max_allied_hq_count:
                    allied_hq_count_legal = False
                if allied_troop_count > max_allied_troop_count:
                    allied_troop_count_legal = False
                if allied_elites_count > max_allied_elites_count:
                    allied_elites_count_legal = False
                if allied_fast_count > max_allied_fast_count:
                    allied_fast_count_legal = False
                if allied_heavy_count > max_allied_heavy_count:
                    allied_heavy_count = False

        if points_total <= points_limit and hq_count_legal \
                  and troop_count_legal \
                  and elites_count_legal \
                  and fast_count_legal \
                  and heavy_count_legal \
                  and fortification_count_legal \
                  and allied_hq_count_legal \
                  and allied_troop_count_legal \
                  and allied_elites_count_legal \
                  and allied_fast_count_legal \
                  and allied_heavy_count_legal:
            return (True, [])
        else:
            reasons = []
            if points_total > points_limit:
                reasons.append('List is %s points over the limit' % (
                                points_total - points_limit))

            if not hq_count:
                reasons.append('Requires at least 1 HQ choice')
            elif not hq_count_legal:
                reasons.append('Has %s HQ choices (1 min; %s max)' % (
                                          hq_count, max_hq_count))
            if troop_count < 2:
                reasons.append('Requires at least 2 Troops choices')
            elif troop_count > max_troop_count:
                reasons.append('Has %s Troop choices (2 min; %s max)' % (
                                  min_troop_count, max_troop_count))
            if elites_count > max_elites_count:
                reasons.append('Has %s Elite choices (%s max)' % (
                                  elites_count, max_elites_count))
            if fast_count > max_fast_count:
                reasons.append('Has %s Fast Attack choices (%s max)' % (
                                  fast_count, max_fast_count))
            if heavy_count > max_heavy_count:
                reasons.append('Has %s Heavy Support choices (%s max)' % (
                                  heavy_count, max_heavy_count))

            if fortification_count > max_fortification_count:
                reasons.append('Has %s Fortification choices (%s max)' % (
                                  fortification_count, max_fortification_count))

            if not allied_hq_count_legal:
                if not allied_hq_count:
                    reasons.append('Requires 1 Allied HQ choice')
                else:
                    reasons.append('Has %s Allied HQ choices (1 min; %s max)' % (
                        allied_hq_count, max_allied_hq_count))
            if not allied_troop_count_legal:
                if not allied_troop_count:
                    reasons.append('Requires 1 Allied Troop choice')
                else:
                    reasons.append('Has %s Allied Troop choices (1 min; %s max)' % (
                        allied_troop_count, max_allied_troop_count))
            if not allied_elites_count_legal:
                reasons.append('Has %s Allied Elites choices (%s max)' % (
                                allied_elites_count, max_allied_elites_count))
            if not allied_fast_count_legal:
                reasons.append('Has %s Allied Fast Attack choices (%s max)' % (
                                allied_fast_count, max_allied_fast_count))
            if not allied_heavy_count_legal:
                reasons.append('Has %s Allied Heavy Support choices (%s max)' % (
                                allied_heavy_count, max_allied_heavy_count))

            return (False, reasons)

    def points_limit(self):
        tp = TournamentPlayer.objects.get(armylist__id=self.id)
        return tp.tournament.points_limit

    def points_total(self):
        total = 0
        for unit in self.units.all():
            total += unit.points_cost
        return total

    def get_list(self):
        data = {}
        for slot in [s[0] for s in force_org_slots]:
            data[slot] = []
        for unit in self.units.all():
            data[unit.force_org_slot].append(
                    {'id': unit.id,
                     'points_cost': unit.points_cost,
                     'num_models': unit.num_models,
                     'type': unit.type,
                     'details': unit.details,
                     'occupies_slot': unit.occupies_slot}
                    )
        return data

    def __unicode__(self):
        data = self.get_list()
        out = []
        for slot in [s[0] for s in force_org_slots]:
            units = data[slot]
            if units:
                out.append('\n%s' % slot)
                for unit in units:
                    if unit.num_models > 1:
                        num_models = '%s ' % unit.num_models
                    else:
                        num_models = ''
                    out.append('[%s pts] %s%s: %s' % (
                        humanize.intcomma(unit['points_cost']),
                        num_models, unit['type'], unit['details']
                        ))
        return '%s\n\nTotal: %s' % (
                '\n'.join(out), humanize.intcomma(self.points_total())
                )


class Unit(models.Model):
    class Meta:
        ordering = ['id']

    force_org_slot = models.CharField('Force Org Slot',
            choices=force_org_slots, max_length=13) 
    num_models = models.IntegerField('#', default=1)
    type = models.CharField('Type', max_length=36)
    details = models.TextField('Details', blank=True)
    occupies_slot = models.BooleanField('Occupies Force Org Slot', default=True)
    points_cost = models.IntegerField('Points Cost')

    def __unicode__(self):
        if self.num_models > 1:
            num_models = '%s ' % self.num_models
        else:
            num_models = ''
        return '%s - %s%s: %s [%s pts]' % (self.force_org_slot, num_models,
                self.type, self.details, humanize.intcomma(self.points_cost))


class ArmyListUnit(models.Model):
    armylist = models.ForeignKey('ArmyList')
    unit = models.ForeignKey('Unit')

    def __unicode__(self):
        descr = self.armylist.description
        if descr:
            descr = '%s (%s)' % (descr, self.armylist.race.abbrev)
        else:
            descr = self.armylist.race
        return '%s for %s' % (self.unit.force_org_slot, descr)


class Appearance(models.Model):
    class Meta:
        ordering = ['player__player__lastname', 'player__player__firstname',
                    'player__player__midname','player__player__suffix']

    player = models.ForeignKey('TournamentPlayer')
    army_basics = models.IntegerField('Army Basics', blank=False, null=False,
        default=10)
    bases_basic = models.IntegerField('Based/Detailed', blank=False, null=False,
        default=0)
    bases_extra = models.IntegerField('Extra Basing', blank=False, null=False,
        default=0)
    bases_highlighting_shading = models.IntegerField('Bases Highlighted/Shaded',
        blank=False, null=False, default=0)
    bases_special = models.IntegerField('Special Details', blank=False,
        null=False, default=0)
    painting_basecoat = models.IntegerField('Clean Basecoat', blank=False,
        null=False, default=0)
    painting_details = models.IntegerField('Details Painted', blank=False,
        null=False, default=0)
    painting_details_quality = models.IntegerField('Details Quality',
        blank=False, null=False, default=0)
    painting_freehand = models.IntegerField('Freehand Details', blank=False,
        null=False, default=0)
    painting_highlighting_shading = models.IntegerField('Highlighting/Shading',
        blank=False, null=False, default=0)
    painting_extra = models.IntegerField('Beyond the Basics', blank=False,
        null=False, default=0)
    conversions = models.IntegerField('Conversions', blank=False, null=False,
        default=0)
    objectives = models.IntegerField('Objectives', blank=False, null=False,
        default=0)
    display_base = models.IntegerField('Display Base', blank=False, null=False,
        default=0)
    something_special = models.IntegerField('Something Special', blank=False,
        null=False, default=0)
    favorite_army_votes = models.IntegerField('Favorite Army Votes',
        blank=False, null=False, default=0)

    notes = models.ManyToManyField('Note', through='AppearanceNote',
                                   symmetrical=False)

    def bases(self):
        return (self.bases_basic
                + self.bases_extra
                + self.bases_highlighting_shading
                + self.bases_special)

    def painting(self):
        return (self.painting_basecoat
                + self.painting_details
                + self.painting_details_quality
                + self.painting_freehand
                + self.painting_highlighting_shading
                + self.painting_extra)

    def extras(self):
        return (self.objectives
                + self.display_base
                + self.something_special)

    def total(self):
        return (self.army_basics
                + self.bases()
                + self.painting()
                + self.conversions
                + self.extras())

    def composite_score(self):
        """
        The composite score is 85% appearance judging + 15% player votes.
        """
        judging = Decimal(self.total())
        max_judging = Decimal(45)
        judging_portion = (Decimal(85) * judging) / max_judging

        votes = Decimal(self.favorite_army_votes)
        max_votes = Decimal(TournamentPlayer.objects.filter(
                            tournament__id=self.player.tournament.id,
                            ).count())
        votes_portion = (Decimal(15) * votes) / max_votes
        return judging_portion + votes_portion

    def __unicode__(self):
        return '%s: %s (Appearance)' % (
                                    self.player.player.fullname(), self.total())


class Sportsmanship(models.Model):
    class Meta:
        ordering = ['player__player__lastname', 'player__player__firstname',
                    'player__player__midname', 'player__player__suffix']

    player = models.ForeignKey('TournamentPlayer',
            related_name='rated_player_id')
    rated_by = models.ForeignKey('TournamentPlayer',
            related_name='rated_by_player_id')
    score = models.IntegerField('Sportsmanship', default=0)


class BlackMark(models.Model):
    class Meta:
        ordering = ['player__player__lastname', 'player__player__firstname',
                    'player__player__midname', 'player__player__suffix']

    player = models.ForeignKey('TournamentPlayer',
            related_name='bm_rated_player_id')
    rated_by = models.ForeignKey('TournamentPlayer',
            related_name='bm_rated_by_player_id')
    reason = models.TextField('Reason', blank=True, default='')


class Round(models.Model):
    class Meta:
        ordering = ['-tournament__start_date','-tournament__end_date','round']

    tournament = models.ForeignKey('Tournament')
    round = models.IntegerField('Round')

    def __unicode__(self):
        return '%s: Round %s' % (self.tournament.name, self.round)


class Game(models.Model):
    class Meta:
        ordering = ['-round__tournament__start_date',
                    '-round__tournament__end_date', 'round__round', 'table',
                    #'player1__player__lastname', 'player2__player__lastname'
                    ]

    round = models.ForeignKey('Round')
    player1 = models.ForeignKey('TournamentPlayer', related_name='player1_id')
    player1_mission_points = models.IntegerField('Player 1 Mission Points',
            default=0)
    player2 = models.ForeignKey('TournamentPlayer', related_name='player2_id')
    player2_mission_points = models.IntegerField('Player 2 Mission Points',
            default=0)
    table = models.IntegerField('Table', blank=True, null=True)

    notes = models.ManyToManyField('Note', through='GameNote',
                                   symmetrical=False)

    def result(self):
        if self.player1_mission_points > self.player2_mission_points:
            return self.player1
        elif self.player1_mission_points < self.player2_mission_points:
            return self.player2
        else:
            return None

    def __unicode__(self):
        return 'Table %s: %s v %s' % (self.table, self.player1.player.fullname(), self.player2.player.fullname())


class Note(models.Model):
    class Meta:
        ordering = ['-effective_date', 'id']
    
    note = models.TextField('Note')
    effective_date = models.DateField('Effective Date', blank=True, null=True)

    def __unicode__(self):
        return '[%s] %s' % (self.effective_date.strftime('%m/%d/%Y'), self.note)


class TournamentNote(models.Model):
    tournament = models.ForeignKey('Tournament')
    note = models.ForeignKey('Note')

    def __unicode__(self):
        return 'Note %s for %s' % (self.note.id, self.tournament)


class PlayerNote(models.Model):
    player = models.ForeignKey('Player')
    note = models.ForeignKey('Note')

    def __unicode__(self):
        return 'Note %s for %s' % (self.note.id, self.player)


class GameNote(models.Model):
    game = models.ForeignKey('Game')
    note = models.ForeignKey('Note')

    def __unicode__(self):
        return 'Note %s for %s' % (self.note.id, self.game)


class AppearanceNote(models.Model):
    appearance = models.ForeignKey('appearance')
    note = models.ForeignKey('Note')

    def __unicode__(self):
        return 'Note %s for %s' % (self.note.id, self.appearance)


#
# TournamentPlayer ranking sorts
#
def standings_by_record(p1, p2):
    if p1['results']['W'] > p2['results']['W']:
        return -1
    if p1['results']['W'] < p2['results']['W']:
        return 1
    if p1['results']['D'] > p2['results']['D']:
        return -1
    if p1['results']['D'] < p2['results']['D']:
        return 1
    if p1['results']['mission_points'] > p2['results']['mission_points']:
        return -1
    if p1['results']['mission_points'] < p2['results']['mission_points']:
        return 1
    if p1['results']['primary_objectives'] > p2['results']['primary_objectives']:
        return -1
    if p1['results']['primary_objectives'] < p2['results']['primary_objectives']:
        return 1
    if p1['results']['secondary_objectives'] > p2['results']['secondary_objectives']:
        return -1
    if p1['results']['secondary_objectives'] < p2['results']['secondary_objectives']:
        return 1
    if p1['results']['tertiary_objectives'] > p2['results']['tertiary_objectives']:
        return -1
    if p1['results']['tertiary_objectives'] < p2['results']['tertiary_objectives']:
        return 1
    return 0

def standings_by_battle_points(p1, p2):
    if p1['results']['battle_points'] > p2['results']['battle_points']:
        return -1
    if p1['results']['battle_points'] < p2['results']['battle_points']:
        return 1
    if p1['results']['W'] > p2['results']['W']:
        return -1
    if p1['results']['W'] < p2['results']['W']:
        return 1
    if p1['results']['mission_points'] > p2['results']['mission_points']:
        return -1
    if p1['results']['mission_points'] < p2['results']['mission_points']:
        return 1
    if p1['results']['primary_objectives'] > p2['results']['primary_objectives']:
        return -1
    if p1['results']['primary_objectives'] < p2['results']['primary_objectives']:
        return 1
    if p1['results']['secondary_objectives'] > p2['results']['secondary_objectives']:
        return -1
    if p1['results']['secondary_objectives'] < p2['results']['secondary_objectives']:
        return 1
    if p1['results']['tertiary_objectives'] > p2['results']['tertiary_objectives']:
        return -1
    if p1['results']['tertiary_objectives'] < p2['results']['tertiary_objectives']:
        return 1
    return 0

def standings_by_mission_points(p1, p2):
    if p1['results']['mission_points'] > p2['results']['mission_points']:
        return -1
    if p1['results']['mission_points'] < p2['results']['mission_points']:
        return 1
    if p1['results']['W'] > p2['results']['W']:
        return -1
    if p1['results']['W'] < p2['results']['W']:
        return 1
    if p1['results']['battle_points'] > p2['results']['battle_points']:
        return -1
    if p1['results']['battle_points'] < p2['results']['battle_points']:
        return 1
    if p1['results']['primary_objectives'] > p2['results']['primary_objectives']:
        return -1
    if p1['results']['primary_objectives'] < p2['results']['primary_objectives']:
        return 1
    if p1['results']['secondary_objectives'] > p2['results']['secondary_objectives']:
        return -1
    if p1['results']['secondary_objectives'] < p2['results']['secondary_objectives']:
        return 1
    if p1['results']['tertiary_objectives'] > p2['results']['tertiary_objectives']:
        return -1
    if p1['results']['tertiary_objectives'] < p2['results']['tertiary_objectives']:
        return 1
    return 0


#
# opponent pairing functions
#
def opponent_pairing_swiss(ranked_player_list, round_num):
    # methodology derived from http://en.wikipedia.org/wiki/Swiss_pairing
    if round_num == 1:
        return opponent_pairing_random(ranked_player_list)
    # attempt straight pairings down the rankings list
    list_copy = ranked_player_list[:]
    pairings = []
    failures = 0
    while list_copy:
        p1 = list_copy.pop(0)
        p1_opp_ids = [p.id for p in p1.opponents()] 
        i = 0
        try:
            while True:
                if list_copy[i].id not in p1_opp_ids:
                    p2 = list_copy.pop(i)
                    pairings.append((p1,p2))
                    break
                i += 1
        except IndexError:
            # final pairings not possible because of opponent repetition
            # break off last pairing(s) and split them up until it works
            list_copy.insert(0, p1)
            failures += 1
            prev_pairs = []
            for x in range(0,failures):
                pairing = pairings.pop()
                list_copy.insert(0, pairing[0])
                list_copy.append(pairing[1])

    return pairings

def opponent_pairing_accelerated_swiss(ranked_player_list, round_num):
    # methodology derived from http://en.wikipedia.org/wiki/Swiss_pairing
    # Note that the ranked_player_list received by this function for rounds 2
    # and 3 should already have been sorted according to the pairing weight 
    # bonuses required by the methodology. Normal (i.e., "actual") results
    # sorting should be used for any rounds NOT the 2nd or 3rd.
    if round_num == 1:
        return opponent_pairing_random(ranked_player_list)
    elif round_num > 2:
        return opponent_pairing_swiss(ranked_player_list, round_num)
    elif round_num == 2:
        top_half_divider = int(len(ranked_player_list)/4)
        q1 = ranked_player_list[:top_half_divider]
        q2 = ranked_player_list[top_half_divider:(2*top_half_divider)]
        bottom_half = ranked_player_list[(2*top_half_divider):]
        bottom_half_divider = int(len(bottom_half)/2)
        q3 = bottom_half[:bottom_half_divider]
        q4 = bottom_half[bottom_half_divider:]
        new_list = []
        for i, player in enumerate(q1):
            new_list.append(player)
            new_list.append(q2[i])
        for i, player in enumerate(q3):
            new_list.append(player)
            new_list.append(q4[i])
        if len(new_list) == len(ranked_player_list):
            return opponent_pairing_swiss(new_list, round_num)
        else:
            raise Exception('Round 2 accelerated Swiss pairing list (%s players) does not match actual player list (%s players).' % (len(new_list), len(ranked_player_list)))

def opponent_pairing_random(player_list, round_num=None):
    # The round_num argument is there just to keep the API for all the pairing
    # functions identical.
    r = random.SystemRandom()
    pairings_list = player_list[:]
    r.shuffle(pairings_list)
    return opponent_pairing_swiss(pairings_list, None)

#
# Appearance ranking sort
#
def appearance_ranking(a1, a2):
    if a1.composite_score() > a2.composite_score():
        return -1
    elif a1.composite_score() < a2.composite_score():
        return 1
    elif a1.total() > a2.total():
        return -1
    elif a1.total() < a2.total():
        return 1
    elif a1.extras() > a2.extras():
        return -1
    elif a1.extras() < a2.extras():
        return 1
    elif a1.favorite_army_votes > a2.favorite_army_votes:
        return -1
    elif a1.favorite_army_votes < a2.favorite_army_votes:
        return 1
    else:
        return 0

#
# sportsmanship ranking sort
#
def sportsmanship_ranking(p1, p2):
    if p1.sportsmanship_score() > p2.sportsmanship_score():
        return -1
    elif p1.sportsmanship_score() < p2.sportsmanship_score():
        return 1
    elif p1.black_marks() > p2.black_marks():
        return 1
    elif p1.black_marks() < p2.black_marks():
        return -1
    elif p1.favorite_opponent_votes > p2.favorite_opponent_votes:
        return -1
    elif p1.favorite_opponent_votes < p2.favorite_opponent_votes:
        return 1
    elif p1.base_sportsmanship() > p2.base_sportsmanship():
        return -1
    elif p1.base_sportsmanship() > p2.base_sportsmanship():
        return 1
    elif p1.judges_discretion_sportsmanship > p2.judges_discretion_sportsmanship:
        return -1
    elif p1.judges_discretion_sportsmanship < p2.judges_discretion_sportsmanship:
        return 1
    else:
        return 0

#
# overall ranking sort
#
class AppearanceExtrasProxy:
    def extras(self):
        return 0

def overall_ranking(p1, p2):
    if p1['ranks_sum'] > p2['ranks_sum']:
        return 1
    elif p1['ranks_sum'] < p2['ranks_sum']:
        return -1
    elif p1['tplayer'].black_marks() > p2['tplayer'].black_marks():
        return 1
    elif p1['tplayer'].black_marks() < p2['tplayer'].black_marks():
        return -1
    elif p1['tplayer'].judges_discretion_sportsmanship > p2['tplayer'].judges_discretion_sportsmanship:
        return -1
    elif p1['tplayer'].judges_discretion_sportsmanship < p2['tplayer'].judges_discretion_sportsmanship:
        return 1
    else:
        try:
            p1_appearance = Appearance.objects.get(player__id=p1['tplayer'].id)
        except Appearance.DoesNotExist:
            p1_appearance = AppearanceExtrasProxy()
        try:
            p2_appearance = Appearance.objects.get(player__id=p2['tplayer'].id)
        except Appearance.DoesNotExist:
            p2_appearance = AppearanceExtrasProxy()
        if p1_appearance.extras() > p2_appearance.extras():
            return -1
        elif p1_appearance.extras() < p2_appearance.extras():
            return 1
        else:
            p1_record = p1['tplayer'].results()
            p2_record = p2['tplayer'].results()
            if p1_record['W'] > p2_record['W']:
                return -1
            elif p1_record['W'] < p2_record['W']:
                return 1
            else:
                return 0

#
# forms
#
def get_tournaments():
    tournaments = []
    for t in Tournament.objects.all():
        tournaments.append((str(t.id), t.name))
    return tournaments

class TournamentChoice(forms.Form):
    tournament = forms.ChoiceField(label="Tournament", choices=[('','')])

    def __init__(self, *args, **kwargs):
        # hackery to force fresh listing of tournaments
        # each time this form is rendered
        super(TournamentChoice, self).__init__(*args, **kwargs)
        self.fields['tournament'].choices = get_tournaments()

class TournamentForm(forms.Form):
    name = forms.CharField(label='Tournament', max_length=30)
    tagline = forms.CharField(label='Tagline', max_length=128, required=False)
    points_limit = forms.IntegerField(label='Points Limit', initial=2000)
    description = forms.CharField(label='Description', required=False)
    start_date = forms.DateField(label='Start Date', required=False,
            widget=forms.DateInput(format='%m/%d/%Y'))
    end_date = forms.DateField(label='End Date', required=False,
            widget=forms.DateInput(format='%m/%d/%Y'))
    ranking_method = forms.ChoiceField(label='Ranking Method', initial='record',
            choices=_ranking_methods)
    opponent_pairing_method = forms.ChoiceField(label='Opponent Pairing Method',
            initial='swiss', choices=_opponent_pairing_methods)


class PlayerForm(forms.Form):
    firstname = forms.CharField(label='First Name', max_length=100, 
        widget=forms.TextInput(attrs={'title':'First name'}), required=False)
    midname = forms.CharField(label='Middle Name', max_length=100, 
        widget=forms.TextInput(attrs={'title':'Middle name'}), required=False)
    lastname = forms.CharField(label='Last Name', max_length=100, 
        widget=forms.TextInput(attrs={'title':'Last name'}), required=False)
    suffix = forms.CharField(label='Suffix', max_length=100, required=False,
        widget=forms.TextInput(attrs={'title':'Suffix (e.g., "Jr", "III")'}))
    addr_number = forms.CharField(label='Address Number', max_length=24,
            widget=forms.TextInput(attrs={'title':'Address number'}),        
            required=False)
    addr_pre_dir = forms.CharField(label='Address Pre Direction', max_length=2,
            widget=forms.TextInput(attrs={'title':'Pre direction (e.g., "N")'}),
            required=False)
    addr_street = forms.CharField(label='Street Address', max_length=255,
            widget=forms.TextInput(attrs={'title':'Street (e.g., "Main St")'}),
            required=False)
    addr_post_dir = forms.CharField(label='Address Post Direction', 
            widget=forms.TextInput(attrs={'title':'Post direction (e.g., "W")'}),
            max_length=2, required=False)
    addr_secondary = forms.CharField(label='Secondary Address', max_length=255,
            widget=forms.TextInput(attrs={'title':'Addr line 2 (e.g., "Apt 1")'}),
            required=False)
    city = forms.CharField(label='City', max_length=48, required=False,
            widget=forms.TextInput(attrs={'title':'City'}))
    state = forms.CharField(label='State', max_length=2, required=False,
            widget=forms.TextInput(attrs={'title':'State'}))        
    zip5 = forms.CharField(label='ZIP Code', max_length=5, required=False,
            widget=forms.TextInput(attrs={'title':'ZIP (first 5 digits)'})) 
    zip4 = forms.CharField(label='ZIP+4', max_length=4, required=False,
            widget=forms.TextInput(attrs={'title':'ZIP+4'}))
    phone = forms.CharField(label='Phone', max_length=14, required=False)
    email = forms.CharField(label='Email', required=False)


class ArmyListForm(forms.Form):
    description = forms.CharField(label='Description', required=False)
    race = forms.ChoiceField(label='Race', choices=_races)
    subrace = forms.CharField(label='Subrace', max_length=20, required=False)


class UnitForm(forms.Form):
    force_org_slot = forms.ChoiceField(label='Force Org Slot',
            choices=force_org_slots, initial="Troop") 
    num_models = forms.IntegerField(label='#', initial=1)
    type = forms.CharField(label='Type', max_length=36)
    details = forms.CharField(label='Details', required=False)
    occupies_slot = forms.BooleanField(label='Occupies Force Org Slot',
            initial=True, required=False)
    points_cost = forms.IntegerField(label='Points Cost')


def build_rounds(tournament_id):
    rounds = Round.objects.filter(tournament__id=tournament_id).all()
    return [(r.round, r.round) for r in rounds]

class RoundSelectForm(forms.Form):
    round_number = forms.ChoiceField(label='Round', choices=[('','')])

    def __init__(self, *args, **kwargs):
        # hackery to force fresh listing of rounds
        # each time this form is rendered
        super(RoundSelectForm, self).__init__(*args, **kwargs)
        args_dict = args[0]
        self.fields['round_number'].choices = build_rounds(
                                                args_dict['tournament_id'])

class AppearanceForm(forms.Form):
    army_basics = forms.IntegerField(label='Army Basics',
        widget=forms.Select(choices=[
('0','0: Army is more primer or bare plastic and metal than paint'),
('5','5: Most, but not all, of the army has been painted to a minimal standard'),
('10','10: The army is fully painted to the three-color standard'),
('15','15: Effort beyond basecoating to three colors is clearly evident'),
        ]))

    bases_basic = forms.IntegerField(label='Based/Detailed',
            widget=forms.Select(choices=[('0','0: No'),('1','1: Yes')]))

    bases_extra = forms.IntegerField(label='Extra Basing',
            widget=forms.Select(choices=[('0','0: No'),('1','1: Yes')]))

    bases_highlighting_shading = forms.IntegerField(
        label='Bases Highlighted/Shaded', widget=forms.Select(
            choices=[('0','0: No'),('1','1: Yes')]))

    bases_special = forms.IntegerField(label='Special Details',
            widget=forms.Select(choices=[
       ('0','0: Very few (or none) of the bases have extra detailing, including highlighting/shading'),
       ('1',"1: A noticeable portion of the army's bases have extra detailing, including highlighting/shading"),
       ('2',"2: A significant majority of the bases have extra detailing, including highlighting/shading"),
                ]))

    painting_basecoat = forms.IntegerField(label='Clean Basecoat',
            widget=forms.Select(choices=[('0','0: No'),('1','1: Yes')]))

    painting_details = forms.IntegerField(label='Details Painted',
            widget=forms.Select(choices=[('0','0: No'),('1','1: Yes')]))

    painting_details_quality = forms.IntegerField(label='Details Quality',
            widget=forms.Select(choices=[
                ('0','0: Details are painted, but are not remarkable'),
                ('1','1: Details are clean and noticeable'),
                ('2','2: Details have their own highlighting/shading'),
                ]))

    painting_freehand = forms.IntegerField(label='Freehand Details',
            widget=forms.Select(choices=[
               ('0','0: Very little to no freehand details'),
               ('1','1: Freehand detailing is evident in portions of the army'),
               ('2','2: Freehand detailing is common or very well executed'),
               ]))

    painting_highlighting_shading = forms.IntegerField(
            label='Highlighting/Shading',
            widget=forms.Select(choices=[
('0','0: Very little to no highlighting/shading'),
('1','1: Highlighting/shading is evident in most of the army'),
('2','2: Highlighting/shading is on nearly every model and very well executed'),
                ]))

    painting_extra = forms.IntegerField(label='Beyond the Basics',
            widget=forms.Select(choices=[
('0','0: Nothing special'),
('1','1: Some to several models display advanced techniques (e.g., blending, layering)'),
('2','2: Most models have been painted with well executed advanced techniques'),
                ]))

    conversions = forms.IntegerField(label='Conversions',
            widget=forms.Select(choices=[
('0','0: Almost nothing but stock GW kits'),
('2','2: Some elementary conversions (e.g., arm/head swaps, minor reposing)'),
('4','4: Most units display at least a few basic conversions'),
('6','6: At least half the army has been converted OR the army contains a few major conversions (e.g., sculpting, plasticard, multi-kit swaps)'),
('8','8: Most of the army has been modified from stock GW and/or major conversions are common'),
('10','10: Almost the entire army has been converted OR army includes outstanding full sculpts/truly impressive scratch builds'),
            ]))

    objectives = forms.IntegerField(label='Objectives',
            widget=forms.Select(choices=[
('0','0: Modeled objectives were not supplied (e.g., player used poker chips)'),
('1','1: Converted and painted models representing objectives were supplied'),
                ]))

    display_base = forms.IntegerField(label='Display Base',
            widget=forms.Select(choices=[
        ('0','0: No display base supplied'),
        ('1','1: Player modeled a display base for the army'),
                ]))

    something_special = forms.IntegerField(label='Something Special',
            widget=forms.Select(choices=[
   ('0','0: Regardless of execution, army lacks real impact/exemplary quality'),
   ('1','1: The army noticeably stands out from the crowd'),
   ('2','2: The army displays several outstanding and memorable features'),
   ('3','3: The army is one of the best presentations at this or any event'),
                ]))

    favorite_army_votes = forms.IntegerField(label='Favorite Army Votes')


class SportsmanshipDiscretionary(forms.Form):
    judges_discretion_sportsmanship = forms.IntegerField(
            label="Judge's Discretion", initial=0)
    judges_discretion_reason = forms.CharField(label='Reason', required=False,
            widget=forms.Textarea())


class BlackMarkForm(forms.Form):
    player = forms.IntegerField(label='Player', widget=forms.HiddenInput())
    rated_by = forms.IntegerField(label='Given by',
            widget=forms.Select(choices=[('','')]))
    reason = forms.CharField(label='Reason', required=False,
            widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        # hackery to force fresh listing of players
        # each time this form is rendered
        super(BlackMarkForm, self).__init__(*args, **kwargs)
        form_args = args[0]
        tournament_id = form_args['tournament_id']
        tplayer_id = form_args['player']
        tplayers = TournamentPlayer.objects.filter(
            tournament__id=tournament_id
            ).exclude(id=tplayer_id).all()
        player_options = [(tp.id, tp.player.fullname()) for tp in tplayers]
        self.fields['rated_by'].widget.choices = player_options


class NoteForm(forms.Form):
    effective_date = forms.DateField(label='Effective Date', required=False,
            widget=forms.DateInput(format='%m/%d/%Y'),
            initial=datetime.date.today)
    note = forms.CharField(label='Note', widget=forms.Textarea())

