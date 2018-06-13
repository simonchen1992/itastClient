from urllib import urlencode
import requests
import json
import settings

def requestJson(query):
  res = requests.get('http://127.0.0.1:8080' + query)
  return RawToJson(res.text)

def RawToJson(raw):
  try:
    if len(raw) == 0:
      return json.dumps({'Error': 'No data'})
    return json.loads(raw)
  except:
    print json.dumps({'Error': 'Parsing JSON'})

to = {'id_test_session': 281, 'id_card': 271, 'dut': 1, 'pos': '0N', 'verdict': 'P'}
print urlencode(to)

qr1 = requestJson('/qrscan/startscan1' )
print qr1
if qr1 == 'QR code not found!':
  print '22'
  exit()


for tc in range(0,7):
    print tc
    if tc == 2:
        tc = 0
