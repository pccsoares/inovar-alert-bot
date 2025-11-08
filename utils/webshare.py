import requests
import random
import threading
import os

class Webshare:
    def __init__(self, api_key=None):
        """
        Initialize Webshare proxy manager.

        Args:
            api_key: Webshare API key. If not provided, reads from WEBSHARE_API_KEY env variable.
        """
        self.api_key = api_key or os.getenv('WEBSHARE_API_KEY')
        if not self.api_key:
            raise ValueError("Webshare API key required. Set WEBSHARE_API_KEY environment variable or pass api_key parameter.")

        self.proxy_list_url = f"https://proxy.webshare.io/api/v2/proxy/list/download/{self.api_key}/-/any/username/direct/-/"
        self.proxies = []
        self.proxies_loaded = False
        self.proxy_load_lock = threading.Lock()
        self.current_proxy = None
    
    def ensure_proxies_loaded(self):
        if self.proxies_loaded:
            return

        with self.proxy_load_lock:
            if self.proxies_loaded:  # Double-check after entering lock
                return

            response = requests.get(self.proxy_list_url)
            response.raise_for_status()
            
            for line in response.text.strip().split('\n'):
                parts = line.strip().split(':')
                if len(parts) == 4:
                    self.proxies.append({
                        'host': parts[0],
                        'port': parts[1],
                        'username': parts[2],
                        'password': parts[3]
                    })
            
            if not self.proxies:
                raise Exception("Failed to load proxies from Webshare.")
            
            print(f"\nLoaded {len(self.proxies)} proxies from Webshare.")
            self.proxies_loaded = True
    
    def get_random_proxy(self):
        self.ensure_proxies_loaded()
        return random.choice(self.proxies)
    
    def get_proxy_dict(self):
        """Returns proxy configuration in requests format"""
        proxy = self.get_random_proxy()
        self.current_proxy = proxy
        
        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def switch_proxy(self):
        """Switch to a new random proxy"""
        self.current_proxy = self.get_random_proxy()
        print(f"Switched to proxy: {self.current_proxy['host']}:{self.current_proxy['port']}")
        return self.get_proxy_dict()