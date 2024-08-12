import requests  # Import the requests module to make HTTP requests
import json  # Import the json module to work with JSON data
import os  # Import the os module to interact with the operating system
from urllib.parse import urlparse  # Import urlparse to parse URLs
import zipfile  # Import the zipfile module to create and manage ZIP files
import io  # Import the io module for handling I/O operations in memory
from datetime import datetime  # Import datetime for working with dates and times
from collections import defaultdict  # Import defaultdict to create dictionaries with default values
import csv  # Import csv module to read/write CSV files

# Set the URL for the GraphQL endpoint
url = "https://gql.thegrid.id/v1/graphql"

# Define the GraphQL query to fetch profile data based on specific conditions
query = """
query MyQuery {
  profiles(
    where: {
      _or: [
        { assets: { deployedOnProductId: { _eq: 22 } } },
        { products: { 
          isMainProduct: { _eq: 1 },
          _or: [
            { deployedOnProductId: { _eq: 22 } },
            { supportsProducts: { id: { _eq: 22 } } }
          ]
        } }
      ]
    }
  ) {
    id
    logo
    name
    profileSector {
      name
    }
    assets {
      name
      deployedOnProductId
    }
    products(
      where: {
        isMainProduct: { _eq: 1 },
        _or: [
          { deployedOnProductId: { _eq: 22 } },
          { supportsProducts: { id: { _eq: 22 } } }
        ]
      }
    ) {
      name
      deployedOnProductId
      isMainProduct
      productType {
        name
      }
    }
  }
}
"""

# Function to fetch data from the GraphQL API
def fetch_data(url, query):
    response = requests.post(url, json={'query': query})  # Send a POST request with the query
    if response.status_code == 200:  # Check if the request was successful
        return response.json()  # Return the JSON response
    else:
        raise Exception(f"Query failed with status code: {response.status_code}")  # Raise an error if the request failed

# Function to download a logo from a given URL
def download_logo(logo_url):
    if not logo_url:  # Check if the logo URL is empty or None
        return None  # Return None if no logo URL is provided
    try:
        response = requests.get(logo_url)  # Send a GET request to download the logo
        if response.status_code == 200:  # Check if the download was successful
            return response.content  # Return the content of the downloaded logo
        else:
            print(f"Failed to download logo from {logo_url}")  # Print an error message if the download failed
            return None  # Return None if the download failed
    except Exception as e:
        print(f"Error downloading logo from {logo_url}: {str(e)}")  # Print an error message if an exception occurs
        return None  # Return None in case of an exception

# Function to process the fetched data
def process_data(data):
    profiles = data['data']['profiles']  # Extract the profiles data from the response
    tree = defaultdict(lambda: defaultdict(list))  # Create a nested dictionary to store profiles by sector and subfolder
    skipped_items = []  # List to store profiles that are skipped due to errors
    logos = {}  # Dictionary to store downloaded logos
    results = []  # List to store results for logging or display
    csv_data = []  # List to store data for CSV export

    for profile in profiles:  # Iterate over each profile in the data
        try:
            sector = profile['profileSector']['name']  # Get the sector name for the profile
            profile_name = profile['name']  # Get the profile name
            profile_id = profile['id']  # Get the profile ID
            logo_url = profile.get('logo')  # Get the logo URL if available

            # Determine the product or asset type and subfolder
            if profile['products']:
                product = profile['products'][0]  # Use the first product
                product_type = product['productType']['name']  # Get the product type name
                subfolder = product_type  # Use product type as subfolder
                asset_name = product['name']  # Get the product name as asset name
            elif profile['assets']:
                subfolder = "ASSETS"  # Use "ASSETS" as the subfolder for assets
                asset_name = profile['assets'][0]['name'] if profile['assets'] else None  # Get the asset name
            else:
                raise KeyError("Profile has neither products nor assets")  # Raise an error if neither products nor assets exist

            logo_content = download_logo(logo_url)  # Download the logo
            if logo_content:
                parsed_url = urlparse(logo_url)  # Parse the logo URL
                file_ext = os.path.splitext(parsed_url.path)[1]  # Get the file extension
                safe_filename = "".join([c for c in profile_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()  # Sanitize the filename
                new_filename = f"{safe_filename}_{profile_id}{file_ext}"  # Create a new filename for the logo
                logos[f"{sector}/{subfolder}/{new_filename}"] = logo_content  # Store the logo in the dictionary
            else:
                new_filename = None  # If no logo was downloaded, set filename to None

            # Store the processed profile data in the tree and results list
            tree[sector][subfolder].append({
                'id': profile_id,
                'name': profile_name,
                'logo': new_filename
            })

            results.append(f"{sector}/{subfolder}/{profile_name}_{profile_id} - Logo: {'Yes' if new_filename else 'No'}")

            # Prepare data for CSV export
            csv_data.append({
                'name': profile_name,
                'gridid': profile_id,
                'sector': sector,
                'product_type': subfolder,
                'assetname': asset_name
            })

        except (KeyError, TypeError) as e:
            skipped_items.append({
                'id': profile.get('id', 'Unknown ID'),  # If ID is missing, use 'Unknown ID'
                'name': profile.get('name', 'Unknown Name'),  # If name is missing, use 'Unknown Name'
                'reason': str(e)  # Store the reason for skipping
            })

    return tree, skipped_items, logos, results, csv_data  # Return processed data

# Function to create a ZIP file containing logos, results, and CSV data
def create_zip_file(logos, results_content, csv_content):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")  # Get the current time for the filename
    zip_filename = f'grid_data_{current_time}.zip'  # Create a filename for the ZIP file
    zip_buffer = io.BytesIO()  # Create an in-memory buffer for the ZIP file
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:  # Create a ZIP file in the buffer
        for filepath, content in logos.items():
            zip_file.writestr(filepath, content)  # Write each logo to the ZIP file
        zip_file.writestr(f'results_{current_time}.txt', results_content)  # Write the results text file to the ZIP
        zip_file.writestr(f'outputs\folder_contents_{current_time}.csv', csv_content)  # Write the CSV file to the ZIP

    os.makedirs('exported zips', exist_ok=True)  # Ensure the output directory exists
    with open(os.path.join('exported zips', zip_filename), 'wb') as f:  # Write the ZIP file to disk
        f.write(zip_buffer.getvalue())  # Save the ZIP buffer contents to the file
    return zip_filename  # Return the name of the created ZIP file

# Function to generate the content for the results text file
def generate_results_content(tree, results, skipped, logo_count):
    content = f"Folder Structure and Contents:\n\nTotal Logos: {logo_count}\n\n"  # Start the content with the logo count
    for sector, subfolders in tree.items():
        content += f"{sector}/\n"  # Add the sector to the content
        for subfolder, profiles in subfolders.items():
            content += f"  {subfolder}/\n"  # Add the subfolder to the content
            for profile in profiles:
                logo_info = f" (Logo: {profile['logo']})" if profile['logo'] else " (No logo)"  # Add logo information
                content += f"    - {profile['name']}_{profile['id']}{logo_info}\n"  # Add profile details
        content += "\n"

    content += "Processed Profiles:\n"
    for result in results:
        content += f"{result}\n"  # Add each result to the content

    content += "\nSkipped Profiles:\n"
    for item in skipped:
        content += f"- ID: {item['id']}, Name: {item['name']}, Reason: {item['reason']}\n"  # Add skipped profile details

    return content  # Return the generated content

# Function to generate the content for the CSV file
def generate_csv_content(csv_data):
    output = io.StringIO()  # Create an in-memory string buffer for the CSV data
    fieldnames = ['name', 'gridid', 'sector', 'product_type', 'assetname']  # Define the CSV header fields
    writer = csv.DictWriter(output, fieldnames=fieldnames)  # Create a CSV writer object
    writer.writeheader()  # Write the CSV header
    for row in csv_data:
        writer.writerow(row)  # Write each row of data to the CSV
    return output.getvalue()  # Return the CSV content as a string

# Main entry point of the script
if __name__ == "__main__":
    try:
        result = fetch_data(url, query)  # Fetch data from the GraphQL API
        tree, skipped, logos, results, csv_data = process_data(result)  # Process the fetched data
        results_content = generate_results_content(tree, results, skipped, len(logos))  # Generate results content
        csv_content = generate_csv_content(csv_data)  # Generate CSV content

        if logos:  # Check if any logos were downloaded
            zip_filename = create_zip_file(logos, results_content, csv_content)  # Create a ZIP file with the data
            print(f"\nCreated {zip_filename} in 'exported zips' folder with {len(logos)} logo files, results file, and CSV file.")
        else:
            print("No logos found to create zip file.")  # Inform the user if no logos were found
    except Exception as e:
        print(f"An error occurred: {str(e)}")  # Print an error message if an exception occurs
