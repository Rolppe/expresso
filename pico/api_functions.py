# api_functions.py (DNS korjattu '8.8.8.8':ksi ristiriidan poistamiseksi)

# Funktion for WiFi connection creation
def set_station(time_module, network_module, ssid, password):
    
    # Create station module
    station = network_module.WLAN(network_module.STA_IF)
    station.active(True)
    
    # Set wifi SSID and Password
    station.connect(ssid, password)
    
    # Define static ip address
    station.ifconfig(('192.0.2.17', '255.255.255.0', '192.0.2.18', '8.8.8.8')) 
    
    # Create object for ip address
    ip_address = station.ifconfig()[0]
    
    # Set maxium wait time for 5 seconds 
    max_wait = 5
    
    # Create connection wait loop
    while max_wait > 0:
        
        # If connectiod succeed or failed: brake the loop
        if station.status() < 0 or station.status() >= 3:
            break
        
        # Decrease 1 second from waiting time
        max_wait -= 1
                
        # Set delay for one second
        time_module.sleep(1)
        
    # If there's a error in connection: return False and inform from error
    if station.isconnected == False:
        raise RuntimeError('network connection failed')
        return False
    
    # Otherwise inform from succesful connection and show link to ip in browser and return True
    else:
        print('Connected')
        print('Api at the address: <a href="http://{0}" target="_blank">{0}</a>'.format(ip_address))
        status = station.ifconfig()
        print('ip = ' , status[0])
        return True


# Function for two ways connection
def set_socket(socket,time_module):
    
    # Create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Clear port
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set port to 80
    port = 80

    # Create loop for binding
    while True:
        try:
            # Bind port to socket
            s.bind(('', port))
            s.listen(5)
            
            # Break the loop
            break
        
        # If there's an error. Inform about it
        except OSError as e:
            if e.errno == 98:
                print(f"Port {port} is already in use. Waiting for it to become available...")
            
            # Wait for one second
            time_module.sleep(1)  
    
    # Return socket
    return s

def parse_request(brew_data, request, save_settings, json):
    # From request: search for brew_temperature for numeric values
    if 'GET /set_value?brew_temperature=' in request:
            
        # Parse numeric values from request string
        brew_temperature = request.split('GET /set_value?brew_temperature=')[1].split('&')[0]
        steam_temperature = request.split('GET /set_value?brew_temperature=')[1].split('&')[1].split('=')[1]
        pre_infusion_time = request.split('GET /set_value?brew_temperature=')[1].split('&')[2].split('=')[1]
        pre_heat_time = request.split('GET /set_value?brew_temperature=')[1].split('&')[3].split('=')[1]
        pressure_soft_release_time = request.split('GET /set_value?brew_temperature=')[1].split('&')[4].split('=')[1]

        # Transform values to integer
        brew_temperature = int(brew_temperature)
        pre_infusion_time = int(pre_infusion_time)
        steam_temperature = int(steam_temperature)
        pressure_soft_release_time = int(pressure_soft_release_time)
        pre_heat_time = int(pre_heat_time)
        
        # Store values to brew_data object
        brew_data.set_settings(brew_temperature, steam_temperature, pre_infusion_time, pressure_soft_release_time, pre_heat_time)
                    
        # Store values to file
        save_settings(brew_data, json)
        
        
# Function for creating HTML response
def response_HTML(brew_data):

    # Get settings from brew_data object
    brew_temperature, steam_temperature, pre_infusion_time, pressure_soft_release_time, pre_heat_time = brew_data.get_settings()
    
    # Get the states of the switches from brew_data object
    brew_switch_state, steam_switch_state, water_switch_state = brew_data.get_switches_state()
    
    # Button color is green if off and red if on
    brew_switch_color = 'red' if brew_switch_state else 'green'
    steam_switch_color = 'red' if steam_switch_state else 'green'
    water_switch_color = 'red' if water_switch_state else 'green'
    
    # Return HTML
    return f"""HTTP/1.1 200 OK
Content-type:text/html

<html>
  <head>
    <title>Silvia Pico</title>
  </head>
  <body>
    <h1>Brewing setup</h1>
    <form action="/set_value" method="get">
      Brewing temperature (&#8451;): <input type="number" name="brew_temperature" value = "{brew_temperature}">
      <br><br>
      Steam temperature (&#8451;): <input type="number" name="steam_temperature" value = "{steam_temperature}">
      <br><br>
      Pre-infusion time (s): <input type="number" name="pre_infusion_time" value = "{pre_infusion_time}">
      <br><br>
      Pre-heat time (s): <input type="number" name="pre_heat_time" value = "{pre_heat_time}">
      <br><br>
      Pressure soft-release time (s): <input type="number" name="pressure_soft_release_time" value = "{pressure_soft_release_time}">
      <br><br>
      <input type="submit" value="Set values and refresh" name="set_values_">
    </form>
    <form action="/set_value" method="get">
      <button type = "submit" name = "brew_switch" value = "true" style = "background-color:{brew_switch_color}">Brew</button>
    </form>
    <form action="/set_value" method="get">
      <button type="submit" name="water_switch" value = "true" style="background-color:{water_switch_color}">Water</button>
    </form>
    <form action="/set_value" method="get">
      <button type="submit" name="steam_switch" value = "true" style="background-color:{steam_switch_color}">Steam</button>
    </form>
  </body>
</html>"""


# Function for creating HTML response
def response_complete_HTML():
    # Return HTML
    return f"""HTTP/1.1 200 OK
Content-type:text/html

<html>
  <head>
    <title>Silvia Pico</title>
  </head>
  <body>
    <h1>Setup Completed</h1>
  </body>
</html>"""