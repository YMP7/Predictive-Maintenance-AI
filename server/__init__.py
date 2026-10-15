import ssl

try:
    ssl.create_default_context()
except Exception:
    try:
        import certifi
        _orig_load = ssl.SSLContext.load_default_certs

        def _safe_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
            try:
                _orig_load(self, purpose)
            except Exception:
                self.load_verify_locations(cafile=certifi.where())

        ssl.SSLContext.load_default_certs = _safe_load_default_certs
    except Exception:
        pass
