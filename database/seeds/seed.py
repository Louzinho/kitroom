"""Demo data. Orders go through the real checkout so both databases stay consistent."""
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import mongo, query_one, execute
from app.models import activity, cart, notification, review
from app.models import category as categories
from app.models import product as products
from app.models import user as users
from app.services import orders

PASSWORD = "KitRoom2026"
PEOPLE = [("admin@kitroom.test", "Louis Durand", "admin"),
          ("mali@kitroom.test", "Mali Srisuk", "customer"),
          ("arthit@kitroom.test", "Arthit Chaiyo", "customer"),
          ("camille@kitroom.test", "Camille Roux", "customer")]
CATEGORIES = [("Premier League", "English top-flight shirts"),
              ("Serie A", "The golden age of Calcio"),
              ("La Liga", "Spanish classics"),
              ("Bundesliga", "German classics"),
              ("Ligue 1", "French classics"),
              ("Internationals", "National team shirts")]
# (category index, title, club, season, price, stock, image, description)
CATALOGUE = [
    (4, "Olympique Lyon home", "Olympique Lyonnais", "2001-02", 3200, 6, "kit-05", "Title-winning era home shirt with the diagonal red band."),
    (4, "Marseille home", "Olympique de Marseille", "1992-93", 5400, 2, "kit-09", "The European Cup season. Rare in this condition."),
    (4, "Paris home", "Paris Saint-Germain", "1996-97", 3900, 5, "kit-17", "Navy with a bold white band across the chest."),
    (1, "Inter home", "Inter Milan", "1997-98", 4700, 4, "kit-02", "Black and blue stripes from the UEFA Cup winning side."),
    (1, "Milan home", "AC Milan", "1988-89", 5200, 3, "kit-03", "Red and black stripes, long sleeves, heavy cotton feel."),
    (1, "Juventus home", "Juventus", "1995-96", 4600, 5, "kit-11", "Black and white stripes from the Champions League year."),
    (1, "Fiorentina away", "Fiorentina", "1998-99", 3500, 1, "kit-10", "White with a purple chest band. One left."),
    (0, "Manchester City home", "Manchester City", "1999-00", 2600, 9, "kit-06", "Sky blue with white trim, promotion season."),
    (0, "Liverpool home", "Liverpool", "1989-90", 4900, 4, "kit-07", "All red, last league title shirt of its era."),
    (0, "Chelsea home", "Chelsea", "1997-98", 3100, 7, "kit-12", "Royal blue, Cup Winners' Cup season."),
    (0, "Aston Villa home", "Aston Villa", "1993-94", 2900, 8, "kit-19", "Claret and blue halves from a League Cup win."),
    (2, "Barcelona home", "FC Barcelona", "1998-99", 4500, 6, "kit-08", "Centenary era halves in blue and garnet."),
    (2, "Real Madrid home", "Real Madrid", "2001-02", 4800, 4, "kit-09", "Centenary season, white with navy trim."),
    (2, "Deportivo home", "Deportivo La Coruna", "1999-00", 3000, 5, "kit-01", "Blue and white stripes from the title-winning side."),
    (3, "Dortmund home", "Borussia Dortmund", "1996-97", 4100, 5, "kit-15", "Yellow and black, the Champions League shirt."),
    (3, "Hamburg home", "Hamburger SV", "1982-83", 3800, 2, "kit-16", "White and red stripes from the European Cup year."),
    (5, "France home", "France", "1998", 6200, 3, "kit-18", "Navy with a red collar. World Cup winners."),
    (5, "Brazil home", "Brazil", "1994", 5600, 4, "kit-13", "Canary yellow with green trim, Pasadena summer."),
    (5, "Netherlands home", "Netherlands", "1988", 6800, 2, "kit-14", "Orange with the famous white chevrons."),
    (5, "Ireland home", "Republic of Ireland", "1990", 3300, 6, "kit-04", "Green hoops from Italia 90."),
]
REVIEWS = [(0, 1, 5, "Arrived folded in tissue. The band is still bright after all these years.", "true"),
           (1, 3, 5, "Best shirt in my collection, by a distance.", "true"),
           (3, 2, 4, "Lovely stripes, a little long in the body.", "large"),
           (3, 1, 5, "Exactly as described.", None),
           (11, 2, 4, "Fits small, order one size up.", "small"),
           (18, 3, 5, "That chevron pattern never gets old.", "true"),
           (16, 1, 5, "Gift for my dad. He would not take it off.", None)]


def seed():
    app = create_app()
    with app.app_context():
        if query_one("SELECT COUNT(*) AS n FROM users")["n"]:
            print("already seeded; run 'python manage.py reset' first")
            return
        hashed = generate_password_hash(PASSWORD)
        uids = [users.create(e, hashed, n, r) for e, n, r in PEOPLE]
        cids = [categories.create(n, d) for n, d in CATEGORIES]
        pids = []
        for c, title, club, season, price, stock, image, text in CATALOGUE:
            pids.append(products.create({
                "category_id": cids[c], "title": title, "club": club, "season": season,
                "price": price, "stock_quantity": stock, "description": text,
                "image_path": f"products/{image}.png"}))

        def buy(uid, indexes, address):
            for i in indexes:
                p = products.get(pids[i])
                cart.add_item(uid, p["product_id"], 1, float(p["price"]), p["title"])
            return orders.place_order(uid, address)["order_id"]

        first = buy(uids[1], [0, 3], "Soi Lat Phrao 71, Bangkok 10230")
        second = buy(uids[1], [16], "Soi Lat Phrao 71, Bangkok 10230")
        third = buy(uids[2], [11, 14], "Rama IV Road, Bangkok 10500")
        fourth = buy(uids[3], [1], "12 rue Paradis, 13001 Marseille")
        orders.change_status(first, "shipped")
        orders.change_status(first, "delivered")
        orders.change_status(second, "shipped")
        orders.cancel_order(fourth)
        buy(uids[3], [18], "12 rue Paradis, 13001 Marseille")

        for index, who, rating, comment, fit in REVIEWS:
            p = products.get(pids[index])
            doc = {"productId": pids[index], "userId": uids[who], "rating": rating,
                   "comment": comment, "userName": PEOPLE[who][1], "productTitle": p["title"],
                   "verifiedPurchase": False}
            if fit:
                doc["sizeFeedback"] = fit
            review.create(doc)
        execute("""UPDATE products SET created_at = created_at - INTERVAL product_id DAY""")

        cart.add_item(uids[1], pids[5], 1, 4600.0, "Juventus home")
        cart.add_item(uids[1], pids[8], 2, 4900.0, "Liverpool home")
        cart.add_item(uids[2], pids[17], 1, 5600.0, "Brazil home")
        for uid in uids:
            notification.create(uid, "New arrivals from Serie A",
                                "Four shirts from the nineties just came in.", "broadcast")
        activity.log(uids[1], "user_login")
        activity.log(uids[2], "product_viewed", {"productId": pids[11], "title": "Barcelona home"})
    print(f"seeded {len(PEOPLE)} users, {len(CATALOGUE)} shirts. Password for all: {PASSWORD}")
