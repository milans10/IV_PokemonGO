# -*- coding: utf-8 -*-

#  Copyright (c) 2026. Created by Milan Svarc


# Form implementation generated from reading ui file '.\PoGoAppka.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!
import datetime
import sys
import threading
import time
from builtins import range

import cv2
import numpy as np
import pytesseract
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect

import main
from pokemon import Pokemon


class ImageWidgetWithRatio(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)

    def hasHeightForWidth(self):
        return self.pixmap() is not None

    def heightForWidth(self, w):
        if self.pixmap():
            return int(w * (self.pixmap().height() / self.pixmap().width()))


def lze_prejmenovat(img_rgb):
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread('btn_rename.png', 0)  # výstřižek ikony pro přejmenování

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)

    # Pokud se nepodaří najít s vysokou přesností, zkusíme snížit práh
    if not loc[0].size > 0:
        print("Nenalezeno tlačítko přejmenovat s prahem 0.8, zkouším snížit na 0.6")
        threshold = 0.6
        loc = np.where(res >= threshold)

    if not loc[0].size > 0:
        print("prazdne - ani snížený práh nepomohl")
        # print("Nelze přejmenovat. Tlačítko není dostupné.")
        return False
    else:
        # print(min(loc[0]))
        return True


class Ui_MainWindow(object):

    def ukaz_printscreen_na_boku(self, fotka):
        RGBarray = cv2.cvtColor(fotka, cv2.COLOR_BGR2RGB)
        width, height, channels = RGBarray.shape
        image = QtGui.QImage(RGBarray.data, height, width, 3 * height, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap(image)
        self.lbl_printscreen.setScaledContents(True)
        self.lbl_printscreen.setPixmap(pixmap)

    def najdi_staty(self):
        fotka = main.adb_printsreen()
        self.ukaz_printscreen_na_boku(fotka)

        bars = self.najdi_stat_panel(fotka)

        if bars is None:
            print("Nepovedlo se najit staty - bary nenalezeny")
            return None

        stredy = [bar['y_center'] for bar in bars]
        x1 = bars[0]['x1']
        x2 = bars[0]['x2']
        y_top = stredy[0] - 60  # priblizny odsazeni nahoru (label + okraj)
        y_bottom = stredy[-1] + 20  # priblizny odsazeni dolu pod posledni bar

        osa_X = x1
        osa_Y = y_top
        w = x2 - x1
        h = y_bottom - y_top

        img_gray = cv2.cvtColor(fotka, cv2.COLOR_BGR2GRAY)
        crop_img = img_gray[osa_Y:y_bottom, osa_X:x2]
        crop_img_color = fotka[osa_Y:y_bottom, osa_X:x2]

        # stredy prepocitane relativne vuci oriznute oblasti (aby sedely na crop_img)
        stredy_relativni = [s - osa_Y for s in stredy]

        cv2.rectangle(fotka, (osa_X, osa_Y), (osa_X + w, osa_Y + h), (0, 0, 255), 2)
        for stred in stredy:
            cv2.line(fotka, (osa_X, stred), (osa_X + w, stred), (0, 255, 0), 1)
        self.ukaz_printscreen_na_boku(fotka)

        return crop_img, w, stredy_relativni, fotka, osa_X, osa_Y

    def najdi_bary_v_crop(self, crop_color, min_w=200):
        """
        Najde vsechny sirsi kapsle (progress bary) v obrazku podle tvaru.
        min_w filtruje mala tlacitka/ikony, ktera by take mohla spadnout do masky.
        """
        gray = cv2.cvtColor(crop_color, cv2.COLOR_BGR2GRAY)
        mask = cv2.inRange(gray, 150, 245)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = [cv2.boundingRect(c) for c in contours]
        boxes = [b for b in boxes if b[2] > 50 and 15 < b[3] < 40]
        boxes.sort(key=lambda b: b[1])

        # seskupeni rozseknutych kontur (delici rysky) do celych radku
        rows = []
        for b in boxes:
            x, y, w, h = b
            placed = False
            for row in rows:
                if abs(row[0][1] - y) < 10:
                    row.append(b)
                    placed = True
                    break
            if not placed:
                rows.append([b])

        bars = []
        for row in rows:
            x1 = min(b[0] for b in row)
            x2 = max(b[0] + b[2] for b in row)
            y1 = min(b[1] for b in row)
            y2 = max(b[1] + b[3] for b in row)
            if x2 - x1 >= min_w:
                bars.append({'x1': x1, 'x2': x2, 'y_center': (y1 + y2) // 2})

        bars.sort(key=lambda b: b['y_center'])
        return bars

    def najdi_stat_panel(self, img):
        """
        Najde 3 stat-bary (Attack/Defense/HP) primo v celem screenshotu,
        BEZ template matchingu. Rozpozna je jako 3 kapsle stejne sirky,
        v pravidelnych rozestupech pod sebou.

        Vraci seznam 3 dictu {'x1','x2','y_center'} serazenych shora dolu,
        nebo None, pokud se nenajde vhodna trojice.
        """
        bars = self.najdi_bary_v_crop(img, min_w=200)

        for i in range(len(bars) - 2):
            b1, b2, b3 = bars[i], bars[i + 1], bars[i + 2]
            same_x = abs(b1['x1'] - b2['x1']) < 15 and abs(b2['x1'] - b3['x1']) < 15
            gap1 = b2['y_center'] - b1['y_center']
            gap2 = b3['y_center'] - b2['y_center']
            similar_gap = abs(gap1 - gap2) < 20
            if same_x and similar_gap:
                return [b1, b2, b3]

        return None

    def zmer_vyplneni(self, crop_color, bar, tolerance=15, edge_skip=6):
        """
        Zmeri procento vyplneni baru (0.0 - 1.0).
        Hleda POSLEDNI pixel odpovidajici barve vyplne zleva doprava -
        odolne vuci delicim ryskam i antialiasingu na zaoblenych rozich.
        """
        y = bar['y_center']
        row = crop_color[y, bar['x1']:bar['x2']].astype(int)
        width = len(row)

        fill_color = row[edge_skip]

        last_match = -1
        for i, pixel in enumerate(row):
            if np.all(np.abs(pixel - fill_color) < tolerance):
                last_match = i

        return (last_match + 1) / width

    def zjisti_atributy_pokemona(self, poradi=1):

        nacteno = True

        # Inicializace proměnné pro uložení kalibrace pixelů, pokud ještě neexistuje
        if not hasattr(self, 'jeden_bod_px'):
            self.jeden_bod_px = None

        while nacteno:
            try:
                vysledek = self.najdi_staty()

                if vysledek is None:
                    raise TypeError("Nenalezeno")
                crop_img, delka, stredy, fotka, osa_X, osa_Y = vysledek
                delka = delka - 10
                att_hodnota = 0
                def_hodnota = 0
                hp_hodnota = 0
                celkova_delka_att = 0

                for a in range(delka):
                    # Zjištění celkové délky baru (vše co není bílé pozadí > 250)
                    if crop_img[stredy[0] - 1, a] < 250:
                        celkova_delka_att += 1

                    # Hledáme tmavší pixely (vyplněný graf), tedy hodnoty menší než práh (např. 225)
                    # 0 = černá, 255 = bílá. Tím se vyloučí pozadí (255) i prázdný pruh (cca 226)
                    if crop_img[stredy[0] - 1, a] < 225:
                        att_hodnota += 1
                        cv2.line(fotka, (osa_X + a, osa_Y + stredy[0] - 1), (osa_X + a, osa_Y + stredy[0] - 1),
                                 (255, 0, 0), 1)
                    if crop_img[stredy[1] - 1, a] < 225:
                        def_hodnota += 1
                        cv2.line(fotka, (osa_X + a, osa_Y + stredy[1] - 1), (osa_X + a, osa_Y + stredy[1] - 1),
                                 (255, 0, 0), 1)
                    if crop_img[stredy[2] - 1, a] < 225:
                        hp_hodnota += 1
                        cv2.line(fotka, (osa_X + a, osa_Y + stredy[2] - 1), (osa_X + a, osa_Y + stredy[2] - 1),
                                 (255, 0, 0), 1)

                self.ukaz_printscreen_na_boku(fotka)
                # print("Naměřené pixely (modré): ATT={}, DEF={}, HP={}".format(att_hodnota, def_hodnota, hp_hodnota))
                # print("Celková délka baru (ATT bez bílé): {}".format(celkova_delka_att))

                # 22px na 1 hodnotu IV statu, rozmezí 0-15 pro každou hodnotu
                # Pokud nemáme zkalibrováno z prvního pokémona, vypočítáme to
                if self.jeden_bod_px is None:
                    self.jeden_bod_px = celkova_delka_att / 15
                    # print(f"Kalibrace uložena: 1 bod = {self.jeden_bod_px} px")

                att_hodnota = int(round(att_hodnota / self.jeden_bod_px, 0))
                def_hodnota = int(round(def_hodnota / self.jeden_bod_px, 0))
                hp_hodnota = int(round(hp_hodnota / self.jeden_bod_px, 0))

                # print(f"Jeden box je {self.jeden_bod_px}px. ATT={att_hodnota}, DEF={def_hodnota}, HP={hp_hodnota}")
                procento = (att_hodnota + def_hodnota + hp_hodnota) * 100 // 45

                # aktuální verze bez kruhů
                text = str(procento) + "%" + str(att_hodnota) + "-" + str(def_hodnota) + "-" + str(hp_hodnota)

                # print(f"text:{text} a délka je: {len(text)}")
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
                time.sleep(0.5)  # Krátká pauza před dalším pokusem, aby se nezahltil procesor
                nacteno = True

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1145, 606)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./img_pokeball.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet("border-image: url(./img_bg.jpg);")
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
        font.setPointSize(12)
        self.btn_prejmenovat.setFont(font)
        self.btn_prejmenovat.setStyleSheet("border-image: none;\n")
        self.btn_prejmenovat.setObjectName("btn_prejmenovat")
        self.vlevo.addWidget(self.btn_prejmenovat)
        self.btn_prejmenovat.clicked.connect(self.zacni_prejmenovavat)

        self.grpbx_kolik = QtWidgets.QGroupBox(self.centralwidget)
        self.grpbx_kolik.setMinimumSize(QtCore.QSize(0, 100))
        self.grpbx_kolik.setMaximumSize(QtCore.QSize(300, 150))
        font.setPointSize(8)
        self.grpbx_kolik.setFont(font)
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
                                       "background: rgba(0, 0, 0, 0.5);")
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
        font.setPointSize(12)
        self.spn_kolik_prejmenovat.setFont(font)
        self.spn_kolik_prejmenovat.setAutoFillBackground(False)
        self.spn_kolik_prejmenovat.setStyleSheet(
            "QSpinBox{border : 1px solid white; color: white; background-color: rgba(255,255,255,0);}")
        self.spn_kolik_prejmenovat.setObjectName("spn_kolik_prejmenovat")
        self.spn_kolik_prejmenovat.setMinimum(0)
        self.spn_kolik_prejmenovat.setMaximum(1000)
        self.verticalLayout_3.addWidget(self.spn_kolik_prejmenovat)
        self.vlevo.addWidget(self.grpbx_kolik)
        self.grpbx_prejmenovat = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grpbx_prejmenovat.sizePolicy().hasHeightForWidth())
        self.grpbx_prejmenovat.setSizePolicy(sizePolicy)
        self.grpbx_prejmenovat.setMinimumSize(QtCore.QSize(0, 150))
        self.grpbx_prejmenovat.setMaximumSize(QtCore.QSize(300, 300))
        font.setPointSize(8)
        self.grpbx_prejmenovat.setFont(font)
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
                                             "background: rgba(0, 0, 0, 0.5);")
        self.grpbx_prejmenovat.setObjectName("grpbx_prejmenovat")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.grpbx_prejmenovat)
        self.verticalLayout.setSpacing(0)
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
        font.setPointSize(12)
        self.spn_hranice_prejmenovani.setFont(font)
        self.spn_hranice_prejmenovani.setAutoFillBackground(False)
        # self.spn_hranice_prejmenovani.setStyleSheet("border-image: none;color:black;")
        self.spn_hranice_prejmenovani.setStyleSheet(
            "QSpinBox{border : 1px solid white; color: white; background-color: rgba(255,255,255,0);}")

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
        font.setPointSize(12)
        self.input_prejmenovat_na.setFont(font)
        font.setPointSize(8)
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
                                                    "background: rgba(255, 255, 255, 0.0);")

        self.chckbx_prejmenovat_posix.setChecked(True)
        self.chckbx_prejmenovat_posix.setAutoExclusive(False)
        self.chckbx_prejmenovat_posix.setObjectName("chckbx_prejmenovat_posix")
        self.verticalLayout.addWidget(self.chckbx_prejmenovat_posix)
        self.vlevo.addWidget(self.grpbx_prejmenovat)
        self.grpbx_preskocit = QtWidgets.QGroupBox(self.centralwidget)
        self.grpbx_preskocit.setMinimumSize(QtCore.QSize(0, 120))
        self.grpbx_preskocit.setMaximumSize(QtCore.QSize(300, 120))
        self.grpbx_preskocit.setFont(font)

        #############
        # Vlastní filtr
        self.chckbx_vlastni_filtr = QtWidgets.QCheckBox(self.grpbx_kolik)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chckbx_vlastni_filtr.sizePolicy().hasHeightForWidth())
        self.chckbx_vlastni_filtr.setSizePolicy(sizePolicy)
        self.chckbx_vlastni_filtr.setMaximumSize(QtCore.QSize(300, 16777215))
        self.chckbx_vlastni_filtr.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.chckbx_vlastni_filtr.setFont(font)
        self.chckbx_vlastni_filtr.setStyleSheet("border-image: none;\n"
                                                "background: rgba(255, 255, 255, 0.0);")

        self.chckbx_vlastni_filtr.setChecked(False)
        self.chckbx_vlastni_filtr.setAutoExclusive(False)
        self.chckbx_vlastni_filtr.setObjectName("chckbx_vlastni_filtr")
        self.verticalLayout_3.addWidget(self.chckbx_vlastni_filtr)
        #######################

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
                                           "background: rgba(0, 0, 0, 0.5);")
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

        #############
        # Přeskakovat Shiny
        self.chckbx_shiny_filtr = QtWidgets.QCheckBox(self.grpbx_kolik)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chckbx_shiny_filtr.sizePolicy().hasHeightForWidth())
        self.chckbx_shiny_filtr.setSizePolicy(sizePolicy)
        self.chckbx_shiny_filtr.setMaximumSize(QtCore.QSize(300, 16777215))
        self.chckbx_shiny_filtr.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily("JetBrains Mono")
        self.chckbx_shiny_filtr.setFont(font)
        self.chckbx_shiny_filtr.setStyleSheet("border-image: none;\n"
                                              "background: rgba(255, 255, 255, 0.0);")

        self.chckbx_shiny_filtr.setChecked(False)
        self.chckbx_shiny_filtr.setAutoExclusive(False)
        self.chckbx_shiny_filtr.setObjectName("chckbx_shiny_filtr")
        self.verticalLayout_2.addWidget(self.chckbx_shiny_filtr)
        #######################

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
        font.setPointSize(12)
        self.input_preskocit_prefix.setFont(font)
        font.setPointSize(8)
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
        self.btn_vyfotit.clicked.connect(self.vyfotit)

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
                                      "background: rgba(0, 0, 0, 0.5);\n"
                                      "color: yellow;")
        self.text_zona2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.text_zona2.setReadOnly(True)
        self.text_zona2.setObjectName("text_zona2")
        font.setBold(True)
        self.text_zona2.setFont(font)
        font.setBold(False)
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
        font.setPointSize(12)
        font.setBold(True)
        self.text_zona.setFont(font)
        self.text_zona.setStyleSheet("border-image: none;\n"
                                     "background: rgba(0, 0, 0, 0.5);\n"
                                     "color: white;")
        font.setPointSize(8)
        font.setBold(False)
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
        font.setBold(True)
        font.setPointSize(12)
        self.lbl_staty_pokemona.setFont(font)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(1)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        self.lbl_staty_pokemona.setGraphicsEffect(shadow)

        font.setPointSize(8)
        self.lbl_staty_pokemona.setStyleSheet("border-image: none;\n"
                                              # "background: rgba(0, 0, 0, 0.5);\n"
                                              "color: white;")
        self.lbl_staty_pokemona.setText("")
        # self.lbl_staty_pokemona.setScaledContents(True)
        # self.lbl_staty_pokemona.setWordWrap(True)
        self.lbl_staty_pokemona.setObjectName("lbl_staty_pokemona")
        self.lbl_staty_pokemona.setAlignment(QtCore.Qt.AlignLeft)
        self.vpravo.addWidget(self.lbl_staty_pokemona)
        self.lbl_printscreen = ImageWidgetWithRatio(self.centralwidget)
        # QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_printscreen.sizePolicy().hasHeightForWidth())
        self.lbl_printscreen.setSizePolicy(sizePolicy)
        self.lbl_printscreen.setMinimumSize(QtCore.QSize(200, 400))
        self.lbl_printscreen.setMaximumSize(QtCore.QSize(400, 800))
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
        self.chckbx_vlastni_filtr.setText(_translate("MainWindow", "Zadám vlastní filtr přímo"))
        self.chckbx_shiny_filtr.setText(_translate("MainWindow", "Přeskakovat pokémony začínající\nna SHINY"))
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


    def zjisti_pocet_pokemonu(self):
        # v daném výřezu zjisti počty pokemonu xx / yy, v případě filtru najde znak Q
        image = main.adb_printsreen()
        souradnice, topleft, bottomright = main.najdi_tlacitko("nadpis_pokemon.png")
        if souradnice != (0, 0):
            x = int(topleft[0])
            y = int(topleft[1]) + 50
            sx = int(bottomright[0])
            sy = int(bottomright[1]) + 60
            crop_img = image[y:sy, x:sx]
            if crop_img.size == 0:
                print("Chyba: prázdný výřez, zkontroluj souřadnice.")
                return 0
            else:
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                text = pytesseract.image_to_string(crop_img)
                text = text.split("/")[0].strip()
                return text
        else:
            print("Nenalezen nadpis Pokémon")

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
        self.text_zona.moveCursor(QtGui.QTextCursor.End)

    def napis_stav_maly_box(self, text):
        self.text_zona2.setReadOnly(False)
        self.text_zona2.insertPlainText(text + "\n")
        self.text_zona2.setReadOnly(True)
        self.text_zona2.moveCursor(QtGui.QTextCursor.End)

    def vymaz_text_zony(self, jakou=0):
        # Vymaže text zóny. Defaultně bez zadaní vymaže obě.
        if jakou == 0:
            self.text_zona.clear()
            self.text_zona2.clear()
        elif jakou == 1:
            self.text_zona.clear()
        elif jakou == 2:
            self.text_zona2.clear()

    def spust_prejmenovani(self):
        if main.btn_pokeball():  # PŘIDAT ŠANCI NA DALŠÍ POKUS
            # tlačítko nalezeno, lze pojračovat dále
            main.btn_seznam_pokemonu()

            if self.chckbx_vlastni_filtr.isChecked():
                self.napis_stav(
                    "Zvolte filtr na telefonu, čas 10 vteřin běží, pak se spustí automatické přejmenovávání !!!")
                for odpocet in range(10, 0, -1):
                    time.sleep(1)
                    self.napis_stav("Přejmenování začne za: " + str(odpocet - 1))

            if self.spn_kolik_prejmenovat.value() == 0:
                pocet_pokemonu = int(self.zjisti_pocet_pokemonu())
            else:
                pocet_pokemonu = int(self.spn_kolik_prejmenovat.value())
            # print("Maximálně počet pokémonů k přejmenování:", pocet_pokemonu)
            self.napis_stav("")
            self.napis_stav("Počet pokémonů k přejmenování: ".upper() + str(pocet_pokemonu))
            main.btn_pokemon()

            start = time.time()
            # print("Čas začátku: ", time.strftime('%H:%M:%S', time.localtime(start)))
            self.napis_stav_maly_box("Čas začátku: ".upper() + time.strftime('%H:%M:%S', time.localtime(start)))
            doba_trvani = 0

            def vypis_prubeh_prejmenovani(x, jmeno, img):
                puvodni_jmeno = main.najdi_jmeno_pokemona(img)
                self.napis_stav("Původní jméno pokémona #" + str(x + 1) + " " + puvodni_jmeno)

                # Přeskauji jméno začínající na SHINY
                if self.chckbx_shiny_filtr.isChecked():
                    delka = len("SHINY")
                    if puvodni_jmeno[0:delka] == "SHINY":
                        self.napis_stav("Pokemon #" + str(x + 1) + " začíná na SHINY. Přeskakuji...")
                        return 1

                if (self.chckbx_preskocit.isChecked()) & (len(self.input_preskocit_prefix.text()) > 0):
                    delka = len(self.input_preskocit_prefix.text())
                    if puvodni_jmeno[0:delka] == self.input_preskocit_prefix.text():
                        self.napis_stav("Pokemon #" + str(x + 1) + " začíná na zvolený text. Přeskakuji...")
                        return 1
                if puvodni_jmeno == jmeno:
                    self.napis_stav("Pokemon #" + str(x + 1) + " má správné jméno dle statů. Přeskakuji...")
                    return 1
                if self.spn_hranice_prejmenovani.value() >= int(novy_pokemon.procento):
                    self.napis_stav(
                        "Pokemon #" + str(
                            x + 1) + " splnil kritérium pro extra přejmenování. Přejmenovávám na " + jmeno)
                else:
                    self.napis_stav("Pokemon #" + str(x + 1) + " má hodnoty:" + jmeno)
                return 0

            preskocen_minuly = False
            for x in range(pocet_pokemonu):
                img = main.adb_printsreen()
                global novy_pokemon
                novy_pokemon = Pokemon()

                if lze_prejmenovat(img):
                    if not preskocen_minuly:
                        main.btn_menu_pokemonu()
                        main.btn_appraise()
                        main.klik_do_stredu()
                    novy_pokemon.jmeno = self.zjisti_atributy_pokemona(x)
                    staty_pokemona = "* : {}\n% : {}\nATT : {}\nDEF : {}\nHP : {}".format(novy_pokemon.hvezd,
                                                                                          novy_pokemon.procento,
                                                                                          novy_pokemon.att_power,
                                                                                          novy_pokemon.def_power,
                                                                                          novy_pokemon.hp_power)
                    self.lbl_staty_pokemona.setText(staty_pokemona)
                    # if doba_trvani != 0:
                    # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                    stav_prejmenovani = vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
                    # cv2.imwrite("./pokemoni/pkm " + str(x+1) + " " + str(novy_pokemon.jmeno) + ".png", img)
                    if stav_prejmenovani == 1:
                        preskocen_minuly = True
                    elif stav_prejmenovani == 0:
                        preskocen_minuly = False
                        main.klik_do_stredu()
                        while (True):
                            main.btn_prejmenuj_pokemona(novy_pokemon.jmeno)  # přejmenování pokémona
                            # kontrola přejmenování pokémona
                            img = main.adb_printsreen()
                            nove_jmeno = main.najdi_jmeno_pokemona(img)
                            self.napis_stav("Nové jméno pokémona #" + str(x + 1) + " " + nove_jmeno)
                            if novy_pokemon.jmeno == nove_jmeno:
                                # print("jmena jsou stejna")
                                break
                            # print("jmena se liší") # opakuj přejmenování když se jména liší

                    main.swipni_doprava()
                    time.sleep(1)

                    if doba_trvani == 0:
                        end = time.time()
                        doba_trvani = (end - start) // 1
                        self.napis_stav_maly_box("Odhadovaný čas konce za: ".upper() + str(
                            datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu))))

                        # print("Hotovo pokémonů:", x + 1)
                        # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                        # stav_prejmenovani = vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
                else:
                    self.napis_stav(
                        "Přeskakuji pokemona #" + str(x + 1) + " (nelze jej přejmenovat) na dalšího pokemona")
                    main.swipni_doprava()
                    time.sleep(1)
                # kontrola na ukončení přejmenovávání
                global ukonci_vlakno
                if ukonci_vlakno | (self.spn_kolik_prejmenovat.value() == (x + 1)):
                    self.btn_prejmenovat.setText("Spustit přejmenovávání")
                    self.btn_prejmenovat.setEnabled(True)
                    self.grpbx_kolik.setEnabled(True)
                    self.grpbx_prejmenovat.setEnabled(True)
                    self.grpbx_preskocit.setEnabled(True)
                    break

            konec = time.time()
            self.napis_stav_maly_box("Čas ukončení: ".upper() + time.strftime('%H:%M:%S', time.localtime(konec)))
            self.napis_stav_maly_box("Doba trvání: ".upper() + str(datetime.timedelta(seconds=int(konec - start))))
            main.klik_do_stredu()
            main.btn_krizek()
            self.napis_stav("KONEC")
            main.btn_krizek()

    def zacni_prejmenovavat(self):
        global t1, ukonci_vlakno
        ukonci_vlakno = False
        t1 = threading.Thread(target=self.spust_prejmenovani)
        t1.daemon = True
        if "Spustit přejmenovávání" == self.btn_prejmenovat.text():
            self.btn_prejmenovat.setDisabled(True)
            self.vymaz_text_zony()
            t1.start()
            time.sleep(2)
            if t1.is_alive():
                self.btn_prejmenovat.setText("Ukončit přejmenovávání")
            self.btn_prejmenovat.setEnabled(True)
            self.grpbx_kolik.setEnabled(False)
            self.grpbx_prejmenovat.setEnabled(False)
            self.grpbx_preskocit.setEnabled(False)

        else:
            ukonci_vlakno = True
            self.btn_prejmenovat.setText("Spustit přejmenovávání")
            self.btn_prejmenovat.setDisabled(True)
            self.grpbx_kolik.setEnabled(True)
            self.grpbx_prejmenovat.setEnabled(True)
            self.grpbx_preskocit.setEnabled(True)

    def vyfotit(self):
        main.vyfot_okno()

    def konec(self):
        # window.destroy()
        sys.exit()


def zobrazUI():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    app.exec_()
