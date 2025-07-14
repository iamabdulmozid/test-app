import os
import re
import requests
from datetime import datetime

SHOP_URL = os.getenv("SHOP_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

MATERIAL_CATEGORIES = {
    'niubi': 'Jayden',
    'niubi plus': 'Jayden',
    'NV': 'Tan',
    'blanket': 'Other',
    'sticker': 'Other'
}

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', 'x', name)

def rename_variant(variant_title: str) -> str:
    variant_lower = variant_title.lower()
    if variant_lower == '2-way tricot':
        return 'niubi'
    elif variant_lower == '2 way tricot':
        return 'niubi'
    elif variant_lower == 'premium 2 way tricot':
        return 'niubi plus'
    elif variant_lower == 'plush':
        return 'nv'
    return variant_title

def extract_material_category(variant_title: str) -> str:
    for key in MATERIAL_CATEGORIES:
        if key.lower() == variant_title.lower():
            return MATERIAL_CATEGORIES[key]
    return "Other"

def generate_query(start_date: str, end_date: str) -> str:
    return f'''
    query ($cursor: String) {{
      orders(first: 100, after: $cursor, query: "created_at:>={start_date}T00:00:00Z created_at:<={end_date}T23:59:59Z") {{
        pageInfo {{ hasNextPage }}
        edges {{
          cursor
          node {{
            id name createdAt email
            totalPriceSet {{ shopMoney {{ amount currencyCode }} }}
            shippingLine {{
              title code
              originalPriceSet {{ shopMoney {{ amount currencyCode }} }}
            }}
            lineItems(first: 20) {{
              edges {{
                node {{
                  name
                  quantity
                  variant {{ title }}
                  customAttributes {{
                    key
                    value
                  }}
                }}
              }}
            }}
            shippingAddress {{
              name address1 city zip country phone
            }}
          }}
        }}
      }}
    }}
    '''


def fetch_orders(start_date: str, end_date: str):
    print(f"Start Date: {start_date}, End Date: {end_date}")
    url = f"{SHOP_URL}/admin/api/2024-04/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    all_orders = []
    cursor = None
    query_template = generate_query(start_date, end_date)

    while True:
        json_data = {
            "query": query_template,
            "variables": {"cursor": cursor}
        }
        res = requests.post(url, headers=headers, json=json_data)
        data = res.json()

        if "errors" in data or "data" not in data:
            raise Exception(f"Shopify API error: {data.get('errors', data)}")

        orders_data = data["data"]["orders"]
        all_orders.extend(orders_data["edges"])

        if not orders_data["pageInfo"]["hasNextPage"]:
            break
        cursor = orders_data["edges"][-1]["cursor"]

    return all_orders

def process_orders(orders):
    today_str = datetime.today().strftime("%d.%m.%Y")
    base_folder = os.path.join("orders", f"{today_str} order")
    os.makedirs(base_folder, exist_ok=True)

    for order in orders:
        node = order["node"]
        items = node["lineItems"]["edges"]
        addr = node["shippingAddress"]
        customer_name = sanitize_filename(addr["name"])

        shipping_method = node["shippingLine"]["title"]



        # Parse all items into types
        type_map = {"Tan": [], "Jayden": [], "Other": []}
        for item in items:
            item_node = item["node"]
            quantity = item_node["quantity"]
            variant_title = item_node["variant"]["title"]
            parts = [p.strip() for p in variant_title.split("/")]
            material = parts[0] if len(parts) > 0 else "Unknown"
            size = sanitize_filename(parts[1]) if len(parts) > 1 else "150x50cm"
            if shipping_method != "Free Shipping": 
                size += f" {shipping_method}"
            if quantity > 1:
                customer_name = f"{quantity}X {customer_name}"
            name_title = sanitize_filename(item_node["name"].split(" - ")[0].strip())

            personalisation = ""

            custom_attrs = item_node.get("customAttributes", [])
            for attr in custom_attrs:
                if attr.get("key") == " Personalisation-Text":
                    personalisation = attr.get("value", "")
                    break  # Exit loop once found
            
            print(f"Personalisation Text: {personalisation}")
            variant_type = rename_variant(material)
            if variant_type in ["niubi", "niubi plus"]:
                type_map["Jayden"].append((name_title, size, variant_type))
            elif variant_type == "NV":
                type_map["Tan"].append((name_title, size, variant_type))
            else:
                type_map["Other"].append((name_title, size, variant_type))

        # How many categories of items are there?
        used_types = [t for t in type_map if type_map[t]]

        def write_address_file(path, note=None):
            os.makedirs(path, exist_ok=True)
            address_text = f"{addr['name']}\n{addr['address1']}\n{addr['city']}, {addr['zip']}\n{addr['country']}\n\n{addr['phone']}\n{node['email']}"
            if shipping_method != "Free Shipping":
                address_text += f"\n\n{shipping_method}"
            if note:
                address_text += f"\n\nNote: {note}"
            if quantity > 1:
                quantity_text = f"Quantity: {quantity}"
                with open(os.path.join(path, "quantity.txt"), "w", encoding="utf-8") as f:
                    f.write(quantity_text)
            if personalisation:
                # address_text += f"\n\nPersonalisation: {personalisation}"
                personalisation_text = f"{personalisation}\n"
                with open(os.path.join(path, "personalisation.txt"), "w", encoding="utf-8") as f:
                    f.write(personalisation_text)
                
            with open(os.path.join(path, "address.txt"), "w", encoding="utf-8") as f:
                f.write(address_text)

        # Handle orders with only one type
        if len(used_types) == 1:
            item_type = used_types[0]
            
            variant_type = type_map[item_type][0][2]
            material_category = sanitize_filename(extract_material_category(type_map[item_type][0][2]))
            if len(type_map[item_type]) == 1:
                folder_name = sanitize_filename(f"{customer_name} {variant_type} {size}")
                base_target = os.path.join(base_folder, material_category, folder_name)
            else:
                folder_name = sanitize_filename(f"{customer_name} {variant_type}")
                base_target = os.path.join(base_folder, material_category, folder_name)
                for name, size, _ in type_map[item_type]:
                    sub_folder = os.path.join(base_target, sanitize_filename(f"{name} {size}"))
                    os.makedirs(sub_folder, exist_ok=True)

            write_address_file(base_target)

        # Handle orders with 2 or 3 types
        else:
            type_to_category = {"NV": "Tan", "2WT": "Jayden", "Other": "Other"}
            for current_type in used_types:
                #category = sanitize_filename(type_to_category[current_type])
                for name, size, variant_type in type_map[current_type]:
                    folder_name = sanitize_filename(f"{customer_name} {variant_type} {size}")
                    path = os.path.join(base_folder, current_type, folder_name)
                    others = [t for t in used_types if t != current_type]
                    note = f"ship with orders from {', '.join(others)}"
                    write_address_file(path, note)

    return base_folder


