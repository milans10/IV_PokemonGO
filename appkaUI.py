# -*- coding: utf-8 -*-

#  Copyright (c) 2020. Created by Milan Svarc

import datetime
import json
import subprocess
import threading
import time
# Form implementation generated from reading ui file '.\PoGoAppka.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!
from datetime import time
from tkinter import *
from typing import re

import cv2
import numpy as np
import pytesseract
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets

import konstanty
from pokemon import Pokemon


class Ui_MainWindow(object):

    def spust_adb_prikaz(self, text, sleep_time=2):
        subprocess.Popen(konstanty.ADB + text + " &")  # swipe o jeden řádek pokemonů
        time.sleep(sleep_time)

    def adb_printsreen(self):
        pipe = subprocess.Popen("adb shell screencap -p &",
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, shell=True)
        image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
        return cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    def vyfot_okno(self):
        printscreen = self.adb_printsreen()

        cv2.imwrite("./IMAGE1.png", printscreen)  # Save screenshot
        # cv2.namedWindow("PokemonGO snímač", cv2.WINDOW_AUTOSIZE)  # Create window with freedom of dimensions
        ims = cv2.resize(printscreen, (300, 600))  # Resize image
        cv2.imshow("PokemonGOsnimac", ims)  # Show image

    def ukaz_printscreen_na_boku(self, fotka):
        photo2 = cv2.cvtColor(fotka, cv2.COLOR_BGR2RGB)
        photo2 = Image.fromarray(photo2)
        photo2 = photo2.resize((200, 400), Image.ANTIALIAS)

        # nutné opravit !!!
        # global imgtk
        # imgtk = ImageTk.PhotoImage(image=photo2)
        # self.lbl_printscreen.setPixmap(ims)
        # img_bg2 = Label(master=self.lbl_printscreen, image=imgtk)
        # img_bg2.grid(row=6, column=2, rowspan=20, pady=5, padx=5)

    def vrat_cislo_v_kruhu(cislo=0):
        # u"\u2460" jednicka v kolečku
        # ①
        # ipa = '"\\u2460"'
        cislo = int(cislo)
        if (cislo > 0) & (cislo < 11):
            cislo = 2459 + cislo
        elif cislo == 11:
            cislo = "246A"
        elif cislo == 12:
            cislo = "246B"
        elif cislo == 13:
            cislo = "246C"
        elif cislo == 14:
            cislo = "246D"
        elif cislo == 15:
            cislo = "246E"
        else:
            cislo = "24EA"

        ipa = '"\\u' + str(cislo) + '"'
        cislo = json.loads(ipa)
        print(cislo)
        return cislo

    def najdi_staty(self):
        global prostredek, crop_img, stredy

        fotka = self.adb_printsreen()
        self.ukaz_printscreen_na_boku(fotka)  # ukáže fotka na boku okna
        img_gray = cv2.cvtColor(fotka, cv2.COLOR_BGR2GRAY)
        template = cv2.imread('img_statsIV.png', 0)
        w, h = template.shape[::-1]

        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)

        if not loc[0].size > 0:
            print("prazdne")
        else:
            osa_Y = min(loc[0])
            osa_X = max(loc[1])

            crop_img = img_gray[osa_Y:osa_Y + h, osa_X + 0:osa_X + w - 10]  # vyříznutí statů IV
            crop_img3 = crop_img[0:h, int(w / 2):int(
                w / 2) + 1]  # vyříznutí kontrolního prhu pro nalezení souřadnic řádků s ATT, DEF, HP

            sekce = []
            stredy = []
            for a in range(h - 1, 0, -1):
                barva = crop_img3[a, 0]
                if all(barva != [255, 255, 255]):
                    sekce.append(a)

            sekce = sorted(sekce)
            for b in range(len(sekce) - 1):
                if b > 8:
                    if ((sekce[b + 1] - sekce[b]) > 10) | (b == len(sekce) - 2):
                        if len(stredy) < 1:
                            prostredek = int(b / 2)
                        stredy.append(sekce[b] - prostredek)
        return crop_img, w, stredy

    def zjisti_atributy_pokemona(self, poradi=1):
        nacteno = True

        while nacteno:
            try:
                crop_img, delka, stredy = self.najdi_staty()
                delka = delka - 10
                att_hodnota = 0
                def_hodnota = 0
                hp_hodnota = 0

                for a in range(delka):
                    att_barva = crop_img[stredy[0] - 1, a]
                    def_barva = crop_img[stredy[1] - 1, a]
                    hp_barva = crop_img[stredy[2] - 1, a]
                    if any((att_barva != [255, 255, 255]) & (att_barva != [226, 226, 226]) & (
                            att_barva < [232, 232, 232])):
                        att_hodnota = att_hodnota + 1
                    if any((def_barva != [255, 255, 255]) & (def_barva != [226, 226, 226]) & (
                            def_barva < [232, 232, 232])):
                        def_hodnota = def_hodnota + 1
                    if any((hp_barva != [255, 255, 255]) & (hp_barva != [226, 226, 226]) & (
                            hp_barva < [232, 232, 232])):
                        hp_hodnota = hp_hodnota + 1

                # 22px na 1 hodnotu IV statu, rozmezí 0-15 pro každou hodnotu
                att_hodnota = att_hodnota // 22
                def_hodnota = def_hodnota // 22
                hp_hodnota = hp_hodnota // 22
                procento = (att_hodnota + def_hodnota + hp_hodnota) * 100 // 45
                # text = str(procento) + "%(" + vrat_cislo_v_kruhu(att_hodnota) + ")(" + vrat_cislo_v_kruhu(
                # def_hodnota) + ")(" + vrat_cislo_v_kruhu(hp_hodnota) +")"
                text = str(procento) + "%" + str(att_hodnota) + "-" + str(def_hodnota) + "-" + str(hp_hodnota)
                # cv2.imwrite("./pokemoni/pkm" + str(poradi+ + 1) + " " + str(text) + "_detail.png", image)

                global novy_pokemon
                novy_pokemon.__init__(att_power=att_hodnota, def_power=def_hodnota, hp_power=hp_hodnota)

                if self.chckbx_prejmenovat.isChecked():
                    # jde se přejmovávat pokud splňuje nastavený limit
                    if int(self.spn_hranice_prejmenovani.value()) >= int(procento):
                        if self.chckbx_prejmenovat_posix.isChecked():
                            return self.input_prejmenovat_na.text() + "-" + str(procento) + "%"
                        return self.input_prejmenovat_na.text()
                return text

            except TypeError:
                print("Nepovedlo se načíst data pokemona... Není vidět tabulka s hodnotami")
                nacteno = True

    def swipni_doprava(self):
        # swipe o jeden řádek pokemonů
        self.spust_adb_prikaz("swipe 940 1080 140 1080 1500")

    def swipni_pokemony(self):
        # swipe o jeden řádek pokemonů
        self.spust_adb_prikaz("swipe 140 1296 140 1000 1500")

    def btn_prejmenuj_pokemona(self, nove_jmeno=""):
        self.spust_adb_prikaz("tap 540 915")  # tapnutí na TLAČÍTKO přejmenování pokémona

        for ciselnik in range(13):
            self.spust_adb_prikaz("keyevent 67", 0)  # klávesa DELETE

        time.sleep(2)
        if len(nove_jmeno) > 12:
            prikaz = "keyboard text 'TOO LONG'"
        else:
            prikaz = "keyboard text '" + nove_jmeno + "'"
        self.spust_adb_prikaz(prikaz, 3)

        # tlačítko HOTOVO na virtuální klávesnici
        self.spust_adb_prikaz("tap 990 2097")

        # tlačítko OK pro potvrzení nového jména
        self.spust_adb_prikaz("tap 540 1170", 3)

    def btn_uprostred(self):
        # PROSTŘEDNÍ TLAČÍTKO tapnutí
        self.spust_adb_prikaz("tap 551 2026")

    def btn_seznam_pokemonu(self):
        # SBÍRKA POKEMONŮ TLAČÍTKO tapnutí
        self.spust_adb_prikaz("tap 238 1862")

    def btn_menu_pokemonu(self):
        # ŘAZENÍ POKEMONŮ(MENU POKEMONA) TLAČÍTKO tapnutí
        self.spust_adb_prikaz("tap 933 2025")

    def btn_appraise(self):
        # APPRAISE TLAČÍTKO tapnutí
        self.spust_adb_prikaz("tap 750 1617")

    def btn_pokemon(self, pozice_na_radku=1):
        # pokemon políčko je X 330 na Y 390
        if pozice_na_radku > 3:
            pozice_na_radku = 3  # více než 3 pokemoni na řádku nejsou
        souradnice_x = 198 + ((pozice_na_radku - 1) * 330)
        prikaz = "tap " + str(souradnice_x) + " 612"

        self.spust_adb_prikaz(prikaz)  # 1.POKEMON VLEVO NAHORE tapnutí

    def klik_do_stredu(self):
        # tapnutí do stredu obrazovky
        self.spust_adb_prikaz("tap 540 1080", 3)


    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1145, 606)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./img_pokeball.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet("border-image: url(./img_bg.png);")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.vlevo = QtWidgets.QVBoxLayout()
        self.vlevo.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.vlevo.setContentsMargins(-1, -1, 10, -1)
        self.vlevo.setObjectName("vlevo")
        self.btn_prejmenovat = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_prejmenovat.sizePolicy().hasHeightForWidth())
        self.btn_prejmenovat.setSizePolicy(sizePolicy)
        self.btn_prejmenovat.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.btn_prejmenovat.setFont(font)
        self.btn_prejmenovat.setStyleSheet("border-image: none;\n"
                                           "")
        self.btn_prejmenovat.setObjectName("btn_prejmenovat")
        self.vlevo.addWidget(self.btn_prejmenovat)
        self.btn_prejmenovat.clicked.connect(self.zacni_prejmenovavat)

        self.grpbx_kolik = QtWidgets.QGroupBox(self.centralwidget)
        self.grpbx_kolik.setMinimumSize(QtCore.QSize(0, 100))
        self.grpbx_kolik.setMaximumSize(QtCore.QSize(300, 150))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.grpbx_kolik.setPalette(palette)
        self.grpbx_kolik.setStyleSheet("border-image: none;\n"
                                       "background: rgba(255, 255, 255, 0.3);")
        self.grpbx_kolik.setObjectName("grpbx_kolik")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.grpbx_kolik)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.lbl_kolik_prejmenovat = QtWidgets.QLabel(self.grpbx_kolik)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_kolik_prejmenovat.sizePolicy().hasHeightForWidth())
        self.lbl_kolik_prejmenovat.setSizePolicy(sizePolicy)
        self.lbl_kolik_prejmenovat.setMinimumSize(QtCore.QSize(0, 20))
        self.lbl_kolik_prejmenovat.setMaximumSize(QtCore.QSize(300, 20))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.lbl_kolik_prejmenovat.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.lbl_kolik_prejmenovat.setFont(font)
        self.lbl_kolik_prejmenovat.setStyleSheet("border-image: none;background: rgba(255, 255, 255, 0);")
        self.lbl_kolik_prejmenovat.setScaledContents(True)
        self.lbl_kolik_prejmenovat.setWordWrap(True)
        self.lbl_kolik_prejmenovat.setObjectName("lbl_kolik_prejmenovat")
        self.verticalLayout_3.addWidget(self.lbl_kolik_prejmenovat)
        self.spn_kolik_prejmenovat = QtWidgets.QSpinBox(self.grpbx_kolik)
        self.spn_kolik_prejmenovat.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.spn_kolik_prejmenovat.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.spn_kolik_prejmenovat.setFont(font)
        self.spn_kolik_prejmenovat.setAutoFillBackground(False)
        self.spn_kolik_prejmenovat.setStyleSheet("border-image: none;color: black;")
        self.spn_kolik_prejmenovat.setObjectName("spn_kolik_prejmenovat")
        self.verticalLayout_3.addWidget(self.spn_kolik_prejmenovat)
        self.vlevo.addWidget(self.grpbx_kolik)
        self.grpbx_prejmenovat = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grpbx_prejmenovat.sizePolicy().hasHeightForWidth())
        self.grpbx_prejmenovat.setSizePolicy(sizePolicy)
        self.grpbx_prejmenovat.setMinimumSize(QtCore.QSize(0, 150))
        self.grpbx_prejmenovat.setMaximumSize(QtCore.QSize(300, 150))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.grpbx_prejmenovat.setPalette(palette)
        self.grpbx_prejmenovat.setStyleSheet("border-image: none;\n"
                                             "background: rgba(255, 255, 255, 0.3);")
        self.grpbx_prejmenovat.setObjectName("grpbx_prejmenovat")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.grpbx_prejmenovat)
        self.verticalLayout.setObjectName("verticalLayout")
        self.chckbx_prejmenovat = QtWidgets.QCheckBox(self.grpbx_prejmenovat)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chckbx_prejmenovat.sizePolicy().hasHeightForWidth())
        self.chckbx_prejmenovat.setSizePolicy(sizePolicy)
        self.chckbx_prejmenovat.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.chckbx_prejmenovat.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.chckbx_prejmenovat.setFont(font)
        self.chckbx_prejmenovat.setStyleSheet("border-image: none;\n"
                                              "background: rgba(255, 255, 255, 0);")
        self.chckbx_prejmenovat.setAutoExclusive(False)
        self.chckbx_prejmenovat.setObjectName("chckbx_prejmenovat")
        self.verticalLayout.addWidget(self.chckbx_prejmenovat)
        self.spn_hranice_prejmenovani = QtWidgets.QSpinBox(self.grpbx_prejmenovat)
        self.spn_hranice_prejmenovani.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.spn_hranice_prejmenovani.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.spn_hranice_prejmenovani.setFont(font)
        self.spn_hranice_prejmenovani.setAutoFillBackground(False)
        self.spn_hranice_prejmenovani.setStyleSheet("border-image: none;color:black;")
        self.spn_hranice_prejmenovani.setProperty("value", 80)
        self.spn_hranice_prejmenovani.setObjectName("spn_hranice_prejmenovani")
        self.verticalLayout.addWidget(self.spn_hranice_prejmenovani)
        self.lbl_prejmenovat = QtWidgets.QLabel(self.grpbx_prejmenovat)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_prejmenovat.sizePolicy().hasHeightForWidth())
        self.lbl_prejmenovat.setSizePolicy(sizePolicy)
        self.lbl_prejmenovat.setMinimumSize(QtCore.QSize(0, 20))
        self.lbl_prejmenovat.setMaximumSize(QtCore.QSize(300, 20))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.lbl_prejmenovat.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.lbl_prejmenovat.setFont(font)
        self.lbl_prejmenovat.setStyleSheet("border-image: none;\n"
                                           "background: rgba(255, 255, 255, 0);")
        self.lbl_prejmenovat.setTextFormat(QtCore.Qt.AutoText)
        self.lbl_prejmenovat.setScaledContents(True)
        self.lbl_prejmenovat.setWordWrap(True)
        self.lbl_prejmenovat.setObjectName("lbl_prejmenovat")
        self.verticalLayout.addWidget(self.lbl_prejmenovat)
        self.input_prejmenovat_na = QtWidgets.QLineEdit(self.grpbx_prejmenovat)
        self.input_prejmenovat_na.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.input_prejmenovat_na.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.input_prejmenovat_na.setFont(font)
        self.input_prejmenovat_na.setStyleSheet("border-image: none;\n"
                                                "background: rgba(255, 255, 255, 0);")
        self.input_prejmenovat_na.setObjectName("input_prejmenovat_na")
        self.input_prejmenovat_na.textChanged.connect(self.uprav_delku_jmena_pro_prejmenovani)
        self.verticalLayout.addWidget(self.input_prejmenovat_na)

        self.chckbx_prejmenovat_posix = QtWidgets.QCheckBox(self.grpbx_prejmenovat)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chckbx_prejmenovat_posix.sizePolicy().hasHeightForWidth())
        self.chckbx_prejmenovat_posix.setSizePolicy(sizePolicy)
        self.chckbx_prejmenovat_posix.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.chckbx_prejmenovat_posix.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.chckbx_prejmenovat_posix.setFont(font)
        self.chckbx_prejmenovat_posix.setStyleSheet("border-image: none;\n"
                                                    "background: rgba(255, 255, 255, 0);")
        self.chckbx_prejmenovat_posix.setChecked(True)
        self.chckbx_prejmenovat_posix.setAutoExclusive(False)
        self.chckbx_prejmenovat_posix.setObjectName("chckbx_prejmenovat_posix")
        self.verticalLayout.addWidget(self.chckbx_prejmenovat_posix)
        self.vlevo.addWidget(self.grpbx_prejmenovat)
        self.grpbx_preskocit = QtWidgets.QGroupBox(self.centralwidget)
        self.grpbx_preskocit.setMinimumSize(QtCore.QSize(0, 100))
        self.grpbx_preskocit.setMaximumSize(QtCore.QSize(300, 100))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 76))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.grpbx_preskocit.setPalette(palette)
        self.grpbx_preskocit.setStyleSheet("border-image: none;\n"
                                           "background: rgba(255, 255, 255, 0.3);")
        self.grpbx_preskocit.setObjectName("grpbx_preskocit")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.grpbx_preskocit)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.chckbx_preskocit = QtWidgets.QCheckBox(self.grpbx_preskocit)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chckbx_preskocit.sizePolicy().hasHeightForWidth())
        self.chckbx_preskocit.setSizePolicy(sizePolicy)
        self.chckbx_preskocit.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.chckbx_preskocit.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.chckbx_preskocit.setFont(font)
        self.chckbx_preskocit.setStyleSheet("border-image: none;\n"
                                            "background: rgba(255, 255, 255, 0);")
        self.chckbx_preskocit.setAutoExclusive(False)
        self.chckbx_preskocit.setObjectName("chckbx_preskocit")
        self.verticalLayout_2.addWidget(self.chckbx_preskocit)
        self.chckbx_preskocit.stateChanged.connect(self.stav_preskocit)
        self.input_preskocit_prefix = QtWidgets.QLineEdit(self.grpbx_preskocit)
        self.input_preskocit_prefix.setMaximumSize(QtCore.QSize(300, 16777215))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.input_preskocit_prefix.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.input_preskocit_prefix.setFont(font)
        self.input_preskocit_prefix.setStyleSheet("border-image: none;\n"
                                                  "background: rgba(255, 255, 255, 0);")
        self.input_preskocit_prefix.setMaxLength(15)
        self.input_preskocit_prefix.setObjectName("input_preskocit_prefix")
        self.input_preskocit_prefix.setEnabled(False)
        self.verticalLayout_2.addWidget(self.input_preskocit_prefix)
        self.vlevo.addWidget(self.grpbx_preskocit)
        self.btn_vyfotit = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_vyfotit.sizePolicy().hasHeightForWidth())
        self.btn_vyfotit.setSizePolicy(sizePolicy)
        self.btn_vyfotit.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.btn_vyfotit.setFont(font)
        self.btn_vyfotit.setStyleSheet("border-image: none;\n"
                                       "")
        self.btn_vyfotit.setObjectName("btn_vyfotit")
        self.vlevo.addWidget(self.btn_vyfotit)
        self.btn_konec = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btn_konec.sizePolicy().hasHeightForWidth())
        self.btn_konec.setSizePolicy(sizePolicy)
        self.btn_konec.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.btn_konec.setFont(font)
        self.btn_konec.setStyleSheet("border-image: none;\n"
                                     "")
        self.btn_konec.setObjectName("btn_konec")
        self.vlevo.addWidget(self.btn_konec)

        self.btn_konec.clicked.connect(self.konec)

        self.text_zona2 = QtWidgets.QTextEdit(self.centralwidget)
        self.text_zona2.setMaximumSize(QtCore.QSize(300, 16777215))
        self.text_zona2.setStyleSheet("border-image: none;\n"
                                      "background: rgba(255, 255, 255, 0.0);\n"
                                      "color: yellow;")
        self.text_zona2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.text_zona2.setReadOnly(True)
        self.text_zona2.setObjectName("text_zona2")
        self.vlevo.addWidget(self.text_zona2)
        self.horizontalLayout.addLayout(self.vlevo)
        self.text_zona = QtWidgets.QTextEdit(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.text_zona.sizePolicy().hasHeightForWidth())
        self.text_zona.setSizePolicy(sizePolicy)
        self.text_zona.setMinimumSize(QtCore.QSize(600, 0))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 25))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.text_zona.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.text_zona.setFont(font)
        self.text_zona.setStyleSheet("border-image: none;\n"
                                     "background: rgba(255, 255, 255, 0.1);\n"
                                     "color: yellow;")
        self.text_zona.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.text_zona.setFrameShadow(QtWidgets.QFrame.Plain)
        self.text_zona.setLineWrapColumnOrWidth(0)
        self.text_zona.setReadOnly(True)
        self.text_zona.setObjectName("text_zona")
        self.horizontalLayout.addWidget(self.text_zona)
        self.vpravo = QtWidgets.QVBoxLayout()
        self.vpravo.setContentsMargins(10, -1, 10, -1)
        self.vpravo.setObjectName("vpravo")
        self.lbl_staty_pokemona = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_staty_pokemona.sizePolicy().hasHeightForWidth())
        self.lbl_staty_pokemona.setSizePolicy(sizePolicy)
        self.lbl_staty_pokemona.setMinimumSize(QtCore.QSize(200, 0))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.lbl_staty_pokemona.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.lbl_staty_pokemona.setFont(font)
        self.lbl_staty_pokemona.setStyleSheet("border-image: none;\n"
                                              "background: rgba(255, 255, 255, 0.0);\n"
                                              "color: yellow;")
        self.lbl_staty_pokemona.setText("")
        self.lbl_staty_pokemona.setScaledContents(True)
        self.lbl_staty_pokemona.setWordWrap(True)
        self.lbl_staty_pokemona.setObjectName("lbl_staty_pokemona")
        self.vpravo.addWidget(self.lbl_staty_pokemona)
        self.lbl_printscreen = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_printscreen.sizePolicy().hasHeightForWidth())
        self.lbl_printscreen.setSizePolicy(sizePolicy)
        self.lbl_printscreen.setMinimumSize(QtCore.QSize(200, 400))
        self.lbl_printscreen.setMaximumSize(QtCore.QSize(200, 400))
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.lbl_printscreen.setFont(font)
        self.lbl_printscreen.setStyleSheet("border-image: none;\n"
                                           "background: rgba(255, 255, 255, 0.0);")
        self.lbl_printscreen.setText("")
        self.lbl_printscreen.setObjectName("lbl_printscreen")
        self.vpravo.addWidget(self.lbl_printscreen)
        self.horizontalLayout.addLayout(self.vpravo)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "IV Pokémon GO"))
        self.btn_prejmenovat.setText(_translate("MainWindow", "Spustit přejmenovávání"))
        self.grpbx_kolik.setTitle(_translate("MainWindow", "Kolik přejmenovat..."))
        self.lbl_kolik_prejmenovat.setText(_translate("MainWindow", "Kolik přejmenovat pokémonů? (0=vše)"))
        self.grpbx_prejmenovat.setTitle(_translate("MainWindow", "Přejmenovat..."))
        self.chckbx_prejmenovat.setText(_translate("MainWindow", "Přejmenovat pokémona s % nižším než"))
        self.lbl_prejmenovat.setText(_translate("MainWindow", "Přejmenovat na:"))
        self.input_prejmenovat_na.setToolTip(_translate("MainWindow", "vložte jméno pro pokémony splňující kritérium"))
        self.input_prejmenovat_na.setText(_translate("MainWindow", "GYM"))
        self.chckbx_prejmenovat_posix.setText(_translate("MainWindow", "Přidat za jméno % (např -97%)"))
        self.grpbx_preskocit.setTitle(_translate("MainWindow", "Přeskočit..."))
        self.chckbx_preskocit.setText(_translate("MainWindow", "Přeskočit pokémona začínajícího na:"))
        self.input_preskocit_prefix.setToolTip(_translate("MainWindow", "Vložte jméno"))
        self.input_preskocit_prefix.setText(_translate("MainWindow", "GYM"))
        self.btn_vyfotit.setText(_translate("MainWindow", "Vyfotit"))
        self.btn_konec.setText(_translate("MainWindow", "Konec"))

    # v daném výřezu zjisti počty pokemonu xx / yy, v případě filtru najde znak Q
    def zjisti_pocet_pokemonu(self):
        image = self.adb_printsreen()
        crop_img = image[200:250, 115:465]
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        text = pytesseract.image_to_string(crop_img)
        text = text.replace("(", "").replace(")", "")
        if text[0] == "Q":
            text = text.split("Q")
            return text[1]
        else:
            return text.split("/")[0]

    def uprav_delku_jmena_pro_prejmenovani(self, text):
        hodnota = self.input_prejmenovat_na.text()
        if self.chckbx_prejmenovat_posix.isChecked():
            if len(hodnota) > 8:
                self.input_prejmenovat_na.setText(hodnota[:8])
        else:
            if len(hodnota) > 12:
                self.input_prejmenovat_na.setText(hodnota[:12])
        return

    def stav_preskocit(self):
        if self.chckbx_preskocit.isChecked():
            self.input_preskocit_prefix.setEnabled(True)
        else:
            self.input_preskocit_prefix.setEnabled(False)

    def napis_stav(self, text):
        self.text_zona.setReadOnly(False)
        self.text_zona.insertPlainText(text + "\n")
        self.text_zona.setReadOnly(True)

    def najdi_jmeno_pokemona(self, screenshot):
        img_rgb = screenshot
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread('btn_rename.png', 0)
        w, h = template.shape[::-1]

        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)

        if not loc[0].size > 0:
            text = "Jméno nerozpoznáno"
            return text
        else:
            osa_Y = min(loc[0])
            osa_X = max(loc[1])
            crop_img = img_gray[osa_Y:osa_Y + h + 40, 50:(osa_X)]
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            text = pytesseract.image_to_string(crop_img)
            text = re.sub('[^0-9a-zA-Z%-]', '', text)
            return text

    @staticmethod
    def lze_prejmenovat(img_rgb):
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread('btn_rename.png', 0)  # výstřižek ikony pro přejmenování

        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)

        if not loc[0].size > 0:
            # print("Nelze přejmenovat. Tlačítko není dostupné.")
            return False
        else:
            # print(min(loc[0]))
            return True

    def spust_prejmenovani(self):
        # btn_uprostred()
        # btn_seznam_pokemonu()
        if self.spn_kolik_prejmenovat.value() == 0:
            pocet_pokemonu = int(self.zjisti_pocet_pokemonu())
        else:
            pocet_pokemonu = int(self.spn_kolik_prejmenovat.value())
        # print("Maximálně počet pokémonů k přejmenování:", pocet_pokemonu)
        self.napis_stav("Maximálně počet pokémonů k přejmenování:" + str(pocet_pokemonu))
        self.btn_pokemon()

        start = time.time()
        # print("Čas začátku: ", time.strftime('%H:%M:%S', time.localtime(start)))
        self.napis_stav("Čas začátku: " + time.strftime('%H:%M:%S', time.localtime(start)))
        doba_trvani = 0

        def vypis_prubeh_prejmenovani(x, jmeno, img):
            puvodni_jmeno = self.najdi_jmeno_pokemona(img)
            self.napis_stav("Původní jméno pokémona #" + str(x + 1) + " " + puvodni_jmeno)
            if (self.chckbx_preskocit.isChecked()) & (len(self.input_preskocit_prefix.text()) > 0):
                delka = len(self.input_preskocit_prefix.text())
                if puvodni_jmeno[0:delka] == self.input_preskocit_prefix.text():
                    self.napis_stav("Pokemon #" + str(x + 1) + " začíná na zvolený text. Přeskakuji...")
                    return 1

            if self.spn_hranice_prejmenovani.value() >= int(novy_pokemon.procento):
                self.napis_stav(
                    "Pokemon #" + str(x + 1) + " splnil kritérium pro extra přejmenování. Přejmenovávám na " + jmeno)
            else:
                self.napis_stav("Pokemon #" + str(x + 1) + " má hodnoty:" + jmeno)
            return 0

        for x in range(pocet_pokemonu):
            img = self.adb_printsreen()
            global novy_pokemon
            novy_pokemon = Pokemon()

            if self.lze_prejmenovat(img):
                self.btn_menu_pokemonu()
                self.btn_appraise()
                self.klik_do_stredu()
                novy_pokemon.jmeno = self.zjisti_atributy_pokemona(x)
                # if doba_trvani != 0:
                # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                stav_prejmenovani = vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
                # cv2.imwrite("./pokemoni/pkm " + str(x+1) + " " + str(novy_pokemon.jmeno) + ".png", img)

                self.klik_do_stredu()

                if stav_prejmenovani == 0:
                    while (True):
                        self.btn_prejmenuj_pokemona(novy_pokemon.jmeno)  # přejmenování pokémona

                        # kontrola přejmenování pokémona
                        img = self.adb_printsreen()
                        nove_jmeno = self.najdi_jmeno_pokemona(img)
                        self.napis_stav("Nové jméno pokémona #" + str(x + 1) + " " + nove_jmeno)
                        if novy_pokemon.jmeno == nove_jmeno:
                            # print("jmena jsou stejna")
                            break
                        # print("jmena se liší") # opakuj přejmenování když se jména liší

                staty_pokemona = "* : {}\n% : {}\nATT : {}\nDEF : {}\nHP : {}".format(novy_pokemon.hvezd,
                                                                                      novy_pokemon.procento,
                                                                                      novy_pokemon.att_power,
                                                                                      novy_pokemon.def_power,
                                                                                      novy_pokemon.hp_power)
                self.lbl_staty_pokemona.setText(staty_pokemona)
                self.swipni_doprava()
                time.sleep(5)

                if doba_trvani == 0:
                    end = time.time()
                    doba_trvani = (end - start) // 1
                    # print("odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))
                    # print("Odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))
                    self.napis_stav(
                        "Odhadovaný čas konce za " + str(datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu))))

                    # print("Hotovo pokémonů:", x + 1)
                    # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                    # stav_prejmenovani = vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
            else:
                # print("Přeskakuji pokemona #", (x + 1), " (nelze jej přejmenovat) na dalšího pokemona")
                self.napis_stav("Přeskakuji pokemona #" + str(x + 1) + " (nelze jej přejmenovat) na dalšího pokemona")
                self.swipni_doprava()
                time.sleep(5)
            # kontrola na ukončení přejmenovávání
            global ukonci_vlakno
            if ukonci_vlakno | (self.spn_kolik_prejmenovat.value() == (x + 1)):
                self.btn_prejmenovat.setText("Spustit přejmenovávání")
                self.btn_prejmenovat.setEnabled(True)
                break

        konec = time.time()
        # print("Čas ukončení: ", time.strftime('%H:%M:%S', time.localtime(konec)), "\t doba trvání", datetime.timedelta(seconds=(konec - start)))
        self.napis_stav("Čas ukončení: " + time.strftime('%H:%M:%S', time.localtime(konec)) + "\t doba trvání " + str(
            datetime.timedelta(seconds=(konec - start))))
        self.btn_uprostred()
        # print("Konec")
        self.napis_stav("Konec")

    def zacni_prejmenovavat(self):
        global t1, ukonci_vlakno
        ukonci_vlakno = False
        t1 = threading.Thread(target=self.spust_prejmenovani)
        t1.daemon = True
        if "Spustit přejmenovávání" == self.btn_prejmenovat.text():
            self.btn_prejmenovat.setDisabled(True)
            t1.start()
            time.sleep(2)
            if t1.is_alive():
                self.btn_prejmenovat.setText("Ukončit přejmenovávání")
            self.btn_prejmenovat.setEnabled(True)

        else:
            ukonci_vlakno = True
            self.btn_prejmenovat.setText("Spustit přejmenovávání")
            self.btn_prejmenovat.setDisabled(True)

    def konec(self):
        # window.destroy()
        sys.exit()



def zobrazUI():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())