#!/usr/bin/env python3
import os
import sys
import argparse
import urllib.request
import urllib.error
import json

def update_status(hostname, status_data):
    api_url = os.environ.get("ORCHESTRATOR_API_URL")
    api_token = os.environ.get("ORCHESTRATOR_API_TOKEN")

    if not api_url or not api_token:
        print("Error: ORCHESTRATOR_API_URL or ORCHESTRATOR_API_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    # First, find server ID by hostname logic (similar to inventory) because usually REST APIs use ID
    # Or assuming /api/servers/hostname works. Let's assume /api/servers/ lookup first.
    
    server_id = None
    try:
        req = urllib.request.Request(f"{api_url}/api/servers/", headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for server in data:
                if server.get("hostname") == hostname or server.get("ip_address") == hostname:
                    server_id = server.get("id")
                    break
    except urllib.error.URLError as e:
        print(f"Error fetching servers: {e}", file=sys.stderr)
        sys.exit(1)

    if not server_id:
        print(f"Error: Server {hostname} not found.", file=sys.stderr)
        sys.exit(1)

    # Now Patch
    try:
        data_bytes = json.dumps(status_data).encode('utf-8')
        req = urllib.request.Request(
            f"{api_url}/api/servers/{server_id}", 
            data=data_bytes, 
            headers=headers, 
            method='PATCH'
        )
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 204):
                print(f"Successfully updated status for {hostname}")
            else:
                print(f"Failed to update status. Code: {response.status}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Error updating status: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update server provisioning status")
    parser.add_argument("--target", required=True, help="Target hostname or IP")
    parser.add_argument("--provisioned", action="store_true", help="Mark as provisioned")
    
    args = parser.parse_args()

    data = {}
    if args.provisioned:
        data["provisioned"] = True

    if not data:
        print("No changes specified.", file=sys.stderr)
        sys.exit(0)

    update_status(args.target, data)
