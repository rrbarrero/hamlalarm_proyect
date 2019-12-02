import requests
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label



BASE_URL = 'https://host'

def show_message(msg):
    return Popup(title='Response',
                content=Label(text=msg, font_size=28),
                size_hint=(None, None), size=(400, 200))

class ClientfeederApp(App):
    
    def alarma_on(self):
        res = requests.get(BASE_URL+'true')
        popup = show_message("{}".format(res.status_code))
        popup.open()
        
    
    def alarma_off(self):
        res = requests.get(BASE_URL+'false')
        popup = show_message("{}".format(res.status_code))
        popup.open()
        

app = ClientfeederApp()
app.run()
