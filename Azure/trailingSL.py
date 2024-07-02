import MetaTrader5 as mt5
import os

def InitializeAccounts():
    print("----------InitializeAccounts---------")
    
    PATH = os.path.abspath(__file__)
    DIRECTORY = os.path.dirname(os.path.dirname(PATH))

    instance_path = os.path.join(DIRECTORY, "Instances", str(2), "terminal64.exe")

    if not mt5.initialize(login=int(97576996), password="*EgU9P2R#p*dNyV", server="XMGlobal-MT5 5", path=instance_path):
        print("Failed to initialize MT5 terminal from", instance_path)
        print("Error:", mt5.last_error())
    else:
        print("MT5 initialized successfully for account ID: 97576996")

