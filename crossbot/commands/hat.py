import logging
from crossbot.models import Item

logger = logging.getLogger(__name__)

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

    hat_item = Item.from_key(args.hat)

    if not hat_item:
        request.reply("{} does not exist".format(args.hat))
        return

    if request.user.don(hat_item):
        request.reply("You donned a {}".format(args.hat))
    else:
        request.reply("You don't own a {}".format(args.hat))

        logger.info("%s put on a %s", request.user, args.hat)
