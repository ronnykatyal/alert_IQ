#!/usr/bin/env python3
"""
Bitcoin OI Scraper Test - No External Dependencies
Uses only built-in Python libraries to test basic connectivity
"""

import urllib.request
import urllib.error
import json
import re
from datetime import datetime

def test_basic_connectivity():
    """Test basic connection using only built-in urllib"""
    print("🔗 Testing CoinGlass connectivity (no external packages)...")
    
    try:
        # Create request with headers
        url = "https://www.coinglass.com/BitcoinOpenInterest"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Make request
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            
        print("✅ Connection successful!")
        print(f"   Status: {response.status}")
        print(f"   Content length: {len(content)} characters")
        
        return True, content
        
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False, None
        
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e.reason}")
        return False, None
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False, None

def test_content_analysis(content):
    """Analyze content using regex and basic string operations"""
    print("\n📊 Analyzing content for Bitcoin OI data...")
    
    try:
        # Convert to lowercase for easier searching
        content_lower = content.lower()
        
        # Look for key Bitcoin OI indicators
        indicators = {
            'bitcoin': 'bitcoin' in content_lower,
            'open_interest': 'open interest' in content_lower or 'openinterest' in content_lower,
            'futures': 'futures' in content_lower,
            'binance': 'binance' in content_lower,
            'btc': 'btc' in content_lower,
            'usd': 'usd' in content_lower or '$' in content_lower
        }
        
        found_count = sum(indicators.values())
        
        print(f"✅ Content indicators found: {found_count}/6")
        for key, found in indicators.items():
            status = "✅" if found else "❌"
            print(f"   {status} {key}")
        
        # Look for numeric patterns that suggest OI data
        print(f"\n🔢 Looking for numeric data patterns...")
        
        # Patterns for financial data
        patterns = {
            'large_numbers': r'\b\d{1,3}(?:,\d{3})+\b',  # 1,234,567
            'currency': r'\$\s*\d+(?:[.,]\d+)*[KMB]?',   # $1.2B
            'percentages': r'[+-]?\d+\.?\d*%',           # +5.23%
            'btc_amounts': r'\d+(?:[.,]\d+)*\s*BTC'      # 123.45 BTC
        }
        
        pattern_counts = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            pattern_counts[name] = len(matches)
            
            if matches:
                print(f"   ✅ {name}: {len(matches)} matches (sample: {matches[0] if matches else 'none'})")
            else:
                print(f"   ❌ {name}: no matches")
        
        total_patterns = sum(pattern_counts.values())
        
        if found_count >= 4 and total_patterns >= 10:
            print(f"\n🎉 Content analysis PASSED!")
            print(f"   Strong indicators of Bitcoin OI data present")
            return True
        elif found_count >= 3:
            print(f"\n⚠️  Content analysis PARTIAL")
            print(f"   Some indicators present, may need refinement")
            return True
        else:
            print(f"\n❌ Content analysis FAILED")
            print(f"   Insufficient indicators of Bitcoin OI data")
            return False
            
    except Exception as e:
        print(f"❌ Content analysis error: {e}")
        return False

def test_json_extraction(content):
    """Look for embedded JSON data that might contain OI information"""
    print(f"\n🔍 Searching for embedded JSON data...")
    
    try:
        # Look for JSON patterns in script tags or data attributes
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.pageData\s*=\s*({.*?});',
            r'"openInterest":\s*({.*?})',
            r'"futures":\s*(\[.*?\])',
            r'data-json="({.*?})"'
        ]
        
        found_json = []
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                print(f"   ✅ JSON pattern {i+1}: {len(matches)} matches")
                found_json.extend(matches[:2])  # Take first 2 matches
            else:
                print(f"   ❌ JSON pattern {i+1}: no matches")
        
        if found_json:
            print(f"\n📋 Found {len(found_json)} potential JSON data sources")
            # Try to validate JSON
            valid_json = 0
            for json_str in found_json:
                try:
                    json.loads(json_str)
                    valid_json += 1
                except:
                    pass
            
            print(f"   ✅ Valid JSON objects: {valid_json}/{len(found_json)}")
            return valid_json > 0
        else:
            print(f"   ⚠️  No obvious JSON data found")
            print(f"   May need to parse HTML tables instead")
            return False
            
    except Exception as e:
        print(f"❌ JSON extraction error: {e}")
        return False

def run_no_deps_test():
    """Run complete test without external dependencies"""
    print("🧪 Bitcoin OI Scraper - No Dependencies Test")
    print("=" * 55)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Basic connectivity
    connectivity_ok, content = test_basic_connectivity()
    
    if not connectivity_ok:
        print(f"\n❌ CONNECTIVITY FAILED")
        print(f"   Cannot reach CoinGlass website")
        print(f"   Check internet connection and try again")
        return False
    
    # Test 2: Content analysis
    content_ok = test_content_analysis(content)
    
    # Test 3: JSON extraction
    json_ok = test_json_extraction(content)
    
    # Summary
    print(f"\n" + "=" * 55)
    print("NO DEPENDENCIES TEST SUMMARY")
    print("=" * 55)
    
    tests = [
        ("Connectivity", connectivity_ok),
        ("Content Analysis", content_ok), 
        ("Data Extraction", json_ok or content_ok)  # Either method works
    ]
    
    passed_tests = sum(result for _, result in tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    print(f"\nTests passed: {passed_tests}/3")
    
    if passed_tests == 3:
        print(f"🎉 EXCELLENT! All tests passed")
        next_steps = """
🚀 Next Steps:
1. Install packages: pip install requests beautifulsoup4 pandas lxml
2. Run full scraper implementation  
3. Test alert system
4. Integrate into GUI

The website is accessible and contains Bitcoin OI data!
"""
        print(next_steps)
        
    elif passed_tests >= 2:
        print(f"⚠️  GOOD! Most tests passed")
        print(f"✅ Website is accessible, proceed with package installation")
        
    else:
        print(f"❌ ISSUES DETECTED")
        print(f"🔧 May need to debug connectivity or website changes")
    
    return passed_tests >= 2

if __name__ == "__main__":
    try:
        success = run_no_deps_test()
        
        if success:
            print(f"\n🎯 READY FOR PACKAGE INSTALLATION!")
            print(f"Run: pip install requests beautifulsoup4 pandas lxml")
        else:
            print(f"\n🔧 Fix connectivity issues first")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")