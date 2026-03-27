from bs4 import BeautifulSoup
import re

PAGE_TYPES = {
    "login": "Giriş / Login sayfası",
    "register": "Kayıt / Üyelik sayfası",
    "payment": "Ödeme sayfası",
    "contact_form": "İletişim formu",
    "search": "Arama sayfası",
    "product_detail": "Ürün / İçerik detay sayfası",
    "listing": "Listeleme / Katalog sayfası",
    "admin": "Admin / Yönetim paneli",
    "generic": "Genel içerik sayfası",
}


class PageClassifier:
    """
    HTML içeriğini ve URL'yi analiz ederek sayfa tipini belirler.
    Bu bilgi LLM'e gönderilir — daha isabetli senaryo üretimi için.
    """

    def classify(self, html: str, url: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        url_lower = url.lower()
        text_lower = soup.get_text().lower()

        # URL tabanlı ipuçları
        if any(k in url_lower for k in ["login", "signin", "giris", "oturum"]):
            return "login"
        if any(k in url_lower for k in ["register", "signup", "kayit", "uyelik"]):
            return "register"
        if any(k in url_lower for k in ["checkout", "payment", "odeme", "sepet", "cart"]):
            return "payment"
        if any(k in url_lower for k in ["admin", "dashboard", "panel", "yonetim"]):
            return "admin"
        if any(k in url_lower for k in ["search", "ara", "arama"]):
            return "search"
        if any(k in url_lower for k in ["contact", "iletisim"]):
            return "contact_form"

        # Form içeriğine göre
        forms = soup.find_all("form")
        input_types = [i.get("type", "").lower() for form in forms
                       for i in form.find_all("input")]
        input_names = [i.get("name", "").lower() for form in forms
                       for i in form.find_all("input")]

        if "password" in input_types:
            if any(k in input_names for k in ["confirm", "re_password", "yeni"]):
                return "register"
            return "login"

        if any(k in input_names for k in ["card", "cvv", "expiry"]):
            return "payment"

        if forms:
            return "contact_form"

        # İçerik tabanlı
        if soup.find_all("ul", class_=re.compile(r"product|item|listing", re.I)):
            return "listing"

        if any(p in text_lower for p in ["₺", "$", "€", "fiyat", "price", "sepete ekle"]):
            return "product_detail"

        return "generic"
