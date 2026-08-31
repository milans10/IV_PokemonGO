#  Copyright (c) 2026. Created by Milan Svarc
import re
import subprocess
import time

import cv2
import numpy as np
import pyglet
import pytesseract

import appkaUI


# ADB příkazy
def spust_adb_prikaz(text, sleep_time=1):
    args = text.split()
    subprocess.Popen(["adb", "shell", "input"] + args)
    time.sleep(sleep_time)


def adb_printsreen(grayscale=False):
    pipe = subprocess.Popen(
        ["adb", "exec-out", "screencap", "-p"],
        stdout=subprocess.PIPE
    )
    image_bytes = pipe.stdout.read()
    flag = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    return cv2.imdecode(np.frombuffer(image_bytes, np.uint8), flag)


def swipni_doprava():
    # swipe doprava základná čas swipu je 400ms a celkový je 800ms
    spust_adb_prikaz("swipe 940 1080 140 1080 400", sleep_time=0.8)


def swipni_pokemony_nahoru():
    # swipe o jeden řádek pokemonů
    spust_adb_prikaz("swipe 140 1296 140 1000 400", sleep_time=0.8)


def btn_prejmenuj_pokemona(nove_jmeno=""):
    # tapnutí na TLAČÍTKO přejmenování pokémona
    souradnice, *_ = najdi_tlacitko("btn_rename.png")
    if souradnice != (0, 0):
        spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))

    for ciselnik in range(13):
        spust_adb_prikaz("keyevent 67", 0)  # klávesa DELETE

    time.sleep(1)
    if len(nove_jmeno) > 12:
        prikaz = "keyboard text 'TOO LONG'"
        print(prikaz)
    else:
        # jmeno bez kruhu
        prikaz = "keyboard text '" + nove_jmeno + "'"
        spust_adb_prikaz(prikaz, 2)

    # tlačítko HOTOVO na virtuální klávesnici
    spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(
        int(souradnice[1])))  # tapnutí do prostoru nahoře, pro zavření klávesnice
    spust_adb_prikaz("tap " + str(int(200)) + " " + str(int(200)))

    # tlačítko OK pro potvrzení nového jména
    souradnice, *_ = najdi_tlacitko("btn_rename_ok.png")
    if souradnice != (0, 0):
        spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))
    else:
        print("nenalezeno OK rename")


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
        osa_y = min(loc[0])
        osa_x = max(loc[1])
        crop_img = img_gray[osa_y:osa_y + h + 40, 50:osa_x]
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
        return (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2

    return stred_nalezu(top_left, bottom_right), top_left, bottom_right


def vyfot_okno():
    printscreen = adb_printsreen()
    ims = cv2.resize(printscreen, (300, 600))  # Resize image
    cv2.imshow("PokemonGOsnimac", ims)  # Show image
    # cv2.imwrite("obrazek.png", printscreen)


def btn_krizek():
    # PROSTŘEDNÍ TLAČÍTKO tapnutí
    while True:
        x, *_ = najdi_tlacitko("btn_krizek.png")
        if x != (0, 0):
            break
        x, *_ = najdi_tlacitko("btn_krizek2.png")
        if x != (0, 0):
            break
        print("Tlačítko s křížkem nenalezeno !!!")

    spust_adb_prikaz("tap " + str(x[0]) + " " + str(x[1]))


def btn_pokeball():
    # TLAČÍTKO NA HLAVNÍ OBRAZOVCE S MAPOU, IKONA POKEBALLU SLOUŽÍCÍ PRO VSTUP DO MENU
    while True:
        souradnice, *_ = najdi_tlacitko("btn_pokeball.png")
        if souradnice != (0, 0):
            spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))
            return True
        print("Tlačítko pokéballu nenalezeno!!!")


def btn_seznam_pokemonu():
    # SBÍRKA POKEMONŮ TLAČÍTKO tapnutí
    # spust_adb_prikaz("tap 238 1862")
    souradnice, *_ = najdi_tlacitko("btn_pokemon.png")
    if souradnice != (0, 0):
        spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))


def btn_menu_pokemonu():
    # ŘAZENÍ POKEMONŮ(MENU POKEMONA) TLAČÍTKO tapnutí
    # spust_adb_prikaz("tap 933 2025")
    souradnice, *_ = najdi_tlacitko("btn_menu_pokemona.png")
    if souradnice != (0, 0):
        spust_adb_prikaz("tap " + str(int(souradnice[0])) + " " + str(int(souradnice[1])))


def btn_appraise():
    # APPRAISE TLAČÍTKO tapnutí
    souradnice, *_ = najdi_tlacitko("btn_appraise.png")
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
    spust_adb_prikaz("tap 540 1080", 2)


if __name__ == '__main__':
    # print(subprocess.Popen("adb shell wm size"))  # Physical size my phone: 1080x2160

    # Načtení fontu
    pyglet.font.add_file('./JetBrainsMono-Regular.ttf')
    pyglet.font.load('JetBrains Mono')

    # zapnutí ADB deamona
    adb = subprocess.Popen(['adb.exe', 'start-server'])

    appkaUI.zobrazUI()

# přidat počítadlo přejmenovaných a nepřejmenovaných
# Nové jméno pokémona #XXX Jméno nerozpoznáno - tady je nutný SKIP nejde vůbec menit jméno
