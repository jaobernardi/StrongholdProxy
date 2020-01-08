import socket
from urllib.parse import urlparse
import threading
from random import choice
from string import ascii_letters
from json import load, dumps

clients = {}

#Config management
class Config:
	def check_user(user, password):
		# Open file
		with open('config.json', 'r') as f:
			# Parse file
			parsed = load(f)
			# Return Value 
			return ([user, password]) in parsed['users']
	def CaptivePortalStatus():
		# Open file
		with open('config.json', 'r') as f:
			# Parse file
			parsed = load(f)
			# Return Value 
			return parsed['captiveportal']
#Client management
class Client(object):
	def __init__(self, address):
		# Defines the object's properties
		self.ip = address[0]
		if self.ip in clients:
			self.allowed = clients[self.ip]
		elif not Config.CaptivePortalStatus():
			self.allowed = True
			clients[self.ip] = True
		else:
			self.allowed = False
	def allow(self):
		# Set the global and object vars
		self.allowed = True
		clients[self.ip] = True
	def deny(self):
		# Set the global and object vars
		self.allowed = False
		clients[self.ip] = False
		
#The server it self
class ProxyServer:
	def __init__(self, host, port):
		# Define host and port for the server
		self.host, self.port = host, port
		# Define server socket
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.threads = []
	def start(self):
		# Bind the server to the Host and Port
		self.socket.bind((self.host, self.port))
		self.socket.listen(0)
		# Start the Listener
		self._listener()
	def _listener(self):
		# Listening loop
		while True:
			# Accept new connections
			client, address = self.socket.accept()
			# Setup the client connection thread
			client_thread = threading.Thread(target=self._connection_hub, args=(client, address))
			self.threads.append(client_thread)
			# Start the thread
			client_thread.start()
	def _request_parser(self, request):
		try:
			# Split the request's head in chunks 'lines'
			request = request.split("\r\n")
			# Strip the address from the first chunk
			address = request[0].split(" ")[1]
			if "http" in address:
				# Use the urllib urlparsing methods that are more efficient than anything i could come off now
				address = [urlparse(address).hostname, 80]
			else:
				# Get the address since it is not an url
				address = address.split(":")
			# Return the results
			print("out", address[0])
			return {
				"port": int(address[1]),
				"hostname": address[0],
				"method": request[0].split(" ")[0]
			}
		except Exception as e:
			print(f"\n---- Error Dump ----\nData: {request}\nError{e}\n")
	def _connection_hub(self, client, address):
		# Create an client object
		client_obj = Client(address)
		# Recieve the data from the client to analyze and then redirect to the right handler
		data = client.recv(1024)
		# Parse and understand the data
		info = self._request_parser(data.decode())
		# Https detection
		if info['method'] == "CONNECT":
			https = True
		else:
			https = False
		# Internal Dashboard Handling
		if info['hostname'] == "stronghold.firewall":
			print(address[0], info['hostname'], "-> Internal Server Connection")
			page = data.decode().split("\r\n")[0].split(" ")[1].split("stronghold.firewall/")[1]
			if page == "Capitive":
				client.send(b'HTTP/1.1 200 OK\nConnection: Close\nServer: Stronghold Proxy\n\n<html><head><title>Captive Portal</title></head><body><h1>Captive Portal</h1><form action="/Captive_Login" method="post">User:<br><input type="text" name="user" value=""><br>Password:<br><input type="password" name="pass" value=""><br><br><input type="submit" value="Sign In"></form> </body></html>')
			elif page == "Captive_Login":
				if info['method'] == "POST":
					infod = data.decode().split("\r\n\r\n")[1]
					user = infod.split("&")[0].split("=")[1]
					passw = infod.split("&")[1].split("=")[1]
					if Config.check_user(user, passw):
						client.send(b'HTTP/1.1 200 OK\nConnection: Close\nServer: Stronghold Proxy\n\n<html><head><title>Captive Portal</title></head><body><h1>Captive Portal</h1><p>Allowed.</p></body></html>')
						client_obj.allow()
						exit()
				client.send(b"HTTP/1.1 302 Network Authentication Required\nConnection: Close\nLocation: http://stronghold.firewall/Capitive\nContent-Type: text/html\nServer: Stronghold Proxy\n\n")
			exit()
		# Captive Portal Handle
		if not client_obj.allowed:
			if https:
				client.send(b"HTTP/1.1 511 Network Authentication Required\nConnection: Close\nServer: Stronghold Proxy\n\n")
				print(address[0], info['hostname'], "-> Closed: Not Authenticated")
			else:
				print(address[0], info['hostname'], "-> Internal Server Redirection -> Captive Portal")
				client.send(b"HTTP/1.1 302 Network Authentication Required\nConnection: Close\nLocation: http://stronghold.firewall/Capitive\nContent-Type: text/html\nServer: Stronghold Proxy\n\n")
			exit()
		print(address[0], info['hostname'])
		# Define a socket for the destination
		dest_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Connect to the destination		
		try:
			dest_sock.connect((info['hostname'], info['port']))
		except:
			if https:
				client.send(b"HTTP/1.1 404 Connection failed\nProxy-Agent: Stronghold Proxy\n\n")
			exit()
		# HTTPS handling
		if https:
			# Warn the client that the connection will be switched to the tunnel
			client.send(b"HTTP/1.1 200 Connection established\nProxy-Agent: Stronghold Proxy\n\n")		
		else:
			dest_sock.send(data)
		# Server side of the connection
		def server_side(dest, client):
			try:
				# Server side loop
				while True:
					# Recive data from the server
					dest_recv = dest.recv(400024)
					if len(dest_recv) == 0:
						break
					# Send the data to the client
					client.send(dest_recv)
			except:
				pass
		# Start the server-side loop		
		threading.Thread(target=server_side, args=(dest_sock, client)).start()
		# Start of the client-side loop
		try:
			while True:		
				# Recieve data from the client
				client_recv = client.recv(400024)
				if len(client_recv) == 0:
					break
				dest_sock.send(client_recv)
		except:
			pass
try:
	ProxyServer("", 2012).start()
except KeyboardInterrupt:
	exit()