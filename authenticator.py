from functools import wraps
import ipaddress
import os, dotenv

from flask import redirect, session, url_for, request

dotenv.load_dotenv()  # Load environment variables from .env file

TRUSTED_NETWORKS = [
    ipaddress.ip_network(os.environ["TRUSTED_IP"].strip()),
    ipaddress.ip_network("127.0.0.1"),
    ipaddress.ip_network("10.0.102.0/24"),
    ipaddress.ip_network("10.0.104.0/24")
]

def is_trusted_ip():
    try:
        client_ip = ipaddress.ip_address(request.remote_addr)
    except (TypeError, ValueError):
        return False
    print(client_ip)
    print(TRUSTED_NETWORKS)
    return any(client_ip in net for net in TRUSTED_NETWORKS)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_trusted_ip():
            print(f"Access granted from trusted IP: {request.remote_addr}")
            return f(*args, **kwargs)  # geen login nodig vanaf vertrouwd IP
        if "user" not in session:
            return redirect(url_for("auth.login"))  # of "login" zonder Blueprint
        return f(*args, **kwargs)
    return wrapper