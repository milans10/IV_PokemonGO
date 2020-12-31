#  Copyright (c) 2020. Created by Milan Svarc
import json
import re
import subprocess
import time

import cv2
import numpy as np
import pyglet
import pytesseract

import appkaUI
import konstanty


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


## ADB příkazy
def spust_adb_prikaz(text, sleep_time=2):
    subprocess.Popen(konstanty.ADB + text + " &")  # swipe o jeden řádek pokemonů
    time.sleep(sleep_time)


def adb_printsreen(grayscale=False):
    pipe = subprocess.Popen("adb shell screencap -p &",
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, shell=True)
    image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
    if grayscale:
        return cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    else:
        return cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)


def swipni_doprava():
    # swipe o jeden řádek pokemonů
    spust_adb_prikaz("swipe 940 1080 140 1080 1500")


def swipni_pokemony():
    # swipe o jeden řádek pokemonů
    spust_adb_prikaz("swipe 140 1296 140 1000 1500")


def btn_prejmenuj_pokemona(nove_jmeno=""):
    spust_adb_prikaz("tap 540 915")  # tapnutí na TLAČÍTKO přejmenování pokémona

    for ciselnik in range(13):
        spust_adb_prikaz("keyevent 67", 0)  # klávesa DELETE

    time.sleep(2)
    if len(nove_jmeno) > 12:
        prikaz = "keyboard text 'TOO LONG'"
    else:
        prikaz = "keyboard text '" + nove_jmeno + "'"
        spust_adb_prikaz(prikaz, 3)

    # tlačítko HOTOVO na virtuální klávesnici
    spust_adb_prikaz("tap 990 2097")

    # tlačítko OK pro potvrzení nového jména
    spust_adb_prikaz("tap 540 1170", 3)


def najdi_jmeno_pokemona(screenshot):
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


def najdi_tlacitko(img_tlacitka):
    img = adb_printsreen(True)  # obrazek kde budu hledat, zde screenshot obrazovky
    template = cv2.imread(img_tlacitka, 0)  # obrazek který hledám
    w, h = template.shape[::-1]

    meth = eval('cv2.TM_CCOEFF_NORMED')  # metoda vyhledávání
    res = cv2.matchTemplate(img, template, meth)
    threshold = 0.7  # nastavení míry hranice rozpoznání
    loc = np.where(res >= threshold)

    if len(loc[0]) > 0:  # kontrola jestli je neco nalezeno
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)
    else:
        # print("nenalezeno")
        top_left = bottom_right = (0, 0)

    def stred_nalezu(p1, p2):
        return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)

    return stred_nalezu(top_left, bottom_right)


def vyfot_okno():
    printscreen = adb_printsreen()
    cv2.imwrite("./IMAGE1.png", printscreen)  # Save screenshot
    # cv2.namedWindow("PokemonGO snímač", cv2.WINDOW_AUTOSIZE)  # Create window with freedom of dimensions
    ims = cv2.resize(printscreen, (300, 600))  # Resize image
    cv2.imshow("PokemonGOsnimac", ims)  # Show image


def btn_uprostred():
    # PROSTŘEDNÍ TLAČÍTKO tapnutí
    # spust_adb_prikaz("tap 551 2026")
    if (x := najdi_tlacitko("btn_krizek.png")) == (0, 0):
        if (x := najdi_tlacitko("btn_krizek2.png")) == (0, 0):
            # nenalez
            print("Tlačítko s křížkem narozpoznáno")
            return
    spust_adb_prikaz("tap " + str(x[0]) + " " + str(x[1]))


def btn_seznam_pokemonu():
    # SBÍRKA POKEMONŮ TLAČÍTKO tapnutí
    spust_adb_prikaz("tap 238 1862")


def btn_menu_pokemonu():
    # ŘAZENÍ POKEMONŮ(MENU POKEMONA) TLAČÍTKO tapnutí
    spust_adb_prikaz("tap 933 2025")


def btn_appraise():
    # APPRAISE TLAČÍTKO tapnutí
    souradnice = najdi_tlacitko("btn_appraise.png")
    if souradnice != (0, 0):
        spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))


def btn_pokemon(pozice_na_radku=1):
    # pokemon políčko je X 330 na Y 390
    if pozice_na_radku > 3:
        pozice_na_radku = 3  # více než 3 pokemoni na řádku nejsou
    souradnice_x = 198 + ((pozice_na_radku - 1) * 330)
    prikaz = "tap " + str(souradnice_x) + " 612"

    spust_adb_prikaz(prikaz)  # 1.POKEMON VLEVO NAHORE tapnutí


def klik_do_stredu():
    # tapnutí do stredu obrazovky
    spust_adb_prikaz("tap 540 1080", 3)


if __name__ == '__main__':
    # print(subprocess.Popen("adb shell wm size"))  # Physical size my phone: 1080x2160

    # Načtení fontu
    pyglet.font.add_file('./JetBrainsMono-Regular.ttf')
    pyglet.font.load('JetBrains Mono')

    # zapnutí ADB deamona
    adb = subprocess.Popen(['adb.exe', 'start-server'])

    appkaUI.zobrazUI()
