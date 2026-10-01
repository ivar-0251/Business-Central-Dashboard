from O365 import Account
from dotenv import load_dotenv
from os import environ as env

load_dotenv()

# 1. Vul hier de gegevens van je Azure App-registratie in
CLIENT_ID = env["client_id_mail"]
CLIENT_SECRET = env["client_secret_mail"]
TENANT_ID = env["tenant_id_mail"]

# Het e-mailadres van de gedeelde mailbox
SHARED_MAILBOX_ADDRESS = env["mailbox_mail"]

def stuur_mail_via_linux():
    credentials = (CLIENT_ID, CLIENT_SECRET)
    
    # Initialiseer het account met de 'credentials' flow (geschikt for daemons/scripts)
    account = Account(credentials, auth_flow_type='credentials', tenant_id=TENANT_ID)
    
    print("Bezig met authenticeren bij Microsoft Graph...")
    if account.authenticate():
        print("Authenticatie succesvol!")
        
        # Koppel specifiek de shared mailbox als bron (resource)
        mailbox = account.mailbox(resource=SHARED_MAILBOX_ADDRESS)
        
        # Maak een nieuw e-mailbericht aan
        message = mailbox.new_message()
        
        # E-mail details invullen
        message.to.add('ivarkoldewijn@gmail.com')
        message.subject = 'Automatisch rapport vanaf Linux'
        
        # Gebruik .body voor platte tekst, of .html_body voor HTML opmaak
        message.body = 'Beste lezer,\n\nDit is een automatisch gegenereerde mail vanuit een Linux script via de Shared Mailbox.'
        
        # Optioneel: Bijlage toevoegen vanaf je Linux bestandssysteem
        # message.attachments.add('/var/log/syslog.log')
        
        print(f"E-mail aan het verzenden namens {SHARED_MAILBOX_ADDRESS}...")
        message.send()
        print("E-mail succesvol verzonden!")
    else:
        print("Authenticatie mislukt. Controleer de ID's en het Secret.")

if __name__ == '__main__':
    stuur_mail_via_linux()
