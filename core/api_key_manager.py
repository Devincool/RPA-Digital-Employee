class APIKeyManager:
    _instance = None
    _api_key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIKeyManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def set_api_key(cls, api_key):
        cls._api_key = api_key

    @classmethod
    def get_api_key(cls):
        if cls._api_key is None:
            raise ValueError("API key has not been set. Please ensure it is set before using.")
        return cls._api_key 