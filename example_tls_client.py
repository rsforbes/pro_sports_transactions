#!/usr/bin/env python3
"""
TLS Client example to bypass TLS fingerprinting on prosportstransactions.com
Enhanced with analysis based on utls issue #285, clienthello.go, tls-fingerprint.md
Includes advanced techniques and more comprehensive testing
"""

import tls_client
import time
import random
from datetime import datetime


def create_session(client_id="chrome_112", custom_headers=None):
    """Create a TLS session with browser-like fingerprint and optional custom headers"""
    session = tls_client.Session(
        client_identifier=client_id,
        random_tls_extension_order=True
    )
    
    # Use custom headers if provided, otherwise use default Chrome headers
    if custom_headers:
        session.headers = custom_headers
    else:
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    
    return session


def get_firefox_headers():
    """Get Firefox-specific headers"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }


def get_safari_headers():
    """Get Safari-specific headers"""
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def analyze_tls_fingerprint():
    """Analyze TLS fingerprint components based on clienthello.go"""
    print("[TLS FINGERPRINT] Based on clienthello.go (gaukas/clienthellod):")
    print("  - TLS Record/Handshake Versions, Cipher Suites (order matters)")
    print("  - Extensions in ORIGINAL ORDER (line 27) - CRITICAL!")
    print("  - Named Groups, Signature Algorithms, ALPN, Key Shares")
    print("[FINGERPRINT] SHA-1 hash of ALL components = unique ClientHello ID")
    print("[DETECTION] Cloudflare compares hash against known bot signatures")
    print("[STRATEGY] Trying multiple approaches to evade detection...")


def fetch_with_client(client_id, custom_headers=None, add_delay=False):
    """Fetch prosportstransactions.com with specific client identifier"""
    url = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php?Player=&Team=&BeginDate=&EndDate=&PlayerMovementChkBx=yes&submit=Search"
    
    print(f"\n[ATTEMPT] Client: {client_id}" + (" (custom headers)" if custom_headers else ""))
    print(f"[{datetime.now().isoformat()}] Starting request")
    
    if add_delay:
        delay = random.uniform(1, 3)
        print(f"[DELAY] Waiting {delay:.1f}s to avoid rate limiting...")
        time.sleep(delay)
    
    try:
        session = create_session(client_id, custom_headers)
        start_time = time.time()
        response = session.get(url)
        elapsed_time = time.time() - start_time
        
        print(f"[RESPONSE] Status: {response.status_code}, Time: {elapsed_time:.2f}s")
        
        if response.status_code == 403:
            # Check for Cloudflare headers
            cf_ray = response.headers.get('cf-ray', 'N/A')
            cf_mitigated = response.headers.get('cf-mitigated', 'N/A')
            server = response.headers.get('server', 'N/A')
            
            print(f"[BLOCKED] Ray ID: {cf_ray}")
            print(f"[BLOCKED] CF-Mitigated: {cf_mitigated}")
            print(f"[BLOCKED] Server: {server}")
            
            if "cloudflare" in server.lower() or cf_ray != 'N/A':
                print(f"[BLOCKED] Cloudflare TLS fingerprint detected for {client_id}")
            else:
                print(f"[BLOCKED] Non-Cloudflare blocking for {client_id}")
                
        elif response.status_code == 200:
            print(f"[SUCCESS] TLS bypass successful! Length: {len(response.text)} bytes")
            if "cf-ray" in response.headers:
                print(f"[SUCCESS] Ray ID: {response.headers.get('cf-ray')}")
            with open('response_debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("[SUCCESS] Response saved to: response_debug.html")
            return response
            
        elif response.status_code == 429:
            print("[RATE_LIMITED] Too many requests - adding delays")
            
        else:
            print(f"[UNEXPECTED] Status {response.status_code}")
            
        return response
        
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        return None


def try_advanced_techniques():
    """Try advanced TLS evasion techniques"""
    print("\n[ADVANCED] Trying additional TLS evasion techniques...")
    
    # Try older Chrome versions with matching headers
    older_clients = [
        ("chrome_103", None),
        ("chrome_105", None), 
        ("chrome_107", None),
        ("chrome_109", None),
    ]
    
    for client_id, headers in older_clients:
        response = fetch_with_client(client_id, headers, add_delay=True)
        if response and response.status_code == 200:
            return response
    
    # Try Firefox clients with Firefox headers
    firefox_headers = get_firefox_headers()
    firefox_clients = ["firefox_102", "firefox_104", "firefox_110", "firefox_119"]
    
    for client_id in firefox_clients:
        response = fetch_with_client(client_id, firefox_headers, add_delay=True)
        if response and response.status_code == 200:
            return response
    
    # Try Safari with Safari headers
    safari_headers = get_safari_headers()
    response = fetch_with_client("safari16_5", safari_headers, add_delay=True)
    if response and response.status_code == 200:
        return response
    
    return None


def main():
    """Main function - comprehensive TLS fingerprint bypass testing"""
    print("=" * 80)
    print("TLS Client Fingerprint Bypass Example - prosportstransactions.com")
    print("=" * 80)
    
    analyze_tls_fingerprint()
    
    # Standard client identifiers
    print("\n[PHASE 1] Testing standard client identifiers...")
    standard_clients = [
        "chrome_112", "chrome_110", "chrome_108", "chrome_104",
        "firefox_110", "firefox_108", "safari16_5", "chrome_120"
    ]
    
    success = False
    blocked_count = 0
    
    for client_id in standard_clients:
        response = fetch_with_client(client_id)
        
        if response and response.status_code == 200:
            success = True
            print(f"\n[FINAL] Success with standard client: {client_id}")
            break
        elif response and response.status_code == 403:
            blocked_count += 1
    
    # If standard approach fails, try advanced techniques
    if not success:
        print(f"\n[PHASE 1 RESULT] All {blocked_count} standard clients blocked")
        print("[PHASE 2] Trying advanced evasion techniques...")
        
        advanced_response = try_advanced_techniques()
        
        if advanced_response and advanced_response.status_code == 200:
            success = True
            print(f"\n[FINAL] Success with advanced technique!")
        else:
            print(f"\n[FINAL] All techniques blocked by TLS fingerprinting")
            print("[INFO] tls-client library signatures are comprehensively detected")
            print("[ANALYSIS] Cloudflare has extensive fingerprint database")
            print("\n[SOLUTIONS]")
            print("  1. utls library with custom ClientHello construction")
            print("  2. Browser automation (Playwright/Selenium) with real browsers")
            print("  3. Capture real browser TLS with tls-fingerprint tool")
            print("  4. Try different network/IP (though likely won't help)")
            print("  5. Look for API endpoints or less protected subdomains")
            print("  6. Consider if manual access works (human verification)")
    
    print("\n" + "=" * 80)
    print("Execution completed - All tls-client fingerprints appear blocked")
    print("Consider utls library or browser automation for genuine TLS signatures")
    print("=" * 80)


if __name__ == "__main__":
    main()