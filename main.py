from flask import Flask, render_template, request, jsonify
import requests
import os       # Essential for securely reading API keys from Replit Secrets

# --- 1. Initialize Flask App ---
app = Flask(__name__)

# --- 2. PriceScout Class (Core Logic) ---
class PriceScout:
    def __init__(self, affiliate_id="YOUR_AFFILIATE_ID_123"):
        self.affiliate_id = affiliate_id

        # --- API CONFIGURATION ---
        self.API_CONFIG = {
            # ⚠️ REPLACE THIS URL with the base URL of your chosen Price Comparison API
            "base_url": "https://coles-product-price-api.p.rapidapi.com/coles/price-changes/?date=2025-03-02&page=1&page_size=20", 

            # Read the secure key from Replit Secrets set as 'RAPIDAPI_KEY'
            "api_key": os.environ.get('RAPIDAPI_KEY'), 

            "platform_name": "RapidAPI Partner" 
        }

    def fetch_prices(self, product_name):
        """
        Sends an HTTP request to the external price comparison API to get live data.
        """
        all_results = []

        # 1. Check if the API key is available (essential for deployment)
        if not self.API_CONFIG.get('api_key'):
            print("ERROR: RAPIDAPI_KEY not found in Replit Secrets.")
            # Fallback for testing when key is missing (you might show a mock result here)
            return []

        # 2. Set up headers and parameters required by the external API
        headers = {
            # Standard way RapidAPI handles keys
            'X-RapidAPI-Key': self.API_CONFIG['api_key'], 
            # Note: The Host header is crucial for RapidAPI, extracted from the base_url
            'X-RapidAPI-Host': self.API_CONFIG['base_url'].split('//')[1].split('/')[0]
        }

        params = {
            # The API needs the product query and usually a country code
            'query': product_name, 
            'country_code': 'IN' 
        }

        try:
            # 3. Execute the external GET request
            response = requests.get(
                self.API_CONFIG['base_url'], 
                headers=headers, 
                params=params, 
                timeout=10 # Set a timeout so the app doesn't freeze
            )
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)

            api_data = response.json()

            # 4. Data Normalization (THIS SECTION IS HYPOTHETICAL AND DEPENDS ON YOUR API's JSON RESPONSE)
            # Assuming the API returns a list of items under a 'results' key
            for result in api_data.get('results', []): 

                try:
                    # Extract the necessary data, converting the price to a float
                    price_float = float(result.get('new_price')) 
                except (ValueError, TypeError):
                    continue # Skip items with invalid or missing price data

                # Add the standardized result to the list for comparison
                all_results.append({
                    "platform": "coles",
                    "price": price_float,
                    "link_base": result.get('url', '#') 
                })

            return all_results

        except requests.exceptions.RequestException as e:
            # Log and handle any request failures (network, timeout, invalid URL)
            print(f"API Request Failed for {product_name}: {e}")
            return []

    def create_affiliate_link(self, base_link):
        """
        Appends the affiliate ID to the product URL, ready for redirection.
        """
        # Note: If your API returns the affiliate link directly, this method is skipped.
        # But for now, we append the ID to the base URL provided by the API.
        return f"{base_link}&affid={self.affiliate_id}" # Using '&affid=' for general compatibility

    def compare_and_output(self, product_name):
        """
        Core logic: calls the API, adds affiliate IDs, and sorts results.
        """
        all_results = self.fetch_prices(product_name)

        if not all_results:
            return None 

        # 1. Add affiliate links
        for item in all_results:
            item['affiliate_link'] = self.create_affiliate_link(item['link_base'])

        # 2. Sort results by price (lowest first)
        sorted_results = sorted(all_results, key=lambda x: x['price'])

        return sorted_results

# --- 3. Flask Routes ---

@app.route('/')
def index():
    """Renders the main search page (index.html)."""
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    """Receives the search query from the frontend and returns JSON results."""

    query = request.args.get('product')

    if not query:
        return jsonify({"error": "No search query provided."}), 400

    # Retrieve the initialized PriceScout instance
    results = app.config['PRICESCOUT'].compare_and_output(query)

    if results is None or not results:
        return jsonify({"error": f"No live price data found for '{query}'. Please try a different product."}), 404

    # Return the results as JSON to the JavaScript frontend
    return jsonify(results)

# --- 4. Running the App ---
if __name__ == '__main__':
    # Initialize the PriceScout object once and store it in app config 
    app.config['PRICESCOUT'] = PriceScout() 
    app.run(host='0.0.0.0', port=8080, debug=True)