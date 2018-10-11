from crossbot.models import Hat

def init(client):
    parser = client.parser.subparsers.add_parser('hat', help='Put on a hat.')
    parser.set_defaults(command=hat)
    parser.add_argument('-r',
                        '--remove',
                        action='store_true',
                        help='Remove your hat.')
    parser.add_argument('hat',
                        type=str,
                        nargs='?',
                        help='The hat to put on')


def hat(request):
    """Put on a hat that you own, or remove your hat."""
    args = request.args

    if args.remove:
        request.user.doff()
        request.reply("Hat removed.")
        return

    try:
        hat_item = Hat.objects.get(name=args.hat)
    except Hat.DoesNotExist:
        request.reply("{} does not exist".format(args.hat))
        return
    if request.user.don(hat_item):
        request.reply("You donned a {}".format(args.hat))
    else:
        request.reply("You don't own a {}".format(args.hat))

        print("{} put on a {}".format(request.user, args.hat))
