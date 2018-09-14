import win32com.client
import time

def startscan(port):
    i = 0
    eng = win32com.client.Dispatch("CAO.CaoEngine")
    ctrl = eng.Workspaces(0).AddController("", "CaoProv.DENSO.QRCode", "", "Conn=com:%s, Mode = 6" % str(port))
    ctrl.Execute("RAW", "U4")
    count = ctrl.AddVariable("@QUEUE_SIZE")
    que = ctrl.AddVariable("@QUEUE")
    ctrl.Execute("RAW", "READON")
    while count.Value <= 0 and i <= 20:
        i += 1
        time.sleep(0.5)
    if count.Value <= 0:
        output = "QR code not found!"
    else:
        output = que.Value
    ctrl.Execute("RAW", "READOFF")
    return output

def multiscan(port, times):
    i = 0
    qr = startscan(port)
    while qr == 'QR code not found!' and i <= times:
        qr = startscan(port)
        i += 1
    if qr == 'QR code not found!':
        raise Exception('Scan failure')
    else:
        return qr