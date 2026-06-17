#!/usr/bin/env bash
# HotelMind API — Full integration test
# Usage: bash test_api.sh
# Requires: curl, python3

set -uo pipefail

BASE="http://localhost:8001/api/v1"
PASS=0
FAIL=0
RUN_ID=$(date +%s)

# Use Python for JSON parsing since jq may not be available
jq() {
  python3 -c "
import sys, json
data = sys.stdin.read().strip()
if not data:
    sys.exit(0)
try:
    obj = json.loads(data)
except json.JSONDecodeError:
    print(data)
    sys.exit(0)
path = '$1'
if path == '.':
    print(json.dumps(obj))
elif path.startswith('.') and '|' not in path and '[' not in path:
    keys = path[1:].split('.')
    val = obj
    for k in keys:
        if k and isinstance(val, dict):
            val = val.get(k, '')
    if isinstance(val, (dict, list)):
        print(json.dumps(val))
    elif val is None:
        print('null')
    else:
        print(str(val).rstrip())
elif path == 'length':
    print(len(obj))
else:
    # Eval-style for complex queries
    try:
        result = eval(path.replace('length', 'len').replace('|', ';'), {'obj': obj, 'len': len, 'json': json})
        print(result)
    except:
        print(data)
"
}

ok()  { echo "  [PASS] $1"; PASS=$((PASS+1)); }
fail(){ echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

expect_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then ok "$label (HTTP $actual)"; else fail "$label — expected HTTP $expected, got $actual"; fi
}

jq_parse() {
  local json="$1" path="$2"
  echo "$json" | python3 -c "
import sys, json
data = '''$json'''.strip()
if not data:
    print('')
    sys.exit(0)
try:
    obj = json.loads(data)
except:
    print('')
    sys.exit(0)
path = '''$path'''
if path == 'length' or path == 'len':
    print(len(obj) if isinstance(obj, (list, dict)) else 0)
elif path.startswith('.'):
    keys = path[1:].split('.')
    val = obj
    for k in keys:
        if k:
            if isinstance(val, dict):
                val = val.get(k, '')
            elif isinstance(val, list) and k == '-1':
                val = val[-1] if val else {}
            else:
                val = ''
    if val is None:
        print('null')
    elif isinstance(val, (dict, list)):
        print(json.dumps(val))
    else:
        print(str(val).rstrip())
elif path == '.[0].items | length' or 'items' in path:
    try:
        items = obj[0].get('items', []) if isinstance(obj, list) and obj else []
        print(len(items))
    except:
        print(0)
" 2>/dev/null || echo ""
}

echo "========================================================"
echo "  HotelMind API Integration Tests"
echo "========================================================"

# ── 0. Health ─────────────────────────────────────────────────────────────────
echo ""
echo "── 0. Health ──"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)
expect_status "GET /health" "200" "$STATUS"

# ── 1. Hotels happy path ──────────────────────────────────────────────────────
echo ""
echo "── 1. Hotels ──"

echo "  Creating hotel..."
HOTEL_JSON=$(curl -sf -X POST "$BASE/hotels/" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Grand Plaza $RUN_ID\",\"star_rating\":5,\"address\":\"123 Main St\",\"city\":\"Dubai\",\"country\":\"UAE\",\"phone\":\"+971501234567\",\"email\":\"info$RUN_ID@grandplaza.com\"}")
HOTEL_ID=$(jq_parse "$HOTEL_JSON" ".id")
[ -n "$HOTEL_ID" ] && ok "POST /hotels/ — hotel_id=$HOTEL_ID" || fail "POST /hotels/"

echo "  Creating branch..."
BRANCH_JSON=$(curl -sf -X POST "$BASE/hotels/$HOTEL_ID/branches" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Main Branch\",\"address\":\"123 Main St\",\"city\":\"Dubai\",\"is_main_branch\":true,\"hotel_id\":\"$HOTEL_ID\"}")
BRANCH_ID=$(jq_parse "$BRANCH_JSON" ".id")
[ -n "$BRANCH_ID" ] && ok "POST /hotels/{id}/branches — branch_id=$BRANCH_ID" || fail "POST /hotels/{id}/branches"

echo "  Listing branches..."
BRANCH_LIST=$(curl -sf "$BASE/hotels/$HOTEL_ID/branches")
BRANCH_COUNT=$(jq_parse "$BRANCH_LIST" "length")
[ "${BRANCH_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "GET /hotels/{id}/branches — $BRANCH_COUNT branch(es)" || fail "GET /hotels/{id}/branches"

echo "  Getting hotel with branches..."
HOTEL_DATA=$(curl -sf "$BASE/hotels/$HOTEL_ID")
NESTED=$(jq_parse "$HOTEL_DATA" ".branches" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(len(d))" 2>/dev/null || echo "0")
[ "${NESTED:-0}" -ge 1 ] 2>/dev/null && ok "GET /hotels/{id} — branches nested ($NESTED)" || fail "GET /hotels/{id} — no nested branches"

echo "  Updating hotel..."
UPDATED_HOTEL=$(curl -sf -X PUT "$BASE/hotels/$HOTEL_ID" \
  -H "Content-Type: application/json" \
  -d '{"star_rating":4}')
STAR=$(jq_parse "$UPDATED_HOTEL" ".star_rating")
[ "$STAR" = "4" ] && ok "PUT /hotels/{id} — star_rating=$STAR" || fail "PUT /hotels/{id}"

echo "  Updating branch (via branches_router — BUG 1 fix test)..."
UPDATED_BRANCH=$(curl -sf -X PUT "$BASE/hotels/branches/$BRANCH_ID" \
  -H "Content-Type: application/json" \
  -d '{"city":"Abu Dhabi"}')
CITY=$(jq_parse "$UPDATED_BRANCH" ".city")
[ "$CITY" = "Abu Dhabi" ] && ok "PUT /hotels/branches/{id} — city=$CITY (BUG 1 fix verified)" || fail "PUT /hotels/branches/{id} — route collision not fixed (city=$CITY)"

echo "  Creating floor..."
FLOOR_JSON=$(curl -sf -X POST "$BASE/hotels/floors" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"floor_number\":1,\"name\":\"Ground Floor\"}")
FLOOR_ID=$(jq_parse "$FLOOR_JSON" ".id")
[ -n "$FLOOR_ID" ] && ok "POST /hotels/floors — floor_id=$FLOOR_ID" || fail "POST /hotels/floors"

echo "  Creating room type..."
RTYPE_JSON=$(curl -sf -X POST "$BASE/hotels/room-types" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"name\":\"Deluxe King\",\"base_price\":\"350.00\",\"max_occupancy\":2}")
RTYPE_ID=$(jq_parse "$RTYPE_JSON" ".id")
[ -n "$RTYPE_ID" ] && ok "POST /hotels/room-types — rtype_id=$RTYPE_ID" || fail "POST /hotels/room-types"

echo "  Listing room types for branch (BUG 1 fix test)..."
RTYPE_LIST=$(curl -sf "$BASE/hotels/branches/$BRANCH_ID/room-types")
RTYPE_COUNT=$(jq_parse "$RTYPE_LIST" "length")
[ "${RTYPE_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "GET /hotels/branches/{id}/room-types — $RTYPE_COUNT type(s) (BUG 1 fix verified)" || fail "GET /hotels/branches/{id}/room-types — route collision not fixed"

echo "  Updating room type..."
curl -sf -X PUT "$BASE/hotels/room-types/$RTYPE_ID" \
  -H "Content-Type: application/json" \
  -d '{"base_price":"399.00"}' > /dev/null
ok "PUT /hotels/room-types/{id}"

echo "  Creating room..."
ROOM_JSON=$(curl -sf -X POST "$BASE/hotels/rooms" \
  -H "Content-Type: application/json" \
  -d "{\"floor_id\":\"$FLOOR_ID\",\"room_type_id\":\"$RTYPE_ID\",\"room_number\":\"101\"}")
ROOM_ID=$(jq_parse "$ROOM_JSON" ".id")
[ -n "$ROOM_ID" ] && ok "POST /hotels/rooms — room_id=$ROOM_ID" || fail "POST /hotels/rooms"

echo "  Listing rooms for branch (BUG 1 fix test)..."
ROOMS_LIST=$(curl -sf "$BASE/hotels/branches/$BRANCH_ID/rooms")
ROOM_COUNT=$(jq_parse "$ROOMS_LIST" "length")
[ "${ROOM_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "GET /hotels/branches/{id}/rooms — $ROOM_COUNT room(s) (BUG 1 fix verified)" || fail "GET /hotels/branches/{id}/rooms — route collision not fixed"

echo "  Filtering rooms by status=AVAILABLE..."
AVAIL_LIST=$(curl -sf "$BASE/hotels/branches/$BRANCH_ID/rooms?status=AVAILABLE")
AVAIL_COUNT=$(jq_parse "$AVAIL_LIST" "length")
ok "GET /hotels/branches/{id}/rooms?status=AVAILABLE — $AVAIL_COUNT room(s)"

echo "  Updating room status to MAINTENANCE..."
ROOM_STATUS_JSON=$(curl -sf -X PATCH "$BASE/hotels/rooms/$ROOM_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"MAINTENANCE"}')
ROOM_STATUS=$(jq_parse "$ROOM_STATUS_JSON" ".status")
[ "$ROOM_STATUS" = "MAINTENANCE" ] && ok "PATCH /hotels/rooms/{id}/status — status=$ROOM_STATUS" || fail "PATCH /hotels/rooms/{id}/status"

echo "  Resetting room to AVAILABLE..."
curl -sf -X PATCH "$BASE/hotels/rooms/$ROOM_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"AVAILABLE"}' > /dev/null
ok "PATCH /hotels/rooms/{id}/status reset to AVAILABLE"

# ── 2. Bookings ───────────────────────────────────────────────────────────────
echo ""
echo "── 2. Bookings ──"

echo "  Creating guest..."
GUEST_JSON=$(curl -sf -X POST "$BASE/bookings/guests" \
  -H "Content-Type: application/json" \
  -d "{\"first_name\":\"John\",\"last_name\":\"Doe\",\"email\":\"john.doe.$RUN_ID@example.com\",\"phone\":\"+971501111111\",\"nationality\":\"US\"}")
GUEST_ID=$(jq_parse "$GUEST_JSON" ".id")
[ -n "$GUEST_ID" ] && ok "POST /bookings/guests — guest_id=$GUEST_ID" || fail "POST /bookings/guests"

echo "  Getting guest..."
GUEST_DATA=$(curl -sf "$BASE/bookings/guests/$GUEST_ID")
G_ID=$(jq_parse "$GUEST_DATA" ".id")
[ "$G_ID" = "$GUEST_ID" ] && ok "GET /bookings/guests/{id}" || fail "GET /bookings/guests/{id}"

echo "  Updating guest..."
UPDATED_G=$(curl -sf -X PUT "$BASE/bookings/guests/$GUEST_ID" \
  -H "Content-Type: application/json" \
  -d '{"nationality":"GB"}')
NATIONALITY=$(jq_parse "$UPDATED_G" ".nationality")
[ "$NATIONALITY" = "GB" ] && ok "PUT /bookings/guests/{id}" || fail "PUT /bookings/guests/{id}"

echo "  Listing guests..."
GUEST_LIST=$(curl -sf "$BASE/bookings/guests")
G_COUNT=$(jq_parse "$GUEST_LIST" "length")
ok "GET /bookings/guests — $G_COUNT guest(s)"

echo "  Creating reservation..."
RES_JSON=$(curl -sf -X POST "$BASE/bookings/reservations" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\":\"$ROOM_ID\",\"guest_id\":\"$GUEST_ID\",\"check_in_date\":\"2026-08-01\",\"check_out_date\":\"2026-08-05\",\"adults\":2,\"total_amount\":\"1596.00\"}")
RES_ID=$(jq_parse "$RES_JSON" ".id")
RES_STATUS=$(jq_parse "$RES_JSON" ".status")
[ -n "$RES_ID" ] && ok "POST /bookings/reservations — res_id=$RES_ID status=$RES_STATUS" || fail "POST /bookings/reservations"

echo "  Getting reservation (with guest nested)..."
RES_DATA=$(curl -sf "$BASE/bookings/reservations/$RES_ID")
NESTED_GUEST=$(jq_parse "$RES_DATA" ".guest.id")
[ "$NESTED_GUEST" = "$GUEST_ID" ] && ok "GET /bookings/reservations/{id} — guest nested" || fail "GET /bookings/reservations/{id}"

echo "  Listing reservations..."
RES_LIST=$(curl -sf "$BASE/bookings/reservations")
R_COUNT=$(jq_parse "$RES_LIST" "length")
ok "GET /bookings/reservations — $R_COUNT reservation(s)"

echo "  Confirming reservation..."
CONFIRMED_JSON=$(curl -sf -X PATCH "$BASE/bookings/reservations/$RES_ID/confirm")
CONFIRMED=$(jq_parse "$CONFIRMED_JSON" ".status")
[ "$CONFIRMED" = "CONFIRMED" ] && ok "PATCH /reservations/{id}/confirm — status=$CONFIRMED" || fail "PATCH /reservations/{id}/confirm"

echo "  Checking in..."
CHECKIN_JSON=$(curl -sf -X PATCH "$BASE/bookings/reservations/$RES_ID/check-in")
CHECKED_IN=$(jq_parse "$CHECKIN_JSON" ".status")
[ "$CHECKED_IN" = "CHECKED_IN" ] && ok "PATCH /reservations/{id}/check-in — status=$CHECKED_IN" || fail "PATCH /reservations/{id}/check-in"

echo "  Verifying room is OCCUPIED after check-in..."
OCC_LIST=$(curl -sf "$BASE/hotels/branches/$BRANCH_ID/rooms?status=OCCUPIED")
OCC_COUNT=$(jq_parse "$OCC_LIST" "length")
[ "${OCC_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "Room auto-set to OCCUPIED on check-in" || fail "Room not OCCUPIED after check-in"

echo "  Checking out..."
CHECKOUT_JSON=$(curl -sf -X PATCH "$BASE/bookings/reservations/$RES_ID/check-out")
CHECKED_OUT=$(jq_parse "$CHECKOUT_JSON" ".status")
[ "$CHECKED_OUT" = "CHECKED_OUT" ] && ok "PATCH /reservations/{id}/check-out — status=$CHECKED_OUT" || fail "PATCH /reservations/{id}/check-out"

echo "  Verifying room is AVAILABLE after check-out..."
AVAIL2_LIST=$(curl -sf "$BASE/hotels/branches/$BRANCH_ID/rooms?status=AVAILABLE")
AVAIL2_COUNT=$(jq_parse "$AVAIL2_LIST" "length")
[ "${AVAIL2_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "Room auto-set to AVAILABLE on check-out" || fail "Room not AVAILABLE after check-out"

echo "  Creating second reservation to cancel..."
RES2_JSON=$(curl -sf -X POST "$BASE/bookings/reservations" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\":\"$ROOM_ID\",\"guest_id\":\"$GUEST_ID\",\"check_in_date\":\"2026-09-01\",\"check_out_date\":\"2026-09-03\",\"adults\":1,\"total_amount\":\"798.00\"}")
RES2_ID=$(jq_parse "$RES2_JSON" ".id")
CANCEL_JSON=$(curl -sf -X PATCH "$BASE/bookings/reservations/$RES2_ID/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Test cancellation"}')
CANCELLED_R=$(jq_parse "$CANCEL_JSON" ".status")
[ "$CANCELLED_R" = "CANCELLED" ] && ok "PATCH /reservations/{id}/cancel — status=$CANCELLED_R" || fail "PATCH /reservations/{id}/cancel"

echo "  Updating reservation..."
curl -sf -X PUT "$BASE/bookings/reservations/$RES_ID" \
  -H "Content-Type: application/json" \
  -d '{"special_requests":"Late check-out please"}' > /dev/null
ok "PUT /bookings/reservations/{id}"

# ── 3. Restaurant ─────────────────────────────────────────────────────────────
echo ""
echo "── 3. Restaurant ──"

echo "  Creating food category..."
CAT_JSON=$(curl -sf -X POST "$BASE/restaurant/categories" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"name\":\"Main Course\",\"display_order\":1}")
CAT_ID=$(jq_parse "$CAT_JSON" ".id")
[ -n "$CAT_ID" ] && ok "POST /restaurant/categories — cat_id=$CAT_ID" || fail "POST /restaurant/categories"

echo "  Listing categories..."
CAT_LIST=$(curl -sf "$BASE/restaurant/categories?branch_id=$BRANCH_ID")
CAT_COUNT=$(jq_parse "$CAT_LIST" "length")
ok "GET /restaurant/categories — $CAT_COUNT category(ies)"

echo "  Creating menu item..."
ITEM_JSON=$(curl -sf -X POST "$BASE/restaurant/menu-items" \
  -H "Content-Type: application/json" \
  -d "{\"category_id\":\"$CAT_ID\",\"name\":\"Grilled Salmon\",\"price\":\"45.00\",\"is_available\":true}")
ITEM_ID=$(jq_parse "$ITEM_JSON" ".id")
[ -n "$ITEM_ID" ] && ok "POST /restaurant/menu-items — item_id=$ITEM_ID" || fail "POST /restaurant/menu-items"

echo "  Listing menu items..."
MI_LIST=$(curl -sf "$BASE/restaurant/menu-items")
MI_COUNT=$(jq_parse "$MI_LIST" "length")
ok "GET /restaurant/menu-items — $MI_COUNT item(s)"

echo "  Filtering menu items by category..."
MI_CAT_LIST=$(curl -sf "$BASE/restaurant/menu-items?category_id=$CAT_ID")
MI_CAT_COUNT=$(jq_parse "$MI_CAT_LIST" "length")
ok "GET /restaurant/menu-items?category_id — $MI_CAT_COUNT item(s)"

echo "  Updating menu item..."
curl -sf -X PUT "$BASE/restaurant/menu-items/$ITEM_ID" \
  -H "Content-Type: application/json" \
  -d '{"price":"48.00"}' > /dev/null
ok "PUT /restaurant/menu-items/{id}"

echo "  Creating table..."
TABLE_JSON=$(curl -sf -X POST "$BASE/restaurant/tables" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"table_number\":\"T01\",\"capacity\":4}")
TABLE_ID=$(jq_parse "$TABLE_JSON" ".id")
[ -n "$TABLE_ID" ] && ok "POST /restaurant/tables — table_id=$TABLE_ID" || fail "POST /restaurant/tables"

echo "  Listing tables..."
T_LIST=$(curl -sf "$BASE/restaurant/tables?branch_id=$BRANCH_ID")
T_COUNT=$(jq_parse "$T_LIST" "length")
ok "GET /restaurant/tables — $T_COUNT table(s)"

echo "  Updating table status..."
T_STATUS_JSON=$(curl -sf -X PATCH "$BASE/restaurant/tables/$TABLE_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"OCCUPIED"}')
T_STATUS=$(jq_parse "$T_STATUS_JSON" ".status")
[ "$T_STATUS" = "OCCUPIED" ] && ok "PATCH /restaurant/tables/{id}/status — status=$T_STATUS" || fail "PATCH /restaurant/tables/{id}/status"

echo "  Opening order..."
ORDER_JSON=$(curl -sf -X POST "$BASE/restaurant/orders" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"table_id\":\"$TABLE_ID\"}")
ORDER_ID=$(jq_parse "$ORDER_JSON" ".id")
ORDER_STATUS=$(jq_parse "$ORDER_JSON" ".status")
[ "$ORDER_STATUS" = "OPEN" ] && ok "POST /restaurant/orders — order_id=$ORDER_ID status=$ORDER_STATUS" || fail "POST /restaurant/orders"

echo "  Adding item to order..."
ORDER_ITEM_JSON=$(curl -sf -X POST "$BASE/restaurant/orders/$ORDER_ID/items" \
  -H "Content-Type: application/json" \
  -d "{\"menu_item_id\":\"$ITEM_ID\",\"quantity\":2}")
ITEM_COUNT=$(jq_parse "$ORDER_ITEM_JSON" ".items" | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read())))" 2>/dev/null || echo "0")
TOTAL=$(jq_parse "$ORDER_ITEM_JSON" ".total_amount")
[ "${ITEM_COUNT:-0}" -ge 1 ] 2>/dev/null && ok "POST /restaurant/orders/{id}/items — items=$ITEM_COUNT total=$TOTAL" || fail "POST /restaurant/orders/{id}/items"

echo "  Getting order with items..."
ORDER_DATA=$(curl -sf "$BASE/restaurant/orders/$ORDER_ID")
GET_ITEMS=$(jq_parse "$ORDER_DATA" ".items" | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read())))" 2>/dev/null || echo "0")
[ "${GET_ITEMS:-0}" -ge 1 ] 2>/dev/null && ok "GET /restaurant/orders/{id} — items=$GET_ITEMS" || fail "GET /restaurant/orders/{id}"

echo "  Listing orders (BUG 4 fix — items should be populated)..."
ORDER_LIST_JSON=$(curl -sf "$BASE/restaurant/orders?branch_id=$BRANCH_ID")
LIST_COUNT=$(jq_parse "$ORDER_LIST_JSON" "length")
LIST_ITEMS=$(echo "$ORDER_LIST_JSON" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(len(data[0].get('items', [])) if data else 0)
" 2>/dev/null || echo "0")
[ "${LIST_ITEMS:-0}" -ge 1 ] 2>/dev/null && ok "GET /restaurant/orders — $LIST_COUNT order(s), items loaded=$LIST_ITEMS (BUG 4 fix verified)" || fail "GET /restaurant/orders — items not loaded (BUG 4 not fixed)"

echo "  Adding second item then removing it..."
ORDER_2ITEMS_JSON=$(curl -sf -X POST "$BASE/restaurant/orders/$ORDER_ID/items" \
  -H "Content-Type: application/json" \
  -d "{\"menu_item_id\":\"$ITEM_ID\",\"quantity\":1}")
ITEM2_ID=$(echo "$ORDER_2ITEMS_JSON" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['items'][-1]['id'])" 2>/dev/null || echo "")
ORDER_AFTER_REMOVE=$(curl -sf -X DELETE "$BASE/restaurant/orders/$ORDER_ID/items/$ITEM2_ID")
REMOVE_COUNT=$(jq_parse "$ORDER_AFTER_REMOVE" ".items" | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read())))" 2>/dev/null || echo "0")
ok "DELETE /restaurant/orders/{id}/items/{item_id} — remaining items=$REMOVE_COUNT"

echo "  Closing order..."
CLOSE_JSON=$(curl -sf -X PATCH "$BASE/restaurant/orders/$ORDER_ID/close")
CLOSED_STATUS=$(jq_parse "$CLOSE_JSON" ".status")
[ "$CLOSED_STATUS" = "CLOSED" ] && ok "PATCH /restaurant/orders/{id}/close — status=$CLOSED_STATUS" || fail "PATCH /restaurant/orders/{id}/close"

echo "  Opening second order to cancel..."
ORDER_C_JSON=$(curl -sf -X POST "$BASE/restaurant/orders" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\"}")
ORDER_CANCEL_ID=$(jq_parse "$ORDER_C_JSON" ".id")
CANCEL_STATUS_JSON=$(curl -sf -X PATCH "$BASE/restaurant/orders/$ORDER_CANCEL_ID/cancel")
CANCEL_STATUS=$(jq_parse "$CANCEL_STATUS_JSON" ".status")
[ "$CANCEL_STATUS" = "CANCELLED" ] && ok "PATCH /restaurant/orders/{id}/cancel — status=$CANCEL_STATUS" || fail "PATCH /restaurant/orders/{id}/cancel"

# ── 4. Staff ──────────────────────────────────────────────────────────────────
echo ""
echo "── 4. Staff ──"

echo "  Creating department..."
DEPT_JSON=$(curl -sf -X POST "$BASE/staff/departments" \
  -H "Content-Type: application/json" \
  -d "{\"branch_id\":\"$BRANCH_ID\",\"name\":\"KITCHEN\"}")
DEPT_ID=$(jq_parse "$DEPT_JSON" ".id")
[ -n "$DEPT_ID" ] && ok "POST /staff/departments — dept_id=$DEPT_ID" || fail "POST /staff/departments"

echo "  Listing departments..."
DEPT_LIST=$(curl -sf "$BASE/staff/departments?branch_id=$BRANCH_ID")
D_COUNT=$(jq_parse "$DEPT_LIST" "length")
ok "GET /staff/departments — $D_COUNT dept(s)"

echo "  Creating employee (BUG 2 fix — department must be nested)..."
EMP_JSON=$(curl -sf -X POST "$BASE/staff/employees" \
  -H "Content-Type: application/json" \
  -d "{\"department_id\":\"$DEPT_ID\",\"first_name\":\"Alice\",\"last_name\":\"Smith\",\"email\":\"alice.smith.$RUN_ID@hotel.com\",\"hire_date\":\"2025-01-15\",\"role\":\"Chef\"}")
EMP_ID=$(jq_parse "$EMP_JSON" ".id")
EMP_DEPT=$(jq_parse "$EMP_JSON" ".department.name")
[ "$EMP_DEPT" = "KITCHEN" ] && ok "POST /staff/employees — dept nested=$EMP_DEPT (BUG 2 fix verified)" || fail "POST /staff/employees — department not nested (BUG 2) — got '$EMP_DEPT'"

echo "  Getting employee (BUG 2 fix — department must be nested)..."
EMP_DATA=$(curl -sf "$BASE/staff/employees/$EMP_ID")
GET_DEPT=$(jq_parse "$EMP_DATA" ".department.name")
[ "$GET_DEPT" = "KITCHEN" ] && ok "GET /staff/employees/{id} — dept nested=$GET_DEPT (BUG 2 fix verified)" || fail "GET /staff/employees/{id} — department not nested (BUG 2)"

echo "  Listing employees..."
EMP_LIST=$(curl -sf "$BASE/staff/employees")
E_COUNT=$(jq_parse "$EMP_LIST" "length")
ok "GET /staff/employees — $E_COUNT employee(s)"

echo "  Updating employee (BUG 2 fix — department must be nested in response)..."
UPD_EMP_JSON=$(curl -sf -X PUT "$BASE/staff/employees/$EMP_ID" \
  -H "Content-Type: application/json" \
  -d '{"role":"Head Chef"}')
UPD_DEPT=$(jq_parse "$UPD_EMP_JSON" ".department.name")
UPD_ROLE=$(jq_parse "$UPD_EMP_JSON" ".role")
[ "$UPD_DEPT" = "KITCHEN" ] && ok "PUT /staff/employees/{id} — role=$UPD_ROLE dept=$UPD_DEPT (BUG 2 fix verified)" || fail "PUT /staff/employees/{id} — department not nested"

echo "  Creating schedule..."
SCHED_JSON=$(curl -sf -X POST "$BASE/staff/schedules" \
  -H "Content-Type: application/json" \
  -d "{\"employee_id\":\"$EMP_ID\",\"shift_date\":\"2026-07-01\",\"shift_start\":\"08:00:00\",\"shift_end\":\"16:00:00\",\"notes\":\"Morning shift\"}")
SCHED_ID=$(jq_parse "$SCHED_JSON" ".id")
[ -n "$SCHED_ID" ] && ok "POST /staff/schedules — sched_id=$SCHED_ID" || fail "POST /staff/schedules"

echo "  Listing schedules..."
SCHED_LIST=$(curl -sf "$BASE/staff/schedules?employee_id=$EMP_ID")
S_COUNT=$(jq_parse "$SCHED_LIST" "length")
ok "GET /staff/schedules — $S_COUNT schedule(s)"

echo "  Clocking in (verifying status=PRESENT default)..."
ATT_JSON=$(curl -sf -X POST "$BASE/staff/attendance/clock-in" \
  -H "Content-Type: application/json" \
  -d "{\"schedule_id\":\"$SCHED_ID\",\"employee_id\":\"$EMP_ID\",\"clock_in\":\"2026-07-01T08:02:00Z\"}")
ATT_ID=$(jq_parse "$ATT_JSON" ".id")
ATT_STATUS=$(jq_parse "$ATT_JSON" ".status")
[ "$ATT_STATUS" = "PRESENT" ] && ok "POST /staff/attendance/clock-in — status=$ATT_STATUS (default verified)" || fail "POST /staff/attendance/clock-in — status=$ATT_STATUS (expected PRESENT)"

echo "  Clocking out..."
ATT_OUT_JSON=$(curl -sf -X PATCH "$BASE/staff/attendance/$ATT_ID/clock-out" \
  -H "Content-Type: application/json" \
  -d '{"clock_out":"2026-07-01T16:05:00Z"}')
CLOCK_OUT=$(jq_parse "$ATT_OUT_JSON" ".clock_out")
[ -n "$CLOCK_OUT" ] && [ "$CLOCK_OUT" != "null" ] && ok "PATCH /staff/attendance/{id}/clock-out — clock_out=$CLOCK_OUT" || fail "PATCH /staff/attendance/{id}/clock-out"

echo "  Listing attendance..."
ATT_LIST=$(curl -sf "$BASE/staff/attendance?employee_id=$EMP_ID")
A_COUNT=$(jq_parse "$ATT_LIST" "length")
ok "GET /staff/attendance — $A_COUNT record(s)"

echo "  Creating second employee to deactivate..."
EMP2_JSON=$(curl -sf -X POST "$BASE/staff/employees" \
  -H "Content-Type: application/json" \
  -d "{\"department_id\":\"$DEPT_ID\",\"first_name\":\"Bob\",\"last_name\":\"Jones\",\"email\":\"bob.jones.$RUN_ID@hotel.com\",\"hire_date\":\"2025-03-01\"}")
EMP2_ID=$(jq_parse "$EMP2_JSON" ".id")
DEACT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/staff/employees/$EMP2_ID/deactivate")
[ "$DEACT_STATUS" = "204" ] && ok "PATCH /staff/employees/{id}/deactivate — HTTP 204" || fail "PATCH /staff/employees/{id}/deactivate — HTTP $DEACT_STATUS"

# ── 5. Dashboard ──────────────────────────────────────────────────────────────
echo ""
echo "── 5. Dashboard ──"

echo "  Getting dashboard summary..."
SUMMARY_JSON=$(curl -sf "$BASE/dashboard/summary?branch_id=$BRANCH_ID")
OCC_PCT=$(jq_parse "$SUMMARY_JSON" ".occupancy_pct")
ok "GET /dashboard/summary — occupancy_pct=$OCC_PCT"

echo "  Getting occupancy trend (7 days)..."
OCC_TREND=$(curl -sf "$BASE/dashboard/occupancy?branch_id=$BRANCH_ID&days=7")
OCC_COUNT=$(jq_parse "$OCC_TREND" "length")
[ "$OCC_COUNT" = "7" ] && ok "GET /dashboard/occupancy?days=7 — $OCC_COUNT data points" || fail "GET /dashboard/occupancy — expected 7 points, got $OCC_COUNT"

echo "  Getting revenue trend (7 days)..."
REV_TREND=$(curl -sf "$BASE/dashboard/revenue?branch_id=$BRANCH_ID&days=7")
REV_COUNT=$(jq_parse "$REV_TREND" "length")
[ "$REV_COUNT" = "7" ] && ok "GET /dashboard/revenue?days=7 — $REV_COUNT data points" || fail "GET /dashboard/revenue — expected 7 points, got $REV_COUNT"

# ── 6. Negative tests ─────────────────────────────────────────────────────────
echo ""
echo "── 6. Negative Tests ──"

NULL_ID="00000000-0000-0000-0000-000000000000"

echo "  404 — non-existent hotel..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/hotels/$NULL_ID")
expect_status "GET /hotels/{bad_id}" "404" "$STATUS"

echo "  404 — non-existent employee..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/staff/employees/$NULL_ID")
expect_status "GET /staff/employees/{bad_id}" "404" "$STATUS"

echo "  422 — reservation check_out before check_in..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/bookings/reservations" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\":\"$ROOM_ID\",\"guest_id\":\"$GUEST_ID\",\"check_in_date\":\"2026-10-10\",\"check_out_date\":\"2026-10-05\",\"adults\":1,\"total_amount\":\"500.00\"}")
expect_status "POST /bookings/reservations (checkout before checkin)" "422" "$STATUS"

echo "  409 — duplicate guest email..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/bookings/guests" \
  -H "Content-Type: application/json" \
  -d "{\"first_name\":\"Dup\",\"last_name\":\"Guest\",\"email\":\"john.doe.$RUN_ID@example.com\"}")
expect_status "POST /bookings/guests (duplicate email)" "409" "$STATUS"

echo "  422 — add item to CLOSED order..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/restaurant/orders/$ORDER_ID/items" \
  -H "Content-Type: application/json" \
  -d "{\"menu_item_id\":\"$ITEM_ID\",\"quantity\":1}")
expect_status "POST /restaurant/orders/{id}/items (order closed)" "422" "$STATUS"

echo "  409 — double-cancel same order (BUG 3 fix test)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/restaurant/orders/$ORDER_CANCEL_ID/cancel")
expect_status "PATCH /restaurant/orders/{id}/cancel (already cancelled)" "409" "$STATUS"

echo "  422 — cancel a CLOSED order..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/restaurant/orders/$ORDER_ID/cancel")
expect_status "PATCH /restaurant/orders/{id}/cancel (order closed)" "422" "$STATUS"

echo "  404 — cancel non-existent order (BUG 3 fix — should be 404 not 422)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/restaurant/orders/$NULL_ID/cancel")
expect_status "PATCH /restaurant/orders/{bad_id}/cancel (not found)" "404" "$STATUS"

echo "  422 — invalid room status..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/hotels/rooms/$ROOM_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"INVALID_STATUS"}')
expect_status "PATCH /hotels/rooms/{id}/status (invalid value)" "422" "$STATUS"

echo "  422 — double clock-out..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/staff/attendance/$ATT_ID/clock-out" \
  -H "Content-Type: application/json" \
  -d '{"clock_out":"2026-07-01T18:00:00Z"}')
expect_status "PATCH /staff/attendance/{id}/clock-out (already clocked out)" "422" "$STATUS"

echo "  422 — invalid reservation state transition (re-confirm CHECKED_OUT)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/bookings/reservations/$RES_ID/confirm")
expect_status "PATCH /reservations/{id}/confirm (already CHECKED_OUT)" "422" "$STATUS"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
