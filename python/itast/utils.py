import json
from collections import namedtuple

def RawToJson(raw):
  try:
    if len(raw) == 0:
      return json.dumps({'Error': 'No data'})
    return json.loads(raw)
  except:
    print json.dumps({'Error': 'Parsing JSON'})

def PrintResponseContents(raw):
  print RawToJson(raw)
