import requests, time, json, conf, math, statistics
from boltiot import Sms, Email, Bolt
from threading import Thread, Lock

mybolt = Bolt(conf.api_key, conf.device_id)
mailer = Email(conf.mailgun_api_key, conf.sandbox_url, conf.sender_email, conf.recipient_email)
sms = Sms(conf.SSID, conf.AUTH_TOKEN, conf.TO_NUMBER, conf.FROM_NUMBER) 
history_data=[]

class globalVars():
	pass

G = globalVars()
G.value = 2
G.lock = Lock()
G.kill = False
trigger = 200

def compute_bounds(history_data,frame_size,factor):  
	if len(history_data)<frame_size :         
		return None
		
	if len(history_data)>frame_size :         
		del history_data[0:len(history_data)-frame_size]

	Mn=statistics.mean(history_data)    
	 
	Variance=0     

	for data in history_data :         
		Variance += math.pow((data-Mn),2)     

	Zn = factor * math.sqrt(Variance / frame_size)     
	High_bound = history_data[frame_size-1]+Zn     
	Low_Bound = history_data[frame_size-1]-Zn     
	return [High_bound,Low_Bound] 


def send_telegram_message(message):
	url = "https://api.telegram.org/" + conf.telegram_bot_id + "/sendMessage"
	data = {"chat_id": conf.telegram_chat_id,"text": message}
	try:         
		response = requests.request("GET",url,params=data)
		print("This is the Telegram response")
		print(response.text) 
		telegram_data = json.loads(response.text)
		return telegram_data["ok"]
	except Exception as e:
		print("An error occurred in sending the alert message via Telegram")
		print(e)
		return False

def auto():
	while True:
		mybolt.digitalWrite(3,'LOW')
		

		if G.kill:
			G.kill = False
			return

		if G.value == 1:
			with G.lock:
				r2=mybolt.digitalWrite(4,"HIGH")
				print(r2 + " Bulb is on")				

		elif G.value == 2:
			with G.lock:
				r1 = mybolt.analogRead('A0')
				data = json.loads(r1)				
				#print (data['value'])
				try:
					sensor_value = int(data['value'])
					print ("The amount of light is ",sensor_value)
					if sensor_value < trigger:
						#response = mailer.send_email("Alert", "The Room lighting is " +str(sensor_value)+". Switching on light")
						r2=mybolt.digitalWrite(4,"HIGH")
						print(r2 + " Bulb is on")
					else:
						r2=mybolt.digitalWrite(4,"LOW")
						print(r2 +" Bulb is off")
				except Exception as e:
					print ("Error",e)

		elif G.value == 3:
			with G.lock:
				r2=mybolt.digitalWrite(4,"LOW")
				print(r2 + " Bulb is off")

		elif G.value == 4:
			with G.lock:
				r3 = mybolt.digitalRead('2')
				data = json.loads(r3)
				presence = int(data['value'])
				

				r1 = mybolt.analogRead('A0')
				data = json.loads(r1)
				sensor_value = int(data['value'])
				print(str(sensor_value) + " sensor value " + str(presence) + " presence")

				bound = compute_bounds(history_data,conf.FRAME_SIZE,conf.MUL_FACTOR)

				if not bound:         
					required_data_count=conf.FRAME_SIZE-len(history_data)         
					print("Not enough data to compute Z-score. Need ",required_data_count," more data points")
					history_data.append(int(data['value']))
					continue
	

				if (presence == 1 or sensor_value > bound[0] or sensor_value < bound[1]):
					print('Intruder Alert')
					mybolt.digitalWrite(3,'HIGH')
					
					mybolt.digitalWrite(4,'HIGH')

					
					#response = sms.send_sms("Alert! Motion Sensor has been triggered, there may be unauthorized personnel at your home")             
					#print("This is the response ",response)

					#response = mailer.send_email("Intruder Alert", "Motion Sensor has been triggered, there may be unauthorized personnel at your home.")
					#print(response)

					#message = "Alert! Motion Sensor has been triggered, there may be unauthorized personnel at your home."
					#telegram_status = send_telegram_message(message)
					#print("This is the Telegram status:", telegram_status) 
					
					
					time.sleep(1)

				elif presence == 0:
					print('All Normal')
					mybolt.digitalWrite(3,'LOW')
					mybolt.digitalWrite(4,'LOW')

				history_data.append(sensor_value);
		
		
		time.sleep(1)

t1 = Thread(target=auto,)
t1.start()

def askinput():
	
	choice = int(input("1:Bulb On\n2:Bulb Auto mode\n3:Bulb off\n4:Sentry\n5:Exit\n"))
	if (choice > 0 and choice < 5) :
		with G.lock:
			G.value = choice

	else:
		G.kill = True
		return 0
	
	return 1


while askinput():
	pass
