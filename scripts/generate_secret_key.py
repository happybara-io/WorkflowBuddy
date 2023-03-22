from cryptography.fernet import Fernet

new_key: str = Fernet.generate_key().decode("utf-8")
print('### Your new SECRET Key ########:\n')
print(new_key)

input("Did you save this somewhere safe? 👀 [Enter]")
input("[!] No but really, did you save this in at least 2 secure places? If you lose it, your user's data will be locked away and unable to be regained. [Enter]")
input("[!!] This is the last stop! If you really did save it carefully, you may continue. Best of luck. [Enter]")
