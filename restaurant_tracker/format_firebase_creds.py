#!/usr/bin/env python3
"""
Helper script to format Firebase credentials JSON for Railway environment variable.
This script reads the credentials file and outputs it as a single-line JSON string
that can be pasted into Railway's environment variable.
"""

import json
import sys
import os

def format_credentials_for_railway(credentials_path):
    """Read Firebase credentials file and format as single-line JSON string."""
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
        
        # Convert to single-line JSON string
        single_line = json.dumps(creds, separators=(',', ':'))
        
        print("=" * 80)
        print("FIREBASE_CREDENTIALS for Railway")
        print("=" * 80)
        print()
        print("Copy the following and paste it as the value for FIREBASE_CREDENTIALS")
        print("in your Railway project's environment variables:")
        print()
        print(single_line)
        print()
        print("=" * 80)
        print(f"Length: {len(single_line)} characters")
        print("=" * 80)
        
        return single_line
        
    except FileNotFoundError:
        print(f"ERROR: Credentials file not found: {credentials_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in credentials file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Default path
    default_path = "../creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json"
    
    # Use command line argument if provided
    credentials_path = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    # Resolve relative paths
    if not os.path.isabs(credentials_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_dir, credentials_path)
    
    format_credentials_for_railway(credentials_path)

