from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

class URLShortenerUser(FastHttpUser):
    wait_time = between(0.001, 0.005)

    @task
    def redirect(self):
        self.client.get("/4C92", allow_redirects=False)

    # def on_start(self):
    #     # Test boshlanganda URL qisqartiradi
    #     res = self.client.post("/api/v1/shorten", json={
    #         "long_url": "https://uzinfocom.uz/test-load"
    #     })
    #     data = res.json()
    #     self.short_code = data.get("short_code", "4C92")

    # @task(10)
    # def redirect(self):
    #     # Eng ko'p bajariladigan vazifa — redirect
    #     self.client.get(f"/{self.short_code}", allow_redirects=False)

    # @task(2)
    # def get_stats(self):
    #     self.client.get(f"/api/v1/stats/{self.short_code}")

    # @task(1)
    # def shorten(self):
    #     self.client.post("/api/v1/shorten", json={
    #         "long_url": "https://uzinfocom.uz/test-load"
    #     })
