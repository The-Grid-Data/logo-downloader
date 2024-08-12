import requests
import json
import os
from urllib.parse import urlparse
import zipfile
import io

# Define the URL for the GraphQL endpoint
url = "https://maximum-grackle-73.hasura.app/v1/graphql"

# Define the GraphQL query to fetch product data, filtering for main products associated with a specific product ID (22)
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


# Function to execute the GraphQL query and fetch data
def fetch_data(url, query):
    # Send a POST request to the GraphQL endpoint with the query
    response = requests.post(url, json={'query': query})

    # Check if the request was successful
    if response.status_code == 200:
        return response.json()  # Return the JSON response
    else:
        # Raise an exception if the query failed
        raise Exception(f"Query failed with status code: {response.status_code}")


# Function to download the logo image from a given URL
def download_logo(logo_url):
    # Return None if the logo URL is not provided
    if not logo_url:
        return None

    try:
        # Send a GET request to download the logo
        response = requests.get(logo_url)

        # Check if the request was successful
        if response.status_code == 200:
            return response.content  # Return the logo content
        else:
            # Print an error message if the download failed
            print(f"Failed to download logo from {logo_url}")
            return None
    except Exception as e:
        # Print an error message if an exception occurred during the download
        print(f"Error downloading logo from {logo_url}: {str(e)}")
        return None


# Function to print the folder tree structure based on product data and download logos
def print_folder_tree(data):
    products = data['data']['products']  # Extract products from the fetched data
    tree = {}  # Initialize the tree structure to organize products
    skipped_items = []  # List to keep track of products that were skipped due to errors
    logos = {}  # Dictionary to store downloaded logos with their file paths

    # Iterate over each product in the data
    for product in products:
        try:
            # Extract relevant product details
            sector = product['profile']['profileSector']['name']
            product_type = product['productType']['name']
            product_name = product['name']
            logo_url = product['profile'].get('logo')  # Get the logo URL, if available

            # Build the tree structure based on sector and product type
            if sector not in tree:
                tree[sector] = {}
            if product_type not in tree[sector]:
                tree[sector][product_type] = []

            # Download the logo
            logo_content = download_logo(logo_url)

            if logo_content:
                # Parse the URL to get the file extension
                parsed_url = urlparse(logo_url)
                file_ext = os.path.splitext(parsed_url.path)[1]

                # Create a safe filename by removing invalid characters
                safe_filename = "".join([c for c in product_name if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
                new_filename = f"{safe_filename}{file_ext}"

                # Store the logo content with its path in the logos dictionary
                logos[f"{sector}/{product_type}/{new_filename}"] = logo_content
            else:
                new_filename = None  # Set to None if logo download failed

            # Add the product to the tree structure
            tree[sector][product_type].append({
                'name': product_name,
                'logo': new_filename
            })
        except (KeyError, TypeError):
            # Skip the product if there was an error extracting data
            skipped_items.append({
                'id': product.get('id', 'Unknown ID'),
                'name': product.get('name', 'Unknown Name')
            })

    # Print the folder tree structure
    for sector, product_types in tree.items():
        print(f"{sector}")
        for product_type, products in product_types.items():
            print(f"-{product_type}")
            for product in products:
                # Print product name along with logo file information
                logo_info = f" (Logo: {product['logo']})" if product['logo'] else " (No logo)"
                print(f"--{product['name']}{logo_info}")
        print()

    return skipped_items, logos  # Return skipped items and downloaded logos


# Function to create a ZIP file containing all downloaded logos
def create_zip_file(logos):
    zip_buffer = io.BytesIO()  # Create an in-memory buffer for the ZIP file
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        # Add each logo to the ZIP file with its respective path
        for filepath, content in logos.items():
            zip_file.writestr(filepath, content)

    # Write the ZIP file content to a file on disk
    with open('logos.zip', 'wb') as f:
        f.write(zip_buffer.getvalue())


# Main script execution
if __name__ == "__main__":
    try:
        # Fetch product data from the GraphQL endpoint
        result = fetch_data(url, query)

        # Process and print the folder tree, and download logos
        skipped, logos = print_folder_tree(result)

        # Create a ZIP file with all downloaded logos, if any were found
        if logos:
            create_zip_file(logos)
            print(f"\nCreated logos.zip with {len(logos)} logo files.")

        # Print information about any products that were skipped
        if skipped:
            print("\nSkipped items:")
            for item in skipped:
                print(f"- ID: {item['id']}, Name: {item['name']}")
    except Exception as e:
        # Print an error message if an exception occurred during execution
        print(f"An error occurred: {str(e)}")
