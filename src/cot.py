import os
import socket
import ssl
import datetime
import logging
import xml.etree.ElementTree as ET


from OpenSSL import crypto

IP = "bellum.airsoftsweden.com"
PORT = 8089





# Parameters that describe the map object
# Guide: https://www.mitre.org/sites/default/files/pdf/09_4937.pdf
ATTITUDE = 'f'
DIMENSION = 'G'
HOW = 'm-g'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
STALE_DURATION = 60 #StaleOut 1HOUR
SENDER_UID = 'taky-bot'
SENDER_CALLSIGN = 'Headquarters'

def writeCert(filepath, data):
  f = open(filepath, "w")
  f.write(data)
  f.close()

def pushCoTLocation(uid, lat, lon):
    p12 = crypto.load_pkcs12(open("/mnt/d/Development/taky-projects/taky-overwatch/src/atak.p12", "rb").read(), "atakatak")
    logging.basicConfig(format='%(levelname)s:%(threadName)s:%(message)s', level=logging.DEBUG)

    cert   = p12.get_certificate()
    key    = p12.get_privatekey()
    ca     = p12.get_ca_certificates()

    writeCert('cert.pem', cert)
    writeCert('cert.key', key)
    writeCert('ca.pem', ca)

    # Compose message
    message = composeLocation(uid, lat, lon)
    print(message.decode("utf-8"))

    # Send message
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_ssl = ssl.wrap_socket(sock, ca_certs='ca.pem', cert_reqs=ssl.CERT_NONE, certfile='cert.pem', keyfile='cert.key')

    conn = sock_ssl.connect((IP, PORT))
    sock_ssl.send(message)

def composeLocation(uid, lat, lon):
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
    group.set('name', 'Yellow')
    group.set('role', 'Team Member')

    point = ET.SubElement(event, 'point')
    point.set('le', '0.0')
    point.set('ce', '1.0')
    point.set('hae', '10.0')
    point.set('lat', str(lat))
    point.set('lon', str(lon))

    return ET.tostring(event)