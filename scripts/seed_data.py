"""Seed the database with realistic demo data for live Phase 7 verification.

Usage (inside the backend container or locally with the right env vars):
    python -m scripts.seed_data
"""
import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.db.session import AsyncSessionLocal
from app.models.booking import Guest, Reservation
from app.models.hotel import Amenity, Branch, Floor, Hotel, Room, RoomType
from app.models.payment import Payment
from app.models.restaurant import FoodCategory, MenuItem, OrderItem, RestaurantOrder, RestaurantTable
from app.models.review import Review
from app.models.staff import Department, Employee

RNG = random.Random(42)

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
               "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"]
ROOM_TYPES = [("STANDARD", Decimal("89.00"), 2), ("DELUXE", Decimal("139.00"), 3),
              ("SUITE", Decimal("219.00"), 4), ("PRESIDENTIAL", Decimal("449.00"), 6)]
AMENITIES = ["WiFi", "Air Conditioning", "Mini Bar", "Ocean View", "Balcony", "Room Service", "Safe", "Bathtub"]
DEPARTMENTS = ["HOUSEKEEPING", "RECEPTION", "KITCHEN", "MANAGEMENT", "SECURITY"]
MENU = [
    ("Breakfast", [("Pancakes", Decimal("9.50")), ("Omelette", Decimal("8.00")), ("Fresh Juice", Decimal("4.50"))]),
    ("Lunch", [("Club Sandwich", Decimal("12.00")), ("Caesar Salad", Decimal("10.50")), ("Grilled Salmon", Decimal("18.00"))]),
    ("Dinner", [("Ribeye Steak", Decimal("28.00")), ("Pasta Primavera", Decimal("15.00")), ("Seafood Platter", Decimal("32.00"))]),
    ("Beverages", [("House Wine", Decimal("7.00")), ("Craft Beer", Decimal("6.00")), ("Espresso", Decimal("3.50"))]),
]
REVIEW_COMMENTS = {
    5: ["Absolutely wonderful stay, will be back!", "Exceptional service and beautiful rooms.", "Best hotel experience this year."],
    4: ["Very good overall, minor issues with noise.", "Great location and friendly staff.", "Comfortable and clean, would recommend."],
    3: ["Decent stay, nothing special.", "Average experience, room was okay.", "It was fine for the price."],
    2: ["Disappointed with the cleanliness.", "Service was slow and staff seemed uninterested.", "Room was smaller than expected."],
    1: ["Would not stay here again.", "Terrible experience from check-in to check-out.", "Many issues that were never resolved."],
}


def rand_name() -> tuple[str, str]:
    return RNG.choice(FIRST_NAMES), RNG.choice(LAST_NAMES)


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        amenities = [Amenity(name=n, icon=None) for n in AMENITIES]
        db.add_all(amenities)
        await db.flush()

        hotels_data = [
            ("HotelMind Grand Colombo", 5, "Colombo", "Sri Lanka"),
            ("HotelMind Beach Resort Galle", 4, "Galle", "Sri Lanka"),
        ]

        all_rooms: list[Room] = []
        all_branches: list[Branch] = []
        all_guests: list[Guest] = []
        all_reservations: list[Reservation] = []
        all_orders: list[RestaurantOrder] = []

        for hotel_name, star, city, country in hotels_data:
            hotel = Hotel(
                name=hotel_name, star_rating=star, address=f"{RNG.randint(1, 200)} Main Rd",
                city=city, country=country, phone="+94112345678", email=f"info@{hotel_name.lower().replace(' ', '')}.com",
                is_active=True,
            )
            db.add(hotel)
            await db.flush()

            branch = Branch(hotel_id=hotel.id, name=f"{hotel_name} Main Branch", address=hotel.address,
                             city=city, phone=hotel.phone, is_main_branch=True)
            db.add(branch)
            await db.flush()
            all_branches.append(branch)

            for dept_name in DEPARTMENTS:
                dept = Department(branch_id=branch.id, name=dept_name)
                db.add(dept)
                await db.flush()
                for _ in range(2):
                    fn, ln = rand_name()
                    emp = Employee(
                        department_id=dept.id, first_name=fn, last_name=ln,
                        email=f"{fn.lower()}.{ln.lower()}.{uuid.uuid4().hex[:6]}@hotelmind.com",
                        phone="+94771234567", role=dept_name.title(), hire_date=date(2023, 1, 1), is_active=True,
                    )
                    db.add(emp)

            room_types: list[RoomType] = []
            for rt_name, price, max_occ in ROOM_TYPES:
                rt = RoomType(branch_id=branch.id, name=rt_name, base_price=price, max_occupancy=max_occ,
                               description=f"{rt_name.title()} room")
                rt.amenities = RNG.sample(amenities, k=3)
                db.add(rt)
                await db.flush()
                room_types.append(rt)

            for floor_num in range(1, 4):
                floor = Floor(branch_id=branch.id, floor_number=floor_num, name=f"Floor {floor_num}")
                db.add(floor)
                await db.flush()
                for i in range(1, 6):
                    rt = RNG.choice(room_types)
                    room = Room(floor_id=floor.id, room_type_id=rt.id, room_number=f"{floor_num}0{i}",
                                status="AVAILABLE", is_active=True)
                    db.add(room)
                    all_rooms.append(room)
            await db.flush()

            categories: list[FoodCategory] = []
            for order_idx, (cat_name, items) in enumerate(MENU):
                cat = FoodCategory(branch_id=branch.id, name=cat_name, display_order=order_idx)
                db.add(cat)
                await db.flush()
                for item_name, price in items:
                    db.add(MenuItem(category_id=cat.id, name=item_name, price=price, is_available=True))
                categories.append(cat)

            for i in range(1, 9):
                db.add(RestaurantTable(branch_id=branch.id, table_number=str(i), capacity=RNG.choice([2, 4, 6]),
                                        status="AVAILABLE"))
            await db.flush()

        for _ in range(40):
            fn, ln = rand_name()
            guest = Guest(
                first_name=fn, last_name=ln, email=f"{fn.lower()}.{ln.lower()}.{uuid.uuid4().hex[:8]}@example.com",
                phone=f"+9477{RNG.randint(1000000, 9999999)}", id_type=RNG.choice(["PASSPORT", "NIC"]),
                id_number=uuid.uuid4().hex[:10].upper(), nationality=RNG.choice(["Sri Lanka", "UK", "USA", "Germany", "India"]),
            )
            db.add(guest)
            all_guests.append(guest)
        await db.flush()

        today = date.today()
        statuses = ["CONFIRMED", "CHECKED_IN", "CHECKED_OUT", "PENDING", "CANCELLED"]
        for room in RNG.sample(all_rooms, k=min(35, len(all_rooms))):
            guest = RNG.choice(all_guests)
            check_in = today + timedelta(days=RNG.randint(-20, 15))
            check_out = check_in + timedelta(days=RNG.randint(1, 6))
            nights = (check_out - check_in).days
            rt_price = Decimal("120.00")
            total = rt_price * nights
            res_status = RNG.choice(statuses)
            res = Reservation(
                room_id=room.id, guest_id=guest.id, check_in_date=check_in, check_out_date=check_out,
                status=res_status, adults=RNG.randint(1, 2), children=RNG.randint(0, 2),
                total_amount=total, paid_amount=total if res_status == "CHECKED_OUT" else Decimal("0.00"),
                special_requests=None,
                cancelled_at=datetime.now(timezone.utc) if res_status == "CANCELLED" else None,
                cancellation_reason="Guest requested cancellation" if res_status == "CANCELLED" else None,
            )
            db.add(res)
            all_reservations.append(res)
        await db.flush()

        for res in all_reservations:
            if res.status in ("CHECKED_OUT", "CHECKED_IN"):
                db.add(Payment(reservation_id=res.id, order_id=None, amount=res.total_amount,
                                method=RNG.choice(["CARD", "CASH", "ONLINE"]), status="COMPLETED"))

        result_tables = await db.execute(RestaurantTable.__table__.select())
        table_rows = result_tables.fetchall()
        result_items = await db.execute(MenuItem.__table__.select())
        item_rows = result_items.fetchall()

        for _ in range(25):
            table_row = RNG.choice(table_rows)
            branch_id = table_row.branch_id
            branch_items = [r for r in item_rows]
            order_status = RNG.choice(["OPEN", "CLOSED", "CLOSED", "CANCELLED"])
            opened_at = datetime.now(timezone.utc) - timedelta(hours=RNG.randint(1, 72))
            order = RestaurantOrder(
                branch_id=branch_id, table_id=table_row.id, status=order_status, opened_at=opened_at,
                closed_at=opened_at + timedelta(hours=1) if order_status != "OPEN" else None,
                total_amount=Decimal("0.00"),
            )
            db.add(order)
            await db.flush()
            total = Decimal("0.00")
            for _ in range(RNG.randint(1, 4)):
                item = RNG.choice(branch_items)
                qty = RNG.randint(1, 3)
                subtotal = item.price * qty
                total += subtotal
                db.add(OrderItem(order_id=order.id, menu_item_id=item.id, quantity=qty,
                                  unit_price=item.price, subtotal=subtotal))
            order.total_amount = total
            all_orders.append(order)
            if order_status == "CLOSED":
                db.add(Payment(reservation_id=None, order_id=order.id, amount=total,
                                method=RNG.choice(["CARD", "CASH"]), status="COMPLETED"))

        checked_out = [r for r in all_reservations if r.status == "CHECKED_OUT"]
        for res in checked_out[:20]:
            rating = RNG.choices([5, 4, 3, 2, 1], weights=[35, 30, 20, 10, 5])[0]
            comment = RNG.choice(REVIEW_COMMENTS[rating])
            sentiment = "POSITIVE" if rating >= 4 else ("NEUTRAL" if rating == 3 else "NEGATIVE")
            score = {"POSITIVE": 0.8, "NEUTRAL": 0.5, "NEGATIVE": 0.2}[sentiment]
            db.add(Review(reservation_id=res.id, guest_id=res.guest_id, rating=rating, comment=comment,
                           sentiment=sentiment, sentiment_score=score + RNG.uniform(-0.1, 0.1)))

        await db.commit()

        print(f"Seeded: {len(hotels_data)} hotels, {len(all_branches)} branches, {len(all_rooms)} rooms, "
              f"{len(all_guests)} guests, {len(all_reservations)} reservations, {len(all_orders)} restaurant orders, "
              f"{len(checked_out[:20])} reviews")


if __name__ == "__main__":
    asyncio.run(seed())
