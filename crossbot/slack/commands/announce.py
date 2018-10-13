from django.utils import timezone

import crossbot

def init(client):

    parser = client.parser.subparsers.add_parser(
        'announce', help='Announce any streaks.')
    parser.set_defaults(command=announce)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to announce for.')

def best(table, date, offset=0):
    # offset_s = '-{} days'.format(offset)
    # query = '''
    # WITH date_times
    # AS (SELECT *
    #     FROM {}
    #     WHERE date = date(?, ?) AND seconds >=0)
    # SELECT userid
    # FROM date_times
    # WHERE seconds = (SELECT min(seconds) FROM date_times)
    # '''.format(table)

    # result = con.execute(query, (date, offset_s)).fetchall()
    offset = timezone.timedelta(days=offset)

    times_for_date = table.objects.filter(date = date - offset, seconds__gte = 0)
    best_time = min(t.seconds for t in times_for_date)

    # get the actual userid's out of the tuple
    return set(t.user for t in times_for_date if t.seconds == best_time)


def announce(request):
    '''Report who won the previous day and if they're on a streak.
    Optionally takes a date.'''

    m = ""

    date = request.args.date
    table = request.args.table

    best1 = best(table, date, 1)
    best2 = best(table, date, 2)
    streaks = best1 & best2

    def fmt(best_set):
        return ' and '.join(str(user) for user in best_set)

    if not best1:
        m += 'No one played the minicrossword yesterday. Why not?\n'
    elif not streaks:
        # empty intersection means no streak
        assert best1
        m += 'Yesterday, {} solved the minicrossword fastest.\n'\
                .format(fmt(best1))
        if best2:
            m += '{} won the day before.\n'\
                    .format(fmt(best2))
    else:
        assert streaks
        # sorry, but tracking multiple winning streaks is too hard and
        # is very unlikely
        best_uid = list(streaks)[0]
        n = 2
        while best_uid in best(con, table, date, n+1): n += 1
        m += '{} is on a {}-day streak! {}\nCan they keep it up?\n'\
                .format(client.user(best_uid), n, ':fire:' * n)

    games = { "mini crossword" : "https://www.nytimes.com/crosswords/game/mini"
            , "easy sudoku"    : "https://www.nytimes.com/crosswords/game/sudoku/easy"
            }

    m += "Play today's:"
    for g in games:
        m += "\n{} : {}".format(g, games[g])

    request.reply(m)
