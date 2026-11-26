import requests
class ApiClient:
    def __init__(self,cfg,token=None):self.cfg=cfg;self.token=token
    def request(self,method,path,params=None,json_body=None,auth=True):
        headers={"Accept":"application/json"}
        if auth and self.token:headers["Authorization"]=f"Bearer {self.token}"
        url=f"{self.cfg.api_base_url}{path}"
        try:
            return requests.request(method,url,headers=headers,params=params,json=json_body,timeout=self.cfg.request_timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"Could not reach JurisMind API at {self.cfg.api_base_url}: {e}") from e
