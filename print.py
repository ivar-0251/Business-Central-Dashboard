import cups # type: ignore

# 1. Maak verbinding met de lokale CUPS-server
conn = cups.Connection()

# 2. Haal een lijst op met alle beschikbare printers
printers = conn.getPrinters()

# Toon de namen van de gekoppelde printers ter controle
print("Beschikbare printers:")
for printer_name in printers:
    print(f"- {printer_name}")


printer_name = list(printers.keys())[0]

bestandsnaam = "test_afdruk.txt"

taak_titel = "Test Afdruk via CUPS"

print(f"Versturen van afdruktaak '{taak_titel}' naar printer '{printer_name}' met bestand '{bestandsnaam}'...")
taak_id = conn.printFile(printer_name, bestandsnaam, taak_titel, {})
print(f"Afdruktaak verzonden met ID: {taak_id}")