# -*- coding: utf-8 -*-


import json
import time

GAME_WINNER = {1:'GameOneWinner', 2:'GameTwoWinner', 3:'GameThreeWinner'}

def get_bit(n):
    i = 1
    j = 0
    while not n%(i*2):
        i*=2
        j+=1
    return j

def _sort(p):
    return (-p.matches_won, -p.t1, -p.t2, -p.t3)

def _sort_t1(p):
    return (-p.matches_won, -p.t1)

class Player(object):

    def __init__(self, *args, **kwargs):
        self.matches_won = 0
        self.matches_played = 0
        self.mr = 0.0
        self.games_won = 0
        self.games_played = 0
        self.byes = 0
        self.opponents = []
        self.name = kwargs['name']
        self.is_playing = 1
        PLAYERS[self.name]=self

    def update_match_rate(self):
        self.mr = self.get_match_rate()

    def get_match_rate(self, xtra=0):
        return max(1/3.0, (self.matches_won+xtra-self.byes)/1.0/((self.matches_played-self.byes) or 1))

    @property
    def max_t1(self):
        sum_wr, n = 0, 0
        for opp in self.opponents:
            sum_wr += opp.get_match_rate(xtra=opp.is_playing)
            n += 1
        return 100.0*sum_wr/(n or 1)

    @property
    def t1(self):
        sum_wr, n = 0, 0
        for opp in self.opponents:
            sum_wr += opp.mr 
            n += 1
        return 100.0*sum_wr/(n or 1)

    @property
    def t2(self):
        sum_wr, n, u_opp_opp = 0, 0, []
        for opp in self.opponents:
            for opp2 in opp.opponents:
                if opp2 != self: # and opp2 not in u_opp_opp:
                    u_opp_opp.append(opp2)
        for opp in u_opp_opp:
            sum_wr += opp.mr 
            n += 1
        return 100.0*sum_wr/(n or 1)

    @property
    def t3(self):
        return 100.0*self.games_won/(self.games_played or 1)

    @property
    def info(self):
        return ('{:>18} {}/{}'+' {:6.2f}'*4).format(self.name, self.matches_won, self.matches_played, self.t1, self.max_t1, self.t2, self.t3)

class Match(object):

    def __init__(self, *args, **kwargs):
        self.is_bye = False
        self.results = []
        self.is_finished = False
        self.i_round = 0
        self.uid = kwargs['uid']
        self.players = kwargs['players']

    def update_match(self, *args, **kwargs):  # вернем 1 - матч закончен

        if not self.i_round:  # number of round
            for p in self.players:
                p.is_playing = True
                p.matches_played += 1
                p.update_match_rate()

        if self.players[0]==self.players[1]:
            self.is_bye = True
            self.is_finished = True
        else:
            if self.players[0] not in self.players[1].opponents:
                self.players[0].opponents.append(self.players[1])
                self.players[1].opponents.append(self.players[0])

            for gw in [1,2,3]:  # муть на будущее
                if kwargs[GAME_WINNER[gw]]:
                    if len(self.results) < gw:
                        self.results.append(self.players[0] if kwargs[GAME_WINNER[gw]]==self.players[0].name else self.players[1])
                else:
                    break

            if len(self.results) == 2 and self.results[0] == self.results[1]:
                self.is_finished = True
            if len(self.results) == 3:
                self.is_finished = True

        self.i_round = self.players[0].matches_played

        if self.is_finished:
            self.finalize_match()
            return 1

        return 0 

    def finalize_match(self):
        if self.is_bye:
            self.players[0].matches_played -= 1
            self.players[0].matches_won += 1
            self.players[0].byes += 1
            self.players[0].update_match_rate()
            return
        for p in self.players:
            p.matches_won += 1 if p == self.results[-1] else 0
            p.games_played += len(self.results)
            p.games_won += self.results.count(p)
            p.is_playing = 0
            p.update_match_rate()

    def fake_match(self, result):
        if result%2:
            if hasattr(self, 'sim'):
                self.players[self.sim].matches_won -= 1
                del self.sim
            self.is_finished = False
        else:
            if hasattr(self, 'sim'):
                self.players[self.sim].matches_won -= 1
            self.players[1 if result else 0].matches_won += 1
            self.sim = 1 if result else 0
            self.is_finished = True
        for p in self.players:
            p.is_playing = result%2
            p.update_match_rate()

class Tournament(object):

    def __init__(self, *args, **kwargs):
        self.uid = ''
        self.finished_matches = []
        self.ongoing_matches = []
        self.players = {}
        self.n_players = 0
        self.n_rounds = 0
        super(Tournament, self).__init__(*args, **kwargs)

    def create_standings(self, msg):
        self.uid = msg['ID']
        self.finished_matches = []
        players = {p['Name']:Player(name=p['Name']) for p in msg['Players']}
        self.players = players
        self.n_players = len(self.players)
        self.n_rounds = len(bin(self.n_players-1))-2
        self.update_standings(msg=msg)

    def get_standings(self):
        return sorted(self.players.values(), key=_sort)
        
    def get_simulated_top(self): #  only 1st tiebreaker matters
        return sorted(self.players.values(), key=_sort_t1)[:8]

    def create_match(self, *args, **kwargs):
        return Match(uid=kwargs['ID'], players=[self.players[p] for p in (kwargs['PlayerOne'], kwargs['PlayerTwo'])])

    def update_standings(self, msg):
        for g in msg['Games']:
            m = self.create_match(**g)
            if m.update_match(**g):
                self.finished_matches.append(m)
            else:
                self.ongoing_matches.append(m)

    def gps(self, n_matches=15):

        challengers = {}
        output = []
        _ongoing_matches = []
        for m in self.ongoing_matches:
            if not hasattr(m, 'sim'):
               _ongoing_matches.append(m)

        for p in self.players:
            if self.players[p].matches_won + self.players[p].is_playing - self.players[p].matches_played < 3:
                challengers[p]=0

        for m in _ongoing_matches:  # init fake matches
            m.fake_match(0)

        nm = 2**(len(_ongoing_matches) if len(_ongoing_matches)<n_matches else n_matches)  # decreasing processing time

        st = time.time()
        print('simulating {} matches.'.format(nm))

        for p in self.get_simulated_top():
            challengers[p.name] += 1

        for i in xrange(nm-1):  # collecting top 8 of all possible outcomes
            if not i%(nm/20):
                print('{:10} ({:5.2f}%) matches simulated, {:5.2f}s has passed.'.format(i, i*1.0/20/nm, time.time()-st))
            tm = _ongoing_matches[get_bit(i+1)]
            tm.fake_match((tm.sim^1)*2)
            for p in self.get_simulated_top():
                challengers[p.name] += 1

        for m in _ongoing_matches:  # revert fake matches
            m.fake_match(1)

        print('Probabilities for placing in top 8:')
        for p in challengers:
            if challengers[p]:
                print('{:>20} - {:6.2f}'.format(p, challengers[p]*100.0/nm))
                output.append([p, challengers[p]*100.0/nm])

        return sorted(output, key=lambda x: -x[1])


def reload(msg):
    global t
    global MATCHES
    global PLAYERS
    MATCHES = {}
    PLAYERS = {}
    t = Tournament()
    t.create_standings(msg)

