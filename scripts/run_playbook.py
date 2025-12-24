#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import tempfile
import urllib.request
import urllib.error
import json

def get_server_details(hostname):
    api_url = os.environ.get("ORCHESTRATOR_API_URL")
    api_token = os.environ.get("ORCHESTRATOR_API_TOKEN")

    if not api_url or not api_token:
        print("Error: ORCHESTRATOR_API_URL or ORCHESTRATOR_API_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    # Simulation note: The backlog says "Tool resolves target to IP and Encrypted Private Key".
    # Since the API doesn't exist yet, we will mock this or assume it returns key details.
    # For now, let's assume we query by hostname to get details.
    # In a real scenario, this might need a specific endpoint like /api/servers/{hostname}/secrets
    
    try:
        # Fetching all servers to find the right one is inefficient but simple for v1
        req = urllib.request.Request(f"{api_url}/api/servers/", headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"Error fetching server details: {e}", file=sys.stderr)
        sys.exit(1)

    for server in data:
        if server.get("hostname") == hostname or server.get("ip_address") == hostname:
             # In a real implementation, we would fetch the private key from a secure vault or specific endpoint.
             # FOR THIS TASK: We assume the key is passed or available. 
             # Backlog Step 2.4 says: "Tool resolves... to ... Encrypted Private Key via API/DB".
             # Step 2.5: "Decrypts key into temp file".
             # As I cannot fully implement the "Encrypted" part without the API support, 
             # I will implement the logic assuming the API *would* return a 'private_key' field.
             return server
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Securely run ansible playbook")
    parser.add_argument("--target", required=True, help="Target hostname or IP")
    parser.add_argument("--playbook", required=True, help="Playbook name (relative to ansible/playbooks)")
    args = parser.parse_args()

    # 1. Resolve target
    server = get_server_details(args.target)
    if not server:
        print(f"Error: Target {args.target} not found in inventory.", file=sys.stderr)
        sys.exit(1)

    # 2. Handle Private Key
    # NOTE: This part is tricky because the API structure isn't fully defined. 
    # I will assume there's a need to handle a key. If the key is not in the API response,
    # we might fallback to default system keys.
    # For the sake of the task "Secure Execution Wrapper", I'll show how to use a temp key file.
    private_key_content = server.get("private_key")
    
    key_file_path = None
    if private_key_content:
        # data = decrypt(private_key_content) # Decryption logic would go here
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_key:
            temp_key.write(private_key_content)
            key_file_path = temp_key.name
        os.chmod(key_file_path, 0o600)

    # 3. Construct Command
    # Assuming the script is run from project root or checks paths relative to it
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ansible_dir = os.path.join(base_dir, "ansible")
    playbook_path = os.path.join(ansible_dir, "playbooks", args.playbook)
    inventory_script = os.path.join(ansible_dir, "inventory", "api_inventory.py")

    cmd = [
        "ansible-playbook",
        "-i", inventory_script,
        playbook_path,
        "--limit", args.target
    ]

    if key_file_path:
        cmd.extend(["--private-key", key_file_path])
        # Disable host key checking for automated new server provisioning often requires it
        # or we should manage known_hosts. For now, let's rely on ansible.cfg or env var.
        os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"

    # 4. Run Command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error executing playbook: {e}", file=sys.stderr)
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(e.returncode)
    finally:
        # 5. Cleanup
        if key_file_path and os.path.exists(key_file_path):
            os.remove(key_file_path)

if __name__ == "__main__":
    main()
