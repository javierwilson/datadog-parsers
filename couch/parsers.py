import re
import collections
import time
from datetime import datetime

"""
Sample log line:
    2015-10-31 18:32:03,963 [:mvp-pampaida] /a/mvp-pampaida/receiver/630916e49084b142c0a5a69c3a52b9b3/ PUT None d3abf611f2acdc7b4c32f7ebf4982a88 0:00:00.191515
"""

WILDCARD = '*'


def parse_couch_logs(logger, line):
    if not line:
        return None

    try:
        timestamp, domain, url, http_method, status_code, couch_url, request_seconds = _parse_line(line)
    except Exception:
        logger.exception('Failed to parse log line')
        return None

    return ('couch.timings', timestamp, request_seconds, {
        'metric_type': 'gauge',
        'url': url,
        'domain': domain,
        'http_method': http_method,
        'status_code': status_code,
        'couch_url': couch_url,
    })


def _parse_line(line):
    pieces = line.split()
    if len(pieces) == 9:
        # content length added: https://github.com/dimagi/commcare-hq/pull/13542
        date1, date2, domain, url, http_method, status_code, content_length, couch_url, request_time = pieces
    else:
        date1, date2, domain, url, http_method, status_code, couch_url, request_time = pieces

    # Combine the two date parts and then strip off milliseconds because it cannot be parsed by datetime
    string_date = '{} {}'.format(date1, date2).split(',')[0]

    date = datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S")
    timestamp = time.mktime(date.timetuple())

    # Strip off first to letters which are [: and last letter which is a closing ]
    domain = domain[2:-1]

    url = _sanitize_url(url)
    couch_url = _sanitize_couch_url(couch_url)

    hours, minutes, seconds = request_time.split(':')
    request_seconds = float(seconds) + (60 * float(minutes)) + (60 * 60 * float(hours))

    return timestamp, domain, url, http_method, status_code, couch_url, request_seconds


def _sanitize_url(url):
    # Normalize all domain names
    url = re.sub(r'/a/[0-9a-z-]+', '/a/{}'.format(WILDCARD), url)

    # Normalize all urls with indexes or ids
    url = re.sub(r'/modules-[0-9]+', '/modules-{}'.format(WILDCARD), url)
    url = re.sub(r'/forms-[0-9]+', '/forms-{}'.format(WILDCARD), url)
    url = re.sub(r'/form_data/[a-z0-9-]+', '/form_data/{}'.format(WILDCARD), url)
    url = re.sub(r'/uuid:[a-z0-9-]+', '/uuid:{}'.format(WILDCARD), url)
    url = re.sub(r'[-0-9a-f]{10,}', '{}'.format(WILDCARD), url)

    # Remove URL params
    url = re.sub(r'\?[^ ]*', '', url)
    return url


def _sanitize_couch_url(url):
    url = re.sub(r'[0-9a-f]{32}', '{}'.format(WILDCARD), url)

    # Removes dashed uuids
    url = re.sub(r'[-0-9a-f]{36}', '{}'.format(WILDCARD), url)

    return url
