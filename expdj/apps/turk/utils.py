from boto.mturk.connection import MTurkConnection
from boto.mturk.question import ExternalQuestion
from boto.mturk.price import Price
from numpy.random import choice
import ConfigParser
import datetime
import os

from django.conf import settings

PRODUCTION_HOST = u'mechanicalturk.amazonaws.com'
SANDBOX_HOST = u'mechanicalturk.sandbox.amazonaws.com'

# TODO: this will need to be where our app is hosted
PRODUCTION_WORKER_URL = u'https://www.mturk.com'
SANDBOX_WORKER_URL = u'https://workersandbox.mturk.com'


class InvalidTurkSettings(Exception):
    """Connection settings for Turk are invalid"""
    def __init__(self, value):
        self.parameter = value

    def __unicode__(self):
        return repr(self.parameter)
    __str__ = __unicode__


def amazon_string_to_datetime(amazon_string):
    """Return datetime from passed Amazon format datestring"""

    amazon_iso_format = '%Y-%m-%dT%H:%M:%SZ'
    return datetime.datetime.strptime(
            amazon_string,
            amazon_iso_format)

def get_host():
    """Read configuration file and get proper host

    The host returned will be the contents of either PRODUCTION_HOST or
    PRODUCTION_HOST as defined in this module. Because the host
    parameter is optional, if it is omitted, the PRODUCTION_HOST is
    returned. Therefore, to use the sandbox, one has to explicitly set
    the host parameter to 'mechanicalturk.sandbox.amazonaws.com' in
    either the TURK or TURK_CONFIG_FILE parmeters/files.
    """
    host = PRODUCTION_HOST

    if hasattr(settings, 'TURK') and settings.TURK is not None:

        # Determine if we are in debug mode, set host appropriately
        if "debug" in settings.TURK:
            if settings.TURK["debug"] == 1:
                if "sandbox_host" in settings.TURK:
                    host = settings.TURK["sandbox_host"]
            else:
                if 'host' in settings.TURK:
                    host = settings.TURK['host']


    # A settings file will just be used in production, no debug option
    elif hasattr(settings, 'TURK_CONFIG_FILE') and\
                          settings.TURK_CONFIG_FILE is not None:
        config = ConfigParser.ConfigParser()
        config.read(settings.TURK_CONFIG_FILE)
        if config.has_option('Connection', 'host'):
            host = config.get('Connection', 'host')

    # We don't want any custom URL addresses
    if host.startswith('http://'):
        host = host.replace('http://', '', 1)

    if host.startswith('https://'):
        host = host.replace('https://', '', 1)

    # This will trigger error if user is not using external submit
    assert host in [SANDBOX_HOST, PRODUCTION_HOST]

    return host


def is_sandbox():
    """Return True if configuration is configured to connect to sandbox"""

    host = get_host()
    return host == SANDBOX_HOST


def get_worker_url():
    """Get proper URL depending upon sandbox settings"""

    if is_sandbox():
        return SANDBOX_WORKER_URL
    else:
        return PRODUCTION_WORKER_URL


def get_connection(aws_access_key_id,aws_secret_access_key):
    """Create connection based upon settings/configuration parameters

    The object returned from this function is a Mechanical Turk
    connection object. If the Mechanical Turk Connection object could
    not be created, an InvalidTurkSettings exception is raised.

    The Django settings file should have either the TURK or
    TURK_CONFIG_FILE parameters defined (and not set to None). If both
    are defined (and not None), the TURK parameter takes precedent.

    If the TURK parameter is used in the settings file, it will have a
    syntax similar to the following:

    TURK = {
        'host': 'mturk.com/mturk/externalSubmit',
        'sandbox_host':'workersandbox.mturk.com/mturk/externalSubmit'
        'app_url': 'brainmeta.org'
        'debug': 1
    }

    The host and debug parameters are optional and, if omitted,
    defaults are used. The host is the Amazon Mechanical Turk host with
    which to connect. There are two choices, production or sandbox. If
    omitted, production is used.  Debug is the level of debug
    information printed by the boto library.

    """

    host = get_host()
    debug = 1

    if hasattr(settings, 'TURK') and settings.TURK is not None:
        if 'debug' in settings.TURK:
            debug = settings.TURK['debug']
    else:
        raise InvalidTurkSettings("Turk settings not found")

    return MTurkConnection(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        host=host,
        debug=debug)


def get_app_url():
    if hasattr(settings, 'TURK') and settings.TURK is not None:
        if "app_url" in settings.TURK:
            return settings.TURK["app_url"]

# Should do this properly and add a different question type?
def get_check_questions():
    return [{"question":"I am currently completing an Amazon Mechanical Turk HIT.",
             "answers":["Yes","No"],
             "correct_index":0},
            {"question":"The season that is occurring in the month of December is:",
             "answers":["Spring","Summer","Winter","Fall"],
             "correct_index":2},
            {"question":"When I subtract three from eight (8-3) the answer is:",
             "answers":[1,2,3,4,5,6,7,8,9,10,11],
             "correct_index":4}]


# Selection Algorithms ###############################################################################

def select_experiments_time(maximum_time_allowed,experiments):
    '''select_experiments_time
    a selection algorithm that selects experiments from list based on not exceeding some max time
    :param maximum_time_allowed: the maximum time allowed, in seconds
    :param experiments: list of experiment.Experiment objects, with time variable specified in minutes
    '''
    # Add tasks with random selection until we reach the time limit
    task_list = []
    total_time = 0
    exps = experiments[:]
    while (total_time < maximum_time_allowed) and len(exps)>0:
        # Randomly select an experiment
        experiment = exps.pop(choice(range(len(exps))))
        if (total_time + experiment.template.time*60.0) <= maximum_time_allowed:
            task_list.append(experiment)
    return task_list
