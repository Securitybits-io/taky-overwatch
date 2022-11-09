import logging
import datetime

import xml.etree.ElementTree as ET

# Parameters that describe the map object
# Guide: https://www.mitre.org/sites/default/files/pdf/09_4937.pdf
ATTITUDE = 'f'
DIMENSION = 'G'
HOW = 'm-g'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
STALE_DURATION = 60 #StaleOut 1HOUR
SENDER_UID = 'taky-overwatch'
SENDER_CALLSIGN = 'Headquarters'

def pushCoTLocation(sock, uid, color, role, lat, lon):
    logging.basicConfig(format='%(levelname)s:%(threadName)s:%(message)s', level=logging.DEBUG)

    # Compose message
    message = composeLocation(uid, color, role, lat, lon)
    logging.debug(message.decode("utf-8"))

    # Send message
    sock.send(message)

def composeLocation(uid, color, role, lat, lon):
    # Initialize CoT parameters
    now = datetime.datetime.utcnow()
    start = now.strftime(DATETIME_FORMAT)
    time = now.strftime(DATETIME_FORMAT)
    stale = (now + datetime.timedelta(minutes=STALE_DURATION)).strftime(DATETIME_FORMAT)

    # Build XML
    event = ET.Element('event')
    event.set('version', '2.0')
    event.set('uid', uid)
    event.set('type', "a-{attitude}-{dimension}-U-C".format(attitude=ATTITUDE, dimension=DIMENSION))
    event.set('how', HOW)
    event.set('start', start)
    event.set('time', time)
    event.set('stale', stale)

    detail = ET.SubElement(event, 'detail')
    contact = ET.SubElement(detail, 'contact')
    contact.set('callsign', uid)
    
    remarks = ET.SubElement(detail, 'remarks')

    group = ET.SubElement(detail, '__group')
    group.set('name', color)
    group.set('role', role)

    point = ET.SubElement(event, 'point')
    point.set('le', '0.0')
    point.set('ce', '1.0')
    point.set('hae', '10.0')
    point.set('lat', str(lat))
    point.set('lon', str(lon))

    return ET.tostring(event)