import datetime
import json
import subprocess
import time

import cv2
import keyboard as keyboard
import numpy as np
import pytesseract

import konstanty


def start_programu():
    # cv2.namedWindow("PokemonGOsnimac", cv2.WINDOW_AUTOSIZE)  # Create window with freedom of dimensions

    def spust_adb_prikaz(text, sleep_time=2):
        subprocess.Popen(konstanty.ADB + text + " &")  # swipe o jeden řádek pokemonů
        time.sleep(sleep_time)

    def adb_printsreen():
        pipe = subprocess.Popen("adb shell screencap -p &",
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, shell=True)
        image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
        return cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    def vyfot_okno():
        printscreen = adb_printsreen()

        cv2.imwrite("./IMAGE1.png", printscreen)  # Save screenshot
        # cv2.namedWindow("PokemonGO snímač", cv2.WINDOW_AUTOSIZE)  # Create window with freedom of dimensions
        ims = cv2.resize(printscreen, (300, 600))  # Resize image
        cv2.imshow("PokemonGOsnimac", ims)  # Show image

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

    def najdi_horni_hranu(image):
        # Střed obrazovky X 1080 Y 540
        for delka_y in range(1080):
            if all(image[1080 + delka_y, 540] == [255, 255, 255]):
                return int(1080 + delka_y)
        return "hrana nenalezena"

    def najdi_spodni_hranu(image, horni_hrana):
        for delka_y in range(2160 - horni_hrana):
            if any(image[horni_hrana + delka_y, 540] != [255, 255, 255]):
                return int(horni_hrana + delka_y)
        return "hrana nenalezena"

    def zjisti_atributy_pokemona(poradi=1):
        nacteno = True

        while nacteno:
            try:
                screenshot = adb_printsreen()

                horni_hrana = najdi_horni_hranu(screenshot)
                spodni_hrana = najdi_spodni_hranu(screenshot, najdi_horni_hranu(screenshot))
                crop_img = screenshot[horni_hrana:spodni_hrana, 100:520]

                att_hodnota = 0
                def_hodnota = 0
                hp_hodnota = 0

                for a in range(420):
                    att_barva = crop_img[126, a]
                    def_barva = crop_img[229, a]
                    hp_barva = crop_img[333, a]
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
                return text

            except TypeError:
                print("Nepovedlo se načíst data pokemona... Není vidět tabulka s hodnotami")
                nacteno = True

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

    def btn_uprostred():
        # PROSTŘEDNÍ TLAČÍTKO tapnutí
        spust_adb_prikaz("tap 551 2026")

    def btn_seznam_pokemonu():
        # SBÍRKA POKEMONŮ TLAČÍTKO tapnutí
        spust_adb_prikaz("tap 238 1862")

    def btn_menu_pokemonu():
        # ŘAZENÍ POKEMONŮ(MENU POKEMONA) TLAČÍTKO tapnutí
        spust_adb_prikaz("tap 933 2025")

    def btn_appraise():
        # APPRAISE TLAČÍTKO tapnutí
        spust_adb_prikaz("tap 750 1617")

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

    # v daném výřezu zjisti počty pokemonu xx / yy, v případě filtru najde znak Q
    def zjisti_pocet_pokemonu():
        image = adb_printsreen()
        crop_img = image[200:250, 115:465]
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        text = pytesseract.image_to_string(crop_img)
        text = text.replace("(", "").replace(")", "")
        if text[0] == "Q":
            text = text.split("Q")
            return text[1]
        else:
            return text.split("/")[0]

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

    while True:

        if keyboard.is_pressed('q'):  # klávesa "q" konec programu
            # cv2.destroyAllWindows()
            break

        if keyboard.is_pressed('w'):  # klávesa "w" začne s hromadným přejmenováváním
            print("macknuto W")
            # btn_uprostred()
            # btn_seznam_pokemonu()
            pocet_pokemonu = int(zjisti_pocet_pokemonu())
            print("celkem pokumonu k přejmenování:", pocet_pokemonu)

            btn_pokemon()

            start = time.time()
            print("Čas začátku: ", time.strftime('%H:%M:%S', time.localtime(start)))
            doba_trvani = 0

            for x in range(pocet_pokemonu):

                img = adb_printsreen()

                if lze_prejmenovat(img):
                    btn_menu_pokemonu()
                    btn_appraise()
                    klik_do_stredu()
                    jmeno = zjisti_atributy_pokemona(x)
                    if doba_trvani != 0:
                        print("Pokemon #", (x + 1), " má hodnoty:", jmeno)
                    # cv2.imwrite("./pokemoni/pkm " + str(x+1) + " " + str(jmeno) + ".png", img)

                    klik_do_stredu()
                    btn_prejmenuj_pokemona(jmeno)
                    swipni_doprava()
                    time.sleep(5)

                    if doba_trvani == 0:
                        end = time.time()
                        doba_trvani = (end - start) // 1
                        # print("odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))
                        print("Odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))

                        # print("Hotovo pokémonů:", x + 1)
                        print("Pokemon #", (x + 1), " má hodnoty:", jmeno)
                else:
                    print("Přeskakuji pokemona #", (x + 1), " (nelze jej přejmenovat) na dalšího pokemona")
                    swipni_doprava()
                    time.sleep(5)

            konec = time.time()
            print("Čas ukončení: ", time.strftime('%H:%M:%S', time.localtime(konec)), "\t doba trvání",
                  datetime.timedelta(seconds=(konec - start)))
            btn_uprostred()
            print("konec")
            break

        if keyboard.is_pressed('e'):  # klávesa "e" vyfotí okno
            vyfot_okno()
            break


if __name__ == '__main__':
    # print(subprocess.Popen("adb shell wm size"))  # Physical size my phone: 1080x2160
    start_programu()
