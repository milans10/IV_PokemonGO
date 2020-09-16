#  Copyright (c) 2020. Created by Milan Svarc

class Pokemon:

    def __init__(self, jmeno="není", att_power=0, def_power=0, hp_power=0):
        super().__init__()
        self.jmeno = jmeno
        self.att_power = att_power
        self.def_power = def_power
        self.hp_power = hp_power
        self.procento = self.vypocti_procento()
        self.hvezd = self.vypocti_pocet_hvezd()

    def vypocti_procento(self):
        vysledek = round(((self.att_power + self.def_power + self.hp_power) * 100 / 45) * 10) / 10.0
        return vysledek

    def vypocti_pocet_hvezd(self):
        # Rozmezí pro označení 0* až 4*(IV perfect)
        # 0 * 0 – 48.9 %
        # 1 * 51.1 – 64.4 %
        # 2 * 66.7 – 80 %
        # 3 * 82.2 – 97.8 %
        # 4 * 100 %
        if self.procento <= 48.9:
            return "0*"
        elif (self.procento >= 51.1) & (self.procento < 64.4):
            return "1*"
        elif (self.procento >= 66.7) & (self.procento < 80):
            return "2*"
        elif (self.procento >= 82.2) & (self.procento < 97.8):
            return "3*"
        elif (self.procento == 100):
            return "4*"

        return "šedá zóna"

    def vypis_informace(self):
        print("jméno=", self.jmeno)
        print("att=", self.att_power)
        print("def=", self.def_power)
        print("hp=", self.hp_power)
        print("%=", self.procento)
        print("hvezd=", self.hvezd)
