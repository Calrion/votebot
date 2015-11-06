import slacker

from handlers import command_handlers


def lambda_handler(event, context):
    """ This is the function Lambda will call. It uses the collection of command_handlers
    created in the handlers module.
    """
    retval = {}
    param_map = _formparams_to_dict(event['formparams'])
    text = param_map['text'].split('+')

    try:
        handler = command_handlers[text[1]]
        print('Running handler {}'.format(handler.__name__))
        retval = handler(param_map, text)
        print('{} returned {}'.format(handler.__name__, retval))
    except slacker.Error as e:
        retval['text'] = 'Slack responded with error: {}'.format(str(e))
    except Exception as e:
        retval['text'] = 'Error: {}'.format(str(e))

    return retval


def _formparams_to_dict(s1):
    """ Converts the incoming formparams from Slack into a dictionary. Ex: 'text=votebot+ping' """
    retval = {}
    for val in s1.split('&'):
        k, v = val.split('=')
        retval[k] = v
    return retval
