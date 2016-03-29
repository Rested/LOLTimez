import sys
from PyQt4 import QtGui, QtCore
import time
import psutil
import requests
import urllib
from PIL import Image, ImageEnhance
import tailer
import math
import threading
import json


with open('config.json') as data_file:
    config = json.load(data_file)

API_KEY = config["API_KEY"]
SUMMONER_NAME = config["SUMMONER_NAME"]
REGION = config["REGION"]
PLATFORM_ID = config["PLATFORM_ID"]
DOWNLOAD_NEW_ASSETS = config["DOWNLOAD_NEW_ASSETS"]
TESTING = config["TESTING"]
NOTES_PATH = config["NOTES_PATH"]
API_URL = "https://%s.api.pvp.net/" % REGION
LOCALE = config["LOCALE"]


def to_secs(mins):
    return (int(mins[0]) * 60) + int(mins[2:4])


def to_mins(secs):
    secs = int(secs)
    secs_part = secs % 60
    if secs_part < 10:
        secs_part = "0" + str(secs_part)
    else:
        secs_part = str(secs_part)
    return str(int(math.floor(secs / 60))) + ":" + secs_part


class Loop(QtCore.QObject):
    valUpd = QtCore.pyqtSignal(int)

    def run(self):
        i = 0
        while True:
            time.sleep(1)
            print i
            self.valUpd.emit(i)
            i += 1


class mymainwindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.loop = Loop(self)
        self.loop.valUpd.connect(self.updateText)

        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.X11BypassWindowManagerHint #|
            #QtCore.Qt.WA_TransparentForMouseEvents |
            #QtCore.Qt.WA_X11DoNotAcceptFocus |
           # QtCore.Qt.WA_ForceDisabled
        )
        #self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        #self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        #self.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setGeometry(QtGui.QStyle.alignedRect(
            QtCore.Qt.LeftToRight, QtCore.Qt.AlignLeft,
            QtCore.QSize(145, 180),
            QtGui.qApp.desktop().availableGeometry()))

        frame = QtGui.QFrame(parent=self)
        frame.setStyleSheet(
            "QFrame {background: rgba(20,33,34,100%); border-right: 2px solid #6F603A; border-bottom: 2px solid #6F603A; margin: 0; padding: 0;}")
        box = QtGui.QHBoxLayout()

        logOutput = QtGui.QTextEdit()
        logOutput.setStyleSheet("background: rgba(20,33,34,0%); border: none; margin: 0; padding: 0;")
        logOutput.setReadOnly(True)
        logOutput.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        logOutput.setVerticalScrollBarPolicy(1)
        logOutput.setHorizontalScrollBarPolicy(1)

        box.addWidget(logOutput)

        frame.setLayout(box)

        self.setCentralWidget(frame)

        self.leagueOpenFlag = False
        self.CURRENT_MATCH = {}
        self.last_line = tailer.tail(open(NOTES_PATH), 5)
        # self.loop.run()

    def updateText(self, value):
        out = self.centralWidget().children()[1]
        if self.leagueOpenFlag:
            enemies = []
            spell_types = []

            for champ in self.CURRENT_MATCH["enemy"]:
                enemies.append(champ)
                for spell in self.CURRENT_MATCH["enemy"][champ]:
                    if spell not in spell_types:
                        spell_types.append(spell)
                    if self.CURRENT_MATCH["enemy"][champ][spell]["status"] != "?:??":
                        new_t = to_secs(self.CURRENT_MATCH["enemy"][champ][spell]["status"]) - 1
                        if new_t < 0:
                            self.CURRENT_MATCH["enemy"][champ][spell]["status"] = "?:??"
                        else:
                            self.CURRENT_MATCH["enemy"][champ][spell]["status"] = to_mins(
                                to_secs(self.CURRENT_MATCH["enemy"][champ][spell]["status"]) - 1)

            enemies.sort()

            new_last_line = tailer.tail(open(NOTES_PATH), 5)
            if self.last_line != new_last_line:
                #print new_last_line
                champ_indx = int(new_last_line[-1][0]) - 1
                sum_spl = int(new_last_line[-1][1]) - 1
                if champ_indx in [0,1,2,3,4] and sum_spl in [0, 1]:
                    print "Valid command"
                    deduct = 0
                    if len(new_last_line[-1].split(" ")) > 1:
                        deduct = int(new_last_line[-1].split(" ")[1])
                    espells = []
                    for spell in self.CURRENT_MATCH["enemy"][enemies[champ_indx]]:
                        espells.append(spell)
                    if self.CURRENT_MATCH["enemy"][enemies[champ_indx]][espells[sum_spl]]["status"] == "?:??":
                        self.CURRENT_MATCH["enemy"][enemies[champ_indx]][espells[sum_spl]]["status"] = to_mins(
                            int(self.CURRENT_MATCH["enemy"][enemies[champ_indx]][espells[sum_spl]]["cooldown"]) - deduct)
                else:
                    print "invalid command"
                self.last_line = new_last_line

            out.setText("")
            main_col = "#1A98FF"
            header_html = "<table border=0 style='color: %s; font-family: Helvetica; font-size: 12px; font-weight: 900; padding: 0; margin: 0;' cellspacing=0 cellpadding=0>" % main_col

            for i in range(0, len(enemies)):
                espells = []
                for spell in self.CURRENT_MATCH["enemy"][enemies[i]]:
                    espells.append(spell)

                row_text_to_add = "<tr><td><img src='imgs/champs/%s.png' width=30 height=30></td>" % enemies[i].replace(" ", "").replace("'", "")
                for spell in espells:
                    if self.CURRENT_MATCH["enemy"][enemies[i]][spell]["status"] == "?:??":
                        desat_str = ""
                        color = main_col
                        text = ""
                    else:
                        desat_str = "_desat"
                        color = "#FFFFFF"
                        text = self.CURRENT_MATCH["enemy"][enemies[i]][spell]["status"]

                    row_text_to_add += "<td width=10></td><td width=30 height=30 style='color: %s; background-image: url(imgs/spells/%s.png); margin-left: 5px; margin-right: 5px' align='center' valign='middle'>%s</td>" % (
                        color, (spell+desat_str).replace(" ", "").replace("'", ""), text)

                row_text_to_add += "</tr>"
                header_html += row_text_to_add

            out.setHtml(header_html + "</table>")
        else:
            out.setText(" ")

        QtGui.qApp.processEvents()

        if value % 30 == 0:
            game_found = False
            for p in psutil.process_iter():
                if 'LeagueofLegends' in str(p.name) or TESTING:
                    print "Getting game details"
                    response = requests.get(API_URL + "/observer-mode/rest/consumer/getSpectatorGameInfo/%s/%s" % (
                            PLATFORM_ID, SUMMONER_ID), params={
                            "api_key": API_KEY
                        }).json()
                    print "Got game details %s" % response
                    if "participants" in response:
                        game_found = True
                        if not self.leagueOpenFlag:
                            self.leagueOpenFlag = True
                            self.CURRENT_MATCH = {}
                            print response
                            friendly_team = 0
                            for participant in response["participants"]:
                                if participant["summonerId"] == SUMMONER_ID:
                                    friendly_team = participant["teamId"]
                            self.CURRENT_MATCH = {"friendly": {}, "enemy": {}}
                            for participant in response["participants"]:
                                print self.CURRENT_MATCH
                                if participant["teamId"] == friendly_team:
                                    self.CURRENT_MATCH["friendly"][
                                        CHAMPIONS[str(participant["championId"])]["name"]] = {
                                        SPELLS[str(participant["spell1Id"])]["name"]: {
                                            "cooldown": SPELLS[str(participant["spell1Id"])]["cooldown"][0],
                                            "time_last_used": -1,
                                            "status": "?"
                                        },
                                        SPELLS[str(participant["spell2Id"])]["name"]: {
                                            "cooldown": SPELLS[str(participant["spell2Id"])]["cooldown"][0],
                                            "time_last_used": -1,
                                            "status": "?"
                                        },
                                    }
                                else:
                                    self.CURRENT_MATCH["enemy"][CHAMPIONS[str(participant["championId"])]["name"]] = {
                                        SPELLS[str(participant["spell1Id"])]["name"]: {
                                            "cooldown": SPELLS[str(participant["spell1Id"])]["cooldown"][0],
                                            "time_last_used": -1,
                                            "status": "?:??"
                                        },
                                        SPELLS[str(participant["spell2Id"])]["name"]: {
                                            "cooldown": SPELLS[str(participant["spell2Id"])]["cooldown"][0],
                                            "time_last_used": -1,
                                            "status": "?:??"
                                        },
                                    }

                        break

            if not game_found:
                self.leagueOpenFlag = False
                print "LEAGUE NOT OPEN"

        if self.leagueOpenFlag:
            self.show()
        else:
            self.hide()

    def go(self):
        self.c_thread=threading.Thread(target=self.loop.run())
        self.c_thread.start()
        #self.loop.run()


SUMMONER_ID = requests.get(API_URL + "/api/lol/%s/v1.4/summoner/by-name/%s" % (REGION, SUMMONER_NAME), params={
    "api_key": API_KEY
}).json()["".join(SUMMONER_NAME.lower().split())]["id"]

CHAMPIONS = requests.get(
    "https://global.api.pvp.net/api/lol/static-data/%s/v1.2/champion?dataById=True&champData=image&api_key=%s" % (
        REGION, API_KEY)).json()["data"]
SPELLS = requests.get(
    "https://global.api.pvp.net/api/lol/static-data/%s/v1.2/summoner-spell?dataById=True&spellData=cooldown,image&api_key=%s" % (
        REGION, API_KEY)).json()["data"]

if DOWNLOAD_NEW_ASSETS:
    size = 30, 30
    for c in CHAMPIONS:
        print "getting pic for %s" % CHAMPIONS[c]["name"]
        urllib.urlretrieve(
            "http://ddragon.leagueoflegends.com/cdn/6.6.1/img/champion/%s" % CHAMPIONS[c]["image"]["full"],
            "imgs/champs/%s.png" % CHAMPIONS[c]["name"].replace(" ", "").replace("'", ""))

    for s in SPELLS:
        print "getting pic for %s" % SPELLS[s]["name"]
        file = "imgs/spells/%s.png" % SPELLS[s]["name"].replace(" ", "").replace("'", "")

        urllib.urlretrieve("http://ddragon.leagueoflegends.com/cdn/6.6.1/img/spell/%s" % SPELLS[s]["image"]["full"],
                           file)
        try:
            im = Image.open(file)
            im.thumbnail(size, Image.ANTIALIAS)
            im2 = ImageEnhance.Color(im).enhance(0.1)
            im2 = ImageEnhance.Brightness(im2).enhance(0.5)
            im.save(file, "PNG")
            im2.save(file.replace(".png", "_desat.png"), "PNG")
        except IOError:
            print "cannot create thumbnail for '%s'" % file


app = QtGui.QApplication(sys.argv)
mywindow = mymainwindow()
mywindow.go()

app.exec_()
