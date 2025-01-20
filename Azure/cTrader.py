import requests
from urllib.parse import urlencode

# Replace with your credentials
client_id = 'YOUR_CLIENT_ID'
client_secret = 'YOUR_CLIENT_SECRET'
redirect_uri = 'YOUR_REDIRECT_URI'
account_id = 'YOUR_ACCOUNT_ID'

# Step 1: Direct user to cTrader's authorization URL
auth_url = 'https://connect.spotware.com/apps/auth'
params = {
    'client_id': client_id,
    'redirect_uri': redirect_uri,
    'scope': 'trading',
    'response_type': 'code'
}
print(f"Please go to the following URL to authorize the application:\n{auth_url}?{urlencode(params)}")

# After authorization, you'll receive a 'code' parameter in the redirect URL
# Use that code to obtain the access token

# Step 2: Exchange authorization code for access token
code = input('Enter the authorization code: ')
token_url = 'https://connect.spotware.com/apps/token'
data = {
    'grant_type': 'authorization_code',
    'client_id': client_id,
    'client_secret': client_secret,
    'code': code,
    'redirect_uri': redirect_uri
}
response = requests.post(token_url, data=data)
tokens = response.json()
access_token = tokens['access_token']
