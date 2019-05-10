import datetime
import json
import os

import pandas
from boto.mturk.connection import MTurkConnection
from boto.mturk.price import Price
from boto.mturk.question import ExternalQuestion
from django.conf import settings

from expdj.apps.experiments.models import Experiment
from expdj.settings import BASE_DIR, MTURK_ALLOW


# RESULTS UTILS
def to_dict(input_ordered_dict):
    '''to_dict converts an input ordered dict into a standard dict
    :param input_ordered_dict: the ordered dict
    '''
    return json.loads(json.dumps(input_ordered_dict))


PRODUCTION_HOST = u'mechanicalturk.amazonaws.com'
SANDBOX_HOST = u'mechanicalturk.sandbox.amazonaws.com'

PRODUCTION_WORKER_URL = u'https://www.mturk.com'
SANDBOX_WORKER_URL = u'https://workersandbox.mturk.com'


def amazon_string_to_datetime(amazon_string):
    """Return datetime from passed Amazon format datestring"""

    amazon_iso_format = '%Y-%m-%dT%H:%M:%SZ'
    return datetime.datetime.strptime(
        amazon_string,
        amazon_iso_format)


def get_host(hit):
    """get_host returns correct amazon url depending on if HIT is specified
    for sandbox or not. The variable MTURK_ALLOW is specified in the settings
    as a global control for deployment permissions
    :param hit: the HIT object to check sandbox status for
    """
    if MTURK_ALLOW:
        if hit is not None:
            if hit.sandbox:
                return SANDBOX_HOST
            else:
                return PRODUCTION_HOST
        else:
            return PRODUCTION_HOST
    else:
        return SANDBOX_HOST


def get_debug(hit):
    """get_debug returns 1 or 0 to specify if creating a HIT is in debug mode
    :param hit: the HIT object to check sandbox status for
    """
    if MTURK_ALLOW:
        if hit.sandbox:
            return 1
        else:
            return 0
    else:
        return 1


def is_sandbox():
    """Return True if configuration is configured to connect to sandbox"""

    host = get_host()
    return host == SANDBOX_HOST


def get_worker_url():
    """Get proper URL depending upon sandbox settings"""

    if not settings.MTURK_ALLOW:
        return SANDBOX_WORKER_URL
    else:
        return PRODUCTION_WORKER_URL


def get_credentials(battery):
    """Load credentials from a credentials file"""
    credentials = "%s/expdj/auth/%s" % (BASE_DIR, battery.credentials)
    credentials = pandas.read_csv(
        credentials, sep="=", index_col=0, header=None)
    AWS_ACCESS_KEY_ID = credentials.loc["AWS_ACCESS_KEY_ID"][1]
    AWS_SECRET_ACCESS_KEY_ID = credentials.loc["AWS_SECRET_ACCESS_KEY_ID"][1]
    return AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY_ID


def get_connection(aws_access_key_id, aws_secret_access_key, hit=None):
    """Create connection based upon settings/configuration parameters"""

    host = get_host(hit)
    debug = get_debug(hit)

    return MTurkConnection(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        host=host,
        debug=debug)


def get_app_url():
    if hasattr(settings, 'TURK') and settings.TURK is not None:
        if "app_url" in settings.TURK:
            return settings.TURK["app_url"]


def get_worker_experiments(worker, battery, completed=False):
    '''get_worker_experiments returns a list of experiment objects that
    a worker has/has not completed for a particular battery
    :param completed: boolean, default False to return uncompleted experiments
    '''
    from expdj.apps.turk.models import Result
    battery_tags = [x.template.exp_id for x in battery.experiments.all()]
    worker_experiments = Result.objects.filter(worker=worker, battery=battery)
    worker_tags = [
        x.experiment.exp_id for x in worker_experiments if x.completed]

    if not completed:
        experiment_selection = [
            e for e in battery_tags if e not in worker_tags]
    else:
        experiment_selection = [e for e in worker_tags if e in battery_tags]
    return Experiment.objects.filter(template__exp_id__in=experiment_selection,
                                     battery_experiments__id=battery.id)


def get_time_difference(d1, d2, format='%Y-%m-%d %H:%M:%S'):
    '''calculate difference between two time strings, t1 and t2, returns minutes'''
    if isinstance(d1, str):
        d1 = datetime.datetime.strptime(d1, format)
    if isinstance(d2, str):
        d2 = datetime.datetime.strptime(d2, format)
    return (d2 - d1).total_seconds() / 60
