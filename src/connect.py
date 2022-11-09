#!/usr/bin/env python3

import logging
import string
import socket
import ssl
import os
import xmltodict
import zipfile
import requests
import cot

import xml.etree.ElementTree as ET

from threading import Thread
from datetime import datetime
from time import sleep
from queue import Queue
from OpenSSL import crypto

CLIENTURL = os.getenv("CLIENTURL")
MASTERURL = os.getenv("MASTERURL")
COLOR = os.getenv("COLOR", default="Yellow")
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO").upper()

COLORS = [
    'White',
    'Yellow',
    'Orange',
    'Magenta',
    'Red',
    'Maroon',
    'Purple',
    'Dark Blue',
    'Blue',
    'Cyan',
    'Teal',
    'Green',
    'Dark Green',
    'Brown'
    ]


def getCOT(socket, queue):
  logging.info(f'[+] Producer Thread started, waiting on CoTs...')

  while(True):
    rawcot = socket.recv()
    queue.put(rawcot)


def postCOT(master_sock_ssl, queue):
  logging.info(f"[+] Consumer Thread started, waiting on queued CoTs...")
  while(True):
    if queue.empty():
      sleep(5)
    else:
      try:
        row = queue.get()
        rawcot = checkCOT(row.decode("utf-8"))

        if rawcot == False:
          pass
        else:
          cotData = parse_cot(rawcot)
          
          assert COLOR.capitalize() in COLORS
          cotData['tak_color'] = string.capwords(COLOR)
          
          cot.pushCoTLocation(master_sock_ssl, cotData['callsign'], cotData['tak_color'], cotData['tak_role'], cotData['lat'], cotData['lon'])

          logging.debug(f"{ cotData }")
      except UnboundLocalError as e:
        logging.error("msg: %s", e)
      except:
        logging.error('Something went wrong')
        logging.error('Raw Cot: %s', row)
        logging.error('Parsed Cot: %s', cot)
      sleep(0.5)


def checkCOT(cot):
  for start in range(0, len(cot)):
    if cot[start:start+6] == "<event":
      for end in range(start, len(cot)):
        if cot[end:end+8] == "</event>":
          return cot[start:end+8]
  return False


def parse_cot(rawcot):
  dict_cot = xmltodict.parse(rawcot)
  
  if ('a-f-G-U-C' in dict_cot['event']['@type']):
    detail = dict_cot['event']['detail']
    
    time = dict_cot['event']['@time']
    callsign = detail['contact']['@callsign']
    color = detail['__group']['@name']
    role = detail['__group']['@role']
    coords = dict_cot['event']['point']

    utc_time = time.replace("Z","UTC")
    utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%f%Z")
    #YYYY-MM-DD hh:mm:ss
    cot = {
      "time": time,
      "callsign": callsign,
      "tak_color": color,
      "tak_role": role,
      "lat": coords['@lat'],
      "lon": coords['@lon'],
    }

    log = '{} | {} | {} | {} | {} | {}'.format(time, callsign, color, role, coords['@lat'], coords['@lon'])
    logging.debug(f"Formatted CoT: { log }")
  return cot


def download_cert(type, url):
  path = f"/tmp/{ type }_atak.zip"
    
  logging.info(f"Downloading ATAK Certs from { url }")
  
  response = requests.get(url)
  open(path, "wb").write(response.content)

  return path


def connect(type, url):
  listOfFiles = ""
  serverCert = ""
  clientCert = ""
  pref = ""
  certfile  = f"/tmp/{ type }_certs/cert.pem"
  keyfile   = f"/tmp/{ type }_certs/cert.key"
  cot_streams = {}
  app_pref = {}

  zip_path = download_cert(type, url)
  
  with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(f"/tmp/{ type }_certs")
    listOfFiles = zip_ref.namelist()

  for file in listOfFiles:
    if 'server' in file:
      serverCert = f"/tmp/{ type }_certs/"+str(file)
    if 'atak' in file:
      clientCert = f"/tmp/{ type }_certs/"+str(file)
    if 'preference.pref' in file:
      pref = f"/tmp/{ type }_certs/"+str(file)
  
  logging.info(f'Server Cert: { serverCert }')
  logging.info(f'Client Cert: { clientCert }')
  logging.info(f'Preference File: { pref }')

  tree = ET.parse(pref)
  root = tree.getroot()
  for child in root:
    if child.attrib['name'] == 'cot_streams':
      for node in child:
        cot_streams[node.attrib['key']] = node.text

    if child.attrib['name'] == 'com.atakmap.app_preferences':
      for node in child:
        app_pref[node.attrib['key']] = node.text

  IP    = cot_streams['connectString0'].split(':')[0]

  pkcs12_password_bytes = app_pref['clientPassword'].encode('utf8')
  p12   = crypto.load_pkcs12(open(clientCert, "rb").read(), pkcs12_password_bytes)
  
  cert  = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())
  key   = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
  
  with open(certfile, 'wb') as pem_file:
      pem_file.write(cert)

  with open(keyfile, 'wb') as key_file:
      key_file.write(key)

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock_ssl = ssl.wrap_socket(sock, cert_reqs=ssl.CERT_NONE, certfile=certfile, keyfile=keyfile)
  conn = sock_ssl.connect((IP, 8089))

  return sock_ssl, conn


def main():
  logging.basicConfig(format='%(levelname)s:%(threadName)s:%(message)s', level=LOG_LEVEL)
  
  queue = Queue()

  client_sock_ssl, client_conn = connect('client', CLIENTURL)
  
  if (client_sock_ssl._connected == True):
    logging.info(f"[+] Connected to Source TAK Server")
    producer = Thread(target=getCOT, args=(client_sock_ssl, queue))
    producer.start()

  master_sock_ssl, master_conn = connect('master', MASTERURL)

  if (master_sock_ssl._connected == True):
    logging.info(f"[+] Connected to Master TAK Server")
    consumer = Thread(target=postCOT, args=(master_sock_ssl, queue))
    consumer.start()

  return


if __name__ == '__main__':
  main()