#  Copyright (c) 2020. Created by Milan Svarc

import datetime
import json
import subprocess
import threading
import time
from tkinter import *
from tkinter import scrolledtext

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageTk

import konstanty
from pokemon import Pokemon


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

    def ukaz_printscreen_na_boku(screenshot):
        photo2 = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        photo2 = Image.fromarray(photo2)
        photo2 = photo2.resize((200, 400), Image.ANTIALIAS)

        global imgtk
        imgtk = ImageTk.PhotoImage(image=photo2)
        img_bg2 = Label(master=gui, image=imgtk)
        img_bg2.grid(row=0, column=2, rowspan=20, pady=5, padx=5)

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

    def najdi_staty():
        global prostredek, crop_img, stredy
        screenshot = adb_printsreen()

        ukaz_printscreen_na_boku(screenshot)  # ukáže screenshot na boku okna

        img_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
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

    def zjisti_atributy_pokemona(poradi=1):
        nacteno = True

        while nacteno:
            try:
                crop_img, delka, stredy = najdi_staty()
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

                if extra_prejmenovani.get() != 0:
                    # jde se přejmovávat pokud splňuje nastavený limit
                    if int(hranice_na_prejmenovani.get()) >= int(procento):
                        if extra_prejmenovani_posix.get() == 1:
                            return extra_prejmenovat_na.get() + "-" + str(procento) + "%"
                        return extra_prejmenovat_na.get()
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

    def spust_prejmenovani():
        # btn_uprostred()
        # btn_seznam_pokemonu()
        if kolik_prejmenovat.get() == 0:
            pocet_pokemonu = int(zjisti_pocet_pokemonu())
        else:
            pocet_pokemonu = int(kolik_prejmenovat.get())
        # print("Maximálně počet pokémonů k přejmenování:", pocet_pokemonu)
        napis_stav("Maximálně počet pokémonů k přejmenování:" + str(pocet_pokemonu))
        btn_pokemon()

        start = time.time()
        # print("Čas začátku: ", time.strftime('%H:%M:%S', time.localtime(start)))
        napis_stav("Čas začátku: " + time.strftime('%H:%M:%S', time.localtime(start)))
        doba_trvani = 0

        def vypis_prubeh_prejmenovani(x, jmeno, img):
            napis_stav("Původní jméno pokémona #" + str(x + 1) + " " + najdi_jmeno_pokemona(img))
            if hranice_na_prejmenovani.get() >= int(novy_pokemon.procento) :
                napis_stav(
                    "Pokemon #" + str(x + 1) + " splnil kritérium pro extra přejmenování. Přejmenovávám na " + jmeno)
            else:
                napis_stav("Pokemon #" + str(x + 1) + " má hodnoty:" + jmeno)

        for x in range(pocet_pokemonu):
            img = adb_printsreen()
            global novy_pokemon
            novy_pokemon = Pokemon()

            if lze_prejmenovat(img):
                btn_menu_pokemonu()
                btn_appraise()
                klik_do_stredu()
                novy_pokemon.jmeno = zjisti_atributy_pokemona(x)
                if doba_trvani != 0:
                    # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                    vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
                # cv2.imwrite("./pokemoni/pkm " + str(x+1) + " " + str(novy_pokemon.jmeno) + ".png", img)

                klik_do_stredu()
                btn_prejmenuj_pokemona(novy_pokemon.jmeno)
                # kontrola přejmenování pokémona
                img = adb_printsreen()
                napis_stav("Nové jméno pokémona #" + str(x + 1) + " " + najdi_jmeno_pokemona(img))

                swipni_doprava()
                time.sleep(5)

                if doba_trvani == 0:
                    end = time.time()
                    doba_trvani = (end - start) // 1
                    # print("odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))
                    # print("Odhadovaný čas konce za", datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu)))
                    napis_stav(
                        "Odhadovaný čas konce za" + str(datetime.timedelta(seconds=(doba_trvani * pocet_pokemonu))))

                    # print("Hotovo pokémonů:", x + 1)
                    # print("Pokemon #", (x + 1), " má hodnoty:", novy_pokemon.jmeno)
                    vypis_prubeh_prejmenovani(x, novy_pokemon.jmeno, img)
            else:
                # print("Přeskakuji pokemona #", (x + 1), " (nelze jej přejmenovat) na dalšího pokemona")
                napis_stav("Přeskakuji pokemona #" + str(x + 1) + " (nelze jej přejmenovat) na dalšího pokemona")
                swipni_doprava()
                time.sleep(5)
            # kontrola na ukončení přejmenovávání
            global ukonci_vlakno
            if ukonci_vlakno | (kolik_prejmenovat.get() == (x + 1)):
                btn_prejmenovat_text.set("Spustit přejmenovávání")
                btn_prejmenovat.config(state="normal")
                break

        konec = time.time()
        # print("Čas ukončení: ", time.strftime('%H:%M:%S', time.localtime(konec)), "\t doba trvání", datetime.timedelta(seconds=(konec - start)))
        napis_stav("Čas ukončení: " + time.strftime('%H:%M:%S', time.localtime(konec)) + "\t doba trvání" + str(
            datetime.timedelta(seconds=(konec - start))))
        btn_uprostred()
        # print("Konec")
        napis_stav("Konec")

    def konec():
        window.destroy()
        sys.exit()

    def zacni():
        global t1, ukonci_vlakno
        ukonci_vlakno = False
        t1 = threading.Thread(target=spust_prejmenovani)
        t1.daemon = True

        if btn_prejmenovat_text.get() == "Spustit přejmenovávání":
            btn_prejmenovat.config(state="disabled")
            t1.start()
            time.sleep(2)
            if t1.is_alive():
                btn_prejmenovat_text.set("Ukončit přejmenovávání")
            btn_prejmenovat.config(state="normal")

        else:
            ukonci_vlakno = True
            btn_prejmenovat_text.set("Spustit přejmenovávání")
            btn_prejmenovat.config(state="disabled")

    def napis_stav(text):
        txt_prubeh.config(state=NORMAL)
        txt_prubeh.insert(END, text + "\n")
        txt_prubeh.config(state=DISABLED)

    window = Tk()
    # window.minsize(957, 400)
    # window.maxsize(957, 400)
    # window.geometry("957x400")
    window.title("IV Pokémon GO")
    window.iconphoto(False, PhotoImage(file='img_pokeball.png'))
    window.configure(bg='black')

    gui = Frame(window, bg="black", relief=RAISED, borderwidth=1)

    btn_prejmenovat_text = StringVar()
    btn_prejmenovat_text.set("Spustit přejmenovávání")
    btn_prejmenovat = Button(master=gui, textvariable=btn_prejmenovat_text, command=zacni)
    btn_prejmenovat.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    Label(gui, text="Přejmenovat pokémonů (0=vše ... 100 max)").grid(row=1, column=0, sticky="nsew", padx=5)

    kolik_prejmenovat = Scale(gui, from_=0, to=100, orient=HORIZONTAL)
    kolik_prejmenovat.set(1)
    kolik_prejmenovat.grid(row=2, column=0, sticky="nsew", padx=5)

    # Sekce extra přejmenování
    sekce_prejmenovat = LabelFrame(gui, text="Extra přejmenovat")
    sekce_prejmenovat.grid(row=3, padx=5, pady=5, rowspan=5, sticky="ewns")

    extra_prejmenovani = IntVar()
    extra_prejmenovani.set(0)
    extra_prejmenovani_posix = IntVar()
    extra_prejmenovani_posix.set(1)

    def stav_extra_prejmenovat():
        if extra_prejmenovani.get() == 0:
            hranice_na_prejmenovani.config(state='disabled')
            extra_prejmenovat_na.config(state='disabled')
            extra_prejmenovat_na_posix.config(state='disabled')
        else:
            hranice_na_prejmenovani.config(state='normal')
            extra_prejmenovat_na.config(state='normal')
            extra_prejmenovat_na_posix.config(state='normal')

    Checkbutton(sekce_prejmenovat, text="Přejmenovat pokémona s % nižším než", variable=extra_prejmenovani,
                command=stav_extra_prejmenovat).pack()
    hranice_na_prejmenovani = Scale(sekce_prejmenovat, from_=0, to=100, orient=HORIZONTAL)
    hranice_na_prejmenovani.set(80)  # hranice pro 2*
    hranice_na_prejmenovani.pack(fill=X, padx=10)
    Label(sekce_prejmenovat, text="přejmovat na").pack()

    hodnota_extra_prejmenovat_na = StringVar()

    def maximalne_znaku(*args):
        hodnota = extra_prejmenovat_na.get()
        if extra_prejmenovani_posix.get() == 1:
            if len(hodnota) > 8:
                extra_prejmenovat_na.delete(0, END)
                extra_prejmenovat_na.insert(0, hodnota[:8])
        else:
            if len(hodnota) > 12:
                extra_prejmenovat_na.delete(0, END)
                extra_prejmenovat_na.insert(0, hodnota[:12])
        return

    hodnota_extra_prejmenovat_na.trace_add("write", maximalne_znaku)

    extra_prejmenovat_na = Entry(sekce_prejmenovat, textvariable=hodnota_extra_prejmenovat_na)
    extra_prejmenovat_na.pack(fill=X, padx=10, pady=5)

    extra_prejmenovat_na_posix = Checkbutton(sekce_prejmenovat, text="přidat na konec % (např. 97%)",
                                             variable=extra_prejmenovani_posix, command=stav_extra_prejmenovat)
    extra_prejmenovat_na_posix.pack()

    stav_extra_prejmenovat()

    btn_vyfot = Button(master=gui, text="Udělat printscreen", command=vyfot_okno).grid(row=9, column=0, sticky="nsew",
                                                                                       padx=5,
                                                                                       pady=5)
    btn_konec = Button(master=gui, text="Konec", command=konec).grid(row=10, column=0, sticky="nsew", padx=5,
                                                                     pady=5)

    image = Image.open("img_bg.png")
    image = image.resize((270, 270), Image.ANTIALIAS)
    photo = ImageTk.PhotoImage(image)

    img_bg = Label(master=gui, image=photo)
    img_bg.grid(row=11, column=0, pady=5, padx=5)

    # Prostřední sekce
    txt_prubeh = scrolledtext.ScrolledText(master=gui)
    txt_prubeh.config(state=DISABLED)
    txt_prubeh.grid(row=0, column=1, rowspan=20, pady=5, padx=5, sticky="nsew")

    gui.grid(sticky="nsew")

    window.mainloop()


if __name__ == '__main__':
    # print(subprocess.Popen("adb shell wm size"))  # Physical size my phone: 1080x2160
    start_programu()
