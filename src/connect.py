#!/usr/bin/env python3

import logging
import string
import socket
import ssl
import os
import xmltodict
#import cot
import zipfile
import requests

import xml.etree.ElementTree as ET

from threading import Thread
from datetime import datetime
from time import sleep
from queue import Queue
from OpenSSL import crypto

sourceURL = os.getenv("ZIPURL")
clientColor = os.getenv("COLOR")
IP = ""

colors = [
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
  print(f'[+] Producer Thread started, waiting on CoTs...')

  while(True):
    rawcot = socket.recv()
    queue.put(rawcot)


def postCOT(run, queue):
  print(f"[+] Consumer Thread started, waiting on queued CoTs...")
  while(run):
    if queue.empty():
      sleep(5)
    else:
      try:
        row = queue.get()
        rawcot = checkCOT(row.decode("utf-8"))

        if rawcot == False:
          pass
        else:
          cot = parse_cot(rawcot)
          assert clientColor.capitalize() in colors
          cot['tak_color'] = string.capwords(clientColor)
          print(f"{ cot }")
      except:
        print(f"Exception happened")


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
    print(f"Formatted CoT: { log }")
    #logging.debug("Formatted CoT: %s", log)
  return cot




def download_cert():
  path = "/tmp/source_atak.zip"
  URL = sourceURL
  
  print(f"Downloading ATAK Certs from {URL}")
  
  response = requests.get(URL)
  open("/tmp/source_atak.zip", "wb").write(response.content)

  return path


def source_connect():
  listOfFiles = ""
  serverCert = ""
  clientCert = ""
  pref = ""
  certfile  = "/tmp/client_certs/cert.pem"
  keyfile   = "/tmp/client_certs/cert.key"
  cot_streams = {}
  app_pref = {}

  zip_path = download_cert()
  # Connecting to the Sending TAKY through the Cert based approach
  
  with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall("/tmp/client_certs")
    listOfFiles = zip_ref.namelist()

  for file in listOfFiles:
    if 'server' in file:
      serverCert = "/tmp/client_certs/"+str(file)
    if 'atak' in file:
      clientCert = "/tmp/client_certs/"+str(file)
    if 'preference.pref' in file:
      pref = "/tmp/client_certs/"+str(file)
  
  print(f'Server Cert: { serverCert }')
  print(f'Client Cert: { clientCert }')
  print(f'Preference File: { pref }')

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


def server_connect():
  # Connecting to Recieving TAKY through the monitoring port
  return


def main():
  global sourceURL
  global IP
  
  queue = Queue()

  source_sock_ssl, source_conn = source_connect()
  
  if (source_sock_ssl._connected == True):
    print(f"[+] Connected to Source TAK Server")
    producer = Thread(target=getCOT, args=(source_sock_ssl, queue))
    producer.start()

  if (True):
    consumer = Thread(target=postCOT, args=(True, queue))
    consumer.start()

  return


if __name__ == '__main__':
  main()