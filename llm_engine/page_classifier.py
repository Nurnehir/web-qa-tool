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
    Öncelik sırası: URL → şifre formu → ödeme → listeleme → ürün detay → genel form → generic
    """

    def classify(self, html: str, url: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        url_lower = url.lower()
        text_lower = soup.get_text().lower()

        # ── 1. URL tabanlı (en güvenilir sinyal) ───────────────────────────────
        if any(k in url_lower for k in ["login", "signin", "giris", "oturum"]):
            return "login"
        if any(k in url_lower for k in ["register", "signup", "kayit", "uyelik"]):
            return "register"
        if any(k in url_lower for k in ["checkout", "payment", "odeme", "sepet", "cart"]):
            return "payment"
        if any(k in url_lower for k in ["admin", "dashboard", "panel", "yonetim"]):
            return "admin"
        if any(k in url_lower for k in ["contact", "iletisim"]):
            return "contact_form"
        if any(k in url_lower for k in ["search", "ara", "arama", "?q=", "?s=", "?query="]):
            return "search"
        if any(k in url_lower for k in
               ["category", "catalogue", "catalog", "kategori",
                "listing", "collection", "shop", "store", "products"]):
            return "listing"

        # ── 2. Şifre formu → login / register ──────────────────────────────────
        forms = soup.find_all("form")
        input_types = [i.get("type", "").lower() for form in forms
                       for i in form.find_all("input")]
        input_names = [i.get("name", "").lower() for form in forms
                       for i in form.find_all("input")]

        if "password" in input_types:
            if any(k in input_names for k in ["confirm", "re_password", "password2", "yeni"]):
                return "register"
            return "login"

        # ── 3. Ödeme formu ──────────────────────────────────────────────────────
        if any(k in input_names for k in ["card", "cvv", "expiry", "cardnumber"]):
            return "payment"

        # ── 4. Listeleme sayfası — çok sayıda tekrarlayan ürün/madde bloğu ─────
        # Birden fazla article, li.product, div.item vb. varsa listing
        articles = soup.find_all("article")
        product_items = soup.find_all(
            lambda tag: tag.name in ("li", "div", "article") and
            any(c in " ".join(tag.get("class", [])).lower()
                for c in ["product", "item", "card", "book", "result", "listing"])
        )
        # 3'ten fazla tekrarlayan blok → listeleme sayfası
        if len(articles) >= 3 or len(product_items) >= 3:
            return "listing"

        # ── 5. Ürün detay sayfası — tek ürün + fiyat sinyali ───────────────────
        price_signals = ["₺", "$", "€", "fiyat", "price", "add to cart",
                         "sepete ekle", "buy now", "satın al", "in stock"]
        if any(p in text_lower for p in price_signals):
            # Tek bir ürün mi yoksa liste mi? h1 varsa ve az article varsa detay
            h1_count = len(soup.find_all("h1"))
            if h1_count >= 1 and len(articles) < 3:
                return "product_detail"

        # ── 6. Arama formu içeren sayfalar (header search kutusu değil, ana form) ─
        # Formlarda text/search input varsa ve sayfa tek bir büyük form içeriyorsa
        main_forms = [f for f in forms if len(f.find_all("input")) >= 2]
        if main_forms:
            return "contact_form"

        # ── 7. Varsayılan ──────────────────────────────────────────────────────
        return "generic"
