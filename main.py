import requests
import json
import os
from urllib.parse import urlparse
import zipfile
import io

url = "https://maximum-grackle-73.hasura.app/v1/graphql"
query = """
query LogoDownloadQuery {
  products(
    where: {
      isMainProduct: {_eq: 1}, 
      _or: [
        {deployedOnProductId: {_eq: 22}}, 
        {supportsProducts: {id: {_eq: 22}}}
      ]
    }
  ) {
    id
    name
    isMainProduct
    productType {
      name
    }
    profile {
      logo
      profileSector {
        name
      }
    }
  }
}
"""

def fetch_data(url, query):
    response = requests.post(url, json={'query': query})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with status code: {response.status_code}")

def download_logo(logo_url):
    if not logo_url:
        return None

    try:
        response = requests.get(logo_url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download logo from {logo_url}")
            return None
    except Exception as e:
        print(f"Error downloading logo from {logo_url}: {str(e)}")
        return None

def print_folder_tree(data):
    products = data['data']['products']
    tree = {}
    skipped_items = []
    logos = {}

    for product in products:
        try:
            sector = product['profile']['profileSector']['name']
            product_type = product['productType']['name']
            product_name = product['name']
            logo_url = product['profile'].get('logo')

            if sector not in tree:
                tree[sector] = {}
            if product_type not in tree[sector]:
                tree[sector][product_type] = []

            # Download the logo
            logo_content = download_logo(logo_url)

            if logo_content:
                # Get the file extension from the URL
                parsed_url = urlparse(logo_url)
                file_ext = os.path.splitext(parsed_url.path)[1]

                # Create a valid filename from the product name
                safe_filename = "".join([c for c in product_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                new_filename = f"{safe_filename}{file_ext}"

                # Store logo with full path
                logos[f"{sector}/{product_type}/{new_filename}"] = logo_content
            else:
                new_filename = None

            tree[sector][product_type].append({
                'name': product_name,
                'logo': new_filename
            })
        except (KeyError, TypeError):
            skipped_items.append({
                'id': product.get('id', 'Unknown ID'),
                'name': product.get('name', 'Unknown Name')
            })

    for sector, product_types in tree.items():
        print(f"{sector}")
        for product_type, products in product_types.items():
            print(f"-{product_type}")
            for product in products:
                logo_info = f" (Logo: {product['logo']})" if product['logo'] else " (No logo)"
                print(f"--{product['name']}{logo_info}")
        print()

    return skipped_items, logos

def create_zip_file(logos):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        for filepath, content in logos.items():
            zip_file.writestr(filepath, content)

    with open('logos.zip', 'wb') as f:
        f.write(zip_buffer.getvalue())

if __name__ == "__main__":
    try:
        result = fetch_data(url, query)
        skipped, logos = print_folder_tree(result)

        if logos:
            create_zip_file(logos)
            print(f"\nCreated logos.zip with {len(logos)} logo files.")

        if skipped:
            print("\nSkipped items:")
            for item in skipped:
                print(f"- ID: {item['id']}, Name: {item['name']}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")