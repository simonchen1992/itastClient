import itast.settings
import itast.utils
import requests

# Module used to debugging functions

def PrintTablesData():
  print "log limit=5 order=desc ordefield=timestamp:"
  res = requests.get(itast.settings.ITAST_HOST + '/db/log?limit=5&order=desc&orderfield=timestamp')
  itast.utils.PrintResponseContents(res.text)
  print ""

  print "sessions limit=1:"
  res = requests.get(itast.settings.ITAST_HOST + '/db/sessions?limit=1')
  print res.text
  itast.utils.PrintResponseContents(res.text)
  print ""

  print "cases:"
  res = requests.get(itast.settings.ITAST_HOST + '/db/cases')
  itast.utils.PrintResponseContents(res.text)
  print ""

  print "txs limit=5:"
  res = requests.get(itast.settings.ITAST_HOST + '/db/txs?limit=5')
  itast.utils.PrintResponseContents(res.text)
  print ""

  print "robot goHome:"
  res = requests.get(itast.settings.ITAST_HOST + '/robot/goHome')
  itast.utils.PrintResponseContents(res.text)
  print ""
