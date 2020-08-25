# IV_PokemonGO
> Vypočte hodnotu IV pro mobilní hru Pokemon GO

### Požadavky na správný chod programu

- je potřeba mít nainstalován Tesseract https://github.com/UB-Mannheim/tesseract/wiki
- je nutné mít naisntalovány ovladače ADB pro Váš mobilní telefon

### Použití
- spusťte cmd "adb devices" k získání čísla Vašeho mobilu, aby bylo možné spouště příkaz adb s paramterm "-s"
- toto číslo zadejte do konstanty.py PHONE = "xxxxxxx" 
- poté by mělo být vše připraveno ke spustění programu main.py
- po spuštění stačí zmáčknout klávesu "w" a program začne s výpočty a přejmenováváním pokémonů (x%attack-defense-hp)
