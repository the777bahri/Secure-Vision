import socket
import requests
from urllib.parse import urlparse

class IPGeoLocator:
    def __init__(self, target="0"):
        self.target = target

    def extract_ip(self):
        if self.target == "0":
            # Use current machine's public IP
            response = requests.get('https://api.ipify.org?format=json')
            return response.json().get('ip')

        # If it's a URL, extract the hostname
        if self.target.startswith(("http://", "https://")):
            parsed = urlparse(self.target)
            host = parsed.hostname
        else:
            raise ValueError("Target must start with 'http://' or be '0'")

        # If host is an IP, return it
        try:
            socket.inet_aton(host)
            return host
        except socket.error:
            # Resolve domain name to IP
            return socket.gethostbyname(host)

    def get_location(self, ip):
        response = requests.get(f'https://ipinfo.io/{ip}/json')
        data = response.json()
        return data.get('loc')  # "lat,long"

    def get_map_info(self):
        ip = self.extract_ip()
        location = self.get_location(ip)
        return {
            'ip': ip,
            'coordinates': location,
            'map_url': f"https://www.google.com/maps?q={location}" if location else None
        }

if __name__ == "__main__":
    locator = IPGeoLocator("0")  # Use "0" for current machine, or a URL
    # locator = IPGeoLocator("https://www.youtube.com/watch?v=5uZa3-RMFos")
    info = locator.get_map_info()
    print(info)

