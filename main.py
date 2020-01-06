import socket
from urllib.parse import urlparse
import threading

#Client management
class Client:
	pass

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
		return {
			"port": int(address[1]),
			"hostname": address[0],
			"method": request[0].split(" ")[0]
		}
	def _connection_hub(self, client, address):
		# Recieve the data from the client to analyze and then redirect to the right handler
		data = client.recv(1024)
		# Parse and understand the data
		info = self._request_parser(data.decode())
		# Logging
		print(address[0], info['hostname'])
		# Define a socket for the destination
		dest_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Connect to the destination
		try:
			dest_sock.connect((info['hostname'], info['port']))
		except:
			exit()
		# HTTPS handling
		if info['method'] != "CONNECT":
			dest_sock.send(data)
		else:
			client.send(b"HTTP/1.1 200 Connection established\nProxy-Agent: Stronghold Proxy\n\n")		
		# Server side of the connection
		def server_side(dest, client):
			try:
				# Server side loop
				while True:
					# Recive data from the server
					dest_recv = dest.recv(4024)
					if len(dest_recv) == 0:
						break
					# Send the data to the client
					client.send(dest_recv)
			except:
				pass
		# Start the server-side loop		
		threading.Thread(target=server_side, args=(dest_sock, client)).start()
		# Start the Client side loop
		try:
			while True:		
				# Recieve data from the client
				client_recv = client.recv(4024)
				if len(client_recv) == 0:
					break
				# Send data to server
				dest_sock.send(client_recv)
		except:
			pass
ProxyServer("", 2012).start()